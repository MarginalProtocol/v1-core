// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "./FixedPoint96.sol";

/// @dev Positions represented in (x, y) space
library Position {
    using SafeCast for uint256;

    struct Info {
        uint128 size;
        uint128 debt0;
        uint128 debt1;
        uint128 insurance0;
        uint128 insurance1;
        bool zeroForOne;
        bool liquidated;
        int56 tickCumulativeStart;
        int56 oracleTickCumulativeStart;
        uint256 margin;
    }

    /// @notice Gets a position from positions mapping
    function get(
        mapping(bytes32 => Info) storage positions,
        address owner,
        uint112 id
    ) internal view returns (Info memory) {
        return positions[keccak256(abi.encodePacked(owner, id))];
    }

    /// @notice Stores the given position in positions mapping
    function set(
        mapping(bytes32 => Info) storage positions,
        address owner,
        uint112 id,
        Info memory position
    ) internal {
        positions[keccak256(abi.encodePacked(owner, id))] = position;
    }

    /// @notice Assembles a new position from pool state
    /// @dev zeroForOne == true means short position
    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne,
        int56 tickCumulativeStart,
        int56 oracleTickCumulativeStart
    ) internal pure returns (Info memory position) {
        position.zeroForOne = zeroForOne;
        position.tickCumulativeStart = tickCumulativeStart;
        position.oracleTickCumulativeStart = oracleTickCumulativeStart;
        position.size = size(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            zeroForOne
        );
        (position.insurance0, position.insurance1) = insurances(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne
        );
        (position.debt0, position.debt1) = debts(
            sqrtPriceX96Next,
            liquidityDelta,
            position.insurance0,
            position.insurance1
        );
    }

    /// @notice Size of position in (x, y) amounts
    function size(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        bool zeroForOne
    ) internal pure returns (uint128) {
        if (!zeroForOne) {
            // L / sqrt(P) - L / sqrt(P')
            return
                ((uint256(liquidity) << FixedPoint96.RESOLUTION) /
                    sqrtPriceX96 -
                    (uint256(liquidity) << FixedPoint96.RESOLUTION) /
                    sqrtPriceX96Next).toUint128();
        } else {
            // L * sqrt(P) - L * sqrt(P')
            return
                (
                    Math.mulDiv(
                        liquidity,
                        sqrtPriceX96 - sqrtPriceX96Next,
                        FixedPoint96.Q96
                    )
                ).toUint128();
        }
    }

    /// @notice Insurance balances to back position in (x, y) amounts
    function insurances(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne
    ) internal pure returns (uint128 insurance0, uint128 insurance1) {
        uint256 prod = !zeroForOne
            ? Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96Next,
                sqrtPriceX96
            ) // iy / y = 1 - sqrt(P'/P) * (1 - del L / L)
            : Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96,
                sqrtPriceX96Next
            ); // iy / y = 1 - sqrt(P/P') * (1 - del L / L)

        insurance0 = (((uint256(liquidity) - prod) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96).toUint128();
        insurance1 = (
            Math.mulDiv(
                uint256(liquidity) - prod,
                sqrtPriceX96,
                FixedPoint96.Q96
            )
        ).toUint128();
    }

    /// @notice Debts owed by position in (x, y) amounts
    function debts(
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        uint128 insurance0,
        uint128 insurance1
    ) internal pure returns (uint128 debt0, uint128 debt1) {
        // ix + dx = del L / sqrt(P'); iy + dy = del L * sqrt(P')
        debt0 = ((uint256(liquidityDelta) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96Next -
            insurance0).toUint128();
        debt1 = (Math.mulDiv(
            liquidityDelta,
            sqrtPriceX96Next,
            FixedPoint96.Q96
        ) - insurance1).toUint128();
    }

    /// @notice Fees owed by position in (x, y) amounts
    /// @dev Fees taken proportional to size
    function fees(uint128 size, uint24 fee) internal pure returns (uint256) {
        return (uint256(size) * fee) / 1e6;
    }

    /// @notice Absolute minimum margin requirement
    function marginMinimum(
        uint128 size,
        uint24 maintenance
    ) internal pure returns (uint256) {
        return (uint256(size) * maintenance) / 1e6;
    }

    /// @notice Amounts (x, y) of pool liquidity locked for position
    function amountsLocked(
        Info memory position
    ) internal pure returns (uint128 amount0, uint128 amount1) {
        if (!position.zeroForOne) {
            amount0 = position.size + position.debt0 + position.insurance0;
            amount1 = position.insurance1;
        } else {
            amount0 = position.insurance0;
            amount1 = position.size + position.debt1 + position.insurance1;
        }
    }
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "./FixedPoint96.sol";
import {MaintenanceMath} from "./MaintenanceMath.sol";

/// @dev Positions represented in (x, y) space
// TODO: check careful w types and overflow for price, liquidity math
library Position {
    using SafeCast for uint256;

    struct Info {
        uint128 size0;
        uint128 size1;
        uint128 debt0;
        uint128 debt1;
        uint128 insurance0;
        uint128 insurance1;
    }

    /// @notice Stores the given position in positions mapping
    function set(
        mapping(uint256 => Info) storage positions,
        uint256 id,
        Info memory position
    ) internal {
        positions[id] = position;
    }

    /// @notice Assembles a new position from pool state
    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne
    ) internal view returns (Info memory position) {
        (position.size0, position.size1) = sizes(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            zeroForOne
        );
        (position.insurance0, position.insurance1) = insurances(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta
        );
        (position.debt0, position.debt1) = debts(
            sqrtPriceX96Next,
            liquidityDelta,
            position.insurance0,
            position.insurance1
        );
    }

    /// @notice Size of position in (x, y) amounts
    function sizes(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        bool zeroForOne
    ) internal view returns (uint128 size0, uint128 size1) {
        if (zeroForOne) {
            // L / sqrt(P) - L / sqrt(P')
            // TODO: sizes, debts, insurances as uint192? otherwise need to safecast
            size0 = ((uint256(liquidity) << FixedPoint96.RESOLUTION) /
                sqrtPriceX96 -
                (uint256(liquidity) << FixedPoint96.RESOLUTION) /
                sqrtPriceX96Next).toUint128();
        } else {
            // L * sqrt(P) - L * sqrt(P')
            // TODO: check math
            // TODO: sizes as uint192? otherwise need to safecast
            size1 = (
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
        uint128 liquidityDelta
    ) internal view returns (uint128 insurance0, uint128 insurance1) {
        // TODO: check math same for long Y vs X
        uint256 prod = Math.mulDiv(
            (uint256(liquidity - liquidityDelta) << FixedPoint96.RESOLUTION) /
                sqrtPriceX96,
            sqrtPriceX96Next,
            sqrtPriceX96
        ); // TODO: overflow issues?
        insurance0 = ((uint256(liquidity) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96 -
            prod).toUint128();
        insurance1 = (Math.mulDiv(liquidity, sqrtPriceX96, FixedPoint96.Q96) -
            Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96Next,
                FixedPoint96.Q96
            )).toUint128();
    }

    /// @notice Debts owed by position in (x, y) amounts
    function debts(
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        uint128 insurance0,
        uint128 insurance1
    ) internal view returns (uint128 debt0, uint128 debt1) {
        // TODO: check math same for long Y vs X
        debt0 = ((uint256(liquidityDelta) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96Next -
            insurance0).toUint128();
        debt1 = (Math.mulDiv(
            liquidityDelta,
            sqrtPriceX96Next,
            FixedPoint96.Q96
        ) - insurance1).toUint128();
    }

    /// @notice Absolute minimum margin requirement
    function marginMinimum(
        uint128 size,
        uint16 maintenance
    ) internal view returns (uint256) {
        return Math.mulDiv(size, maintenance, MaintenanceMath.unit);
    }
}

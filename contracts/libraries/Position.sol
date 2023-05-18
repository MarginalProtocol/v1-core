// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "./FixedPoint96.sol";

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
    /// @dev Includes fees on size added to debt on long token
    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint24 fee
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
            liquidityDelta,
            zeroForOne
        );
        (position.debt0, position.debt1) = debts(
            sqrtPriceX96Next,
            liquidityDelta,
            position.insurance0,
            position.insurance1
        );

        (uint128 fees0, uint128 fees1) = fees(
            position.size0,
            position.size1,
            fee
        );

        // add the fees to debt outstanding
        position.debt0 += fees0;
        position.debt1 += fees1;
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
            size0 = ((uint256(liquidity) << FixedPoint96.RESOLUTION) /
                sqrtPriceX96 -
                (uint256(liquidity) << FixedPoint96.RESOLUTION) /
                sqrtPriceX96Next).toUint128();
        } else {
            // L * sqrt(P) - L * sqrt(P')
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
        uint128 liquidityDelta,
        bool zeroForOne
    ) internal view returns (uint128 insurance0, uint128 insurance1) {
        uint256 prod = zeroForOne
            ? Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96Next,
                sqrtPriceX96
            )
            : Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96,
                sqrtPriceX96Next
            );

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
    ) internal view returns (uint128 debt0, uint128 debt1) {
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
    /// @dev Fees taken proportional to size and added to long token debt
    function fees(
        uint128 size0,
        uint128 size1,
        uint24 fee
    ) internal view returns (uint128 fees0, uint128 fees1) {
        fees0 = uint128((uint256(size0) * fee) / 1e6);
        fees1 = uint128((uint256(size1) * fee) / 1e6);
    }

    /// @notice Absolute minimum margin requirement accounting for fees
    function marginMinimumWithFees(
        uint128 size,
        uint24 maintenance,
        uint24 fee
    ) internal view returns (uint256) {
        return (uint256(size) * maintenance + uint256(size) * fee) / 1e6;
    }
}

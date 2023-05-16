// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {FixedPoint96} from "./FixedPoint96.sol";
import {MaintenanceMath} from "./MaintenanceMath.sol";

/// @dev Positions represented in (x, y) space
library Position {
    struct Info {
        uint256 size0;
        uint256 size1;
        uint256 debt0;
        uint256 debt1;
        uint256 insurance0;
        uint256 insurance1;
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
        uint256 liquidity,
        uint256 sqrtPrice,
        uint256 sqrtPriceNext,
        uint256 liquidityDelta,
        bool zeroForOne
    ) internal returns (Info memory position) {
        (position.size0, position.size1) = sizes(
            liquidity,
            sqrtPrice,
            sqrtPriceNext,
            liquidityDelta,
            zeroForOne
        );
        // TODO: debts, insurance
    }

    /// @notice Size of position in (x, y) amounts
    function sizes(
        uint256 liquidity,
        uint256 sqrtPrice,
        uint256 sqrtPriceNext,
        uint256 liquidityDelta,
        bool zeroForOne
    ) internal view returns (uint256 size0, uint256 size1) {
        if (zeroForOne) {
            // L / sqrt(P) - L / sqrt(P')
            uint256 shifted = liquidity << FixedPoint96.RESOLUTION;
            size0 = shifted / sqrtPrice - shifted / sqrtPriceNext;
        } else {
            // TODO: check math
            // L * sqrt(P) - L * sqrt(P')
            size1 =
                Math.mulDiv(liquidity, sqrtPrice, FixedPoint96.Q96) -
                Math.mulDiv(liquidity, sqrtPriceNext, FixedPoint96.Q96);
        }
    }

    /// @notice Absolute minimum margin requirement
    function marginMinimum(
        uint256 size,
        uint256 maintenance
    ) internal view returns (uint256) {
        return Math.mulDiv(size, maintenance, MaintenanceMath.unit);
    }
}

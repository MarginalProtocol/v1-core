// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {MaintenanceMath} from "./MaintenanceMath.sol";

library Position {
    struct Info {
        uint256 liquidityBefore;
        uint256 sqrtPriceBefore;
        uint256 sqrtPriceAfter;
        uint256 fundingIndexBefore;
        uint256 liquidityDelta;
        bool zeroForOne;
        uint256 margin;
    }

    /// @notice Position size in long token
    function size(Info memory position) internal view returns (uint256) {
        // TODO: consider using uint160 sqrtPriceX96 to be consistent w uni v3
        return 0;
    }

    /// @notice Absolute minimum margin requirement
    function marginMinimum(
        Info memory position,
        uint256 maintenance
    ) internal view returns (uint256) {
        return Math.mulDiv(size(position), maintenance, MaintenanceMath.unit);
    }
}

// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

contract MockTickMath {
    function getTickAtSqrtRatio(
        uint160 sqrtRatioX96
    ) external pure returns (int24) {
        return TickMath.getTickAtSqrtRatio(sqrtRatioX96);
    }

    function getSqrtRatioAtTick(int24 tick) external pure returns (uint160) {
        return TickMath.getSqrtRatioAtTick(tick);
    }
}

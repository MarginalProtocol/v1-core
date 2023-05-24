// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "./FixedPoint96.sol";

library LiquidityMath {
    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96
    ) internal view returns (uint256 amount0, uint256 amount1) {
        // x = L / sqrt(P); y = L * sqrt(P)
        amount0 =
            (uint256(liquidity) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96;
        amount1 = Math.mulDiv(liquidity, sqrtPriceX96, FixedPoint96.Q96);
    }
}

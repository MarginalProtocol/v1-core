// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {LiquidityMath} from "../../../libraries/LiquidityMath.sol";

contract MockLiquidityMath {
    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96
    ) external view returns (uint128 amount0, uint128 amount1) {
        (amount0, amount1) = LiquidityMath.toAmounts(liquidity, sqrtPriceX96);
    }

    function toLiquiditySqrtPriceX96(
        uint128 reserve0,
        uint128 reserve1
    ) external view returns (uint128 liquidity, uint160 sqrtPriceX96) {
        (liquidity, sqrtPriceX96) = LiquidityMath.toLiquiditySqrtPriceX96(
            reserve0,
            reserve1
        );
    }
}

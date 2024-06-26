// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {LiquidityMath} from "../../../libraries/LiquidityMath.sol";

contract MockLiquidityMath {
    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96
    ) external view returns (uint256 amount0, uint256 amount1) {
        (amount0, amount1) = LiquidityMath.toAmounts(liquidity, sqrtPriceX96);
    }

    function toLiquiditySqrtPriceX96(
        uint256 reserve0,
        uint256 reserve1
    ) external view returns (uint128 liquidity, uint160 sqrtPriceX96) {
        (liquidity, sqrtPriceX96) = LiquidityMath.toLiquiditySqrtPriceX96(
            reserve0,
            reserve1
        );
    }

    function liquiditySqrtPriceX96Next(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        int256 amount0,
        int256 amount1
    ) external view returns (uint128 liquidityNext, uint160 sqrtPriceX96Next) {
        (liquidityNext, sqrtPriceX96Next) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                liquidity,
                sqrtPriceX96,
                amount0,
                amount1
            );
    }
}

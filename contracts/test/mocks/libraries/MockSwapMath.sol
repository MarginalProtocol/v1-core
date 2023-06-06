// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {SwapMath} from "../../../libraries/SwapMath.sol";

contract MockSwapMath {
    function swapAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint24 fee
    ) external pure returns (int256 amount0Delta, int256 amount1Delta) {
        return
            SwapMath.swapAmounts(
                liquidity,
                sqrtPriceX96,
                sqrtPriceX96Next,
                fee
            );
    }
}

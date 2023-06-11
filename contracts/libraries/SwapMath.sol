// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {FixedPoint96} from "./FixedPoint96.sol";

library SwapMath {
    /// @notice Computes amounts in and out on swap without fees
    /// @dev amount > 0 is amountIn, amount < 0 is amountOut
    // TODO: retest without fees
    function swapAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next
    ) internal pure returns (int256 amount0Delta, int256 amount1Delta) {
        // del x = L * del (1 / sqrt(P)); del y = L * del sqrt(P)
        bool zeroForOne = sqrtPriceX96Next < sqrtPriceX96;
        amount0Delta =
            int256(
                (uint256(liquidity) << FixedPoint96.RESOLUTION) /
                    sqrtPriceX96Next
            ) -
            int256(
                (uint256(liquidity) << FixedPoint96.RESOLUTION) / sqrtPriceX96
            );
        amount1Delta = zeroForOne
            ? -int256(
                Math.mulDiv(
                    liquidity,
                    sqrtPriceX96 - sqrtPriceX96Next,
                    FixedPoint96.Q96
                )
            )
            : int256(
                Math.mulDiv(
                    liquidity,
                    sqrtPriceX96Next - sqrtPriceX96,
                    FixedPoint96.Q96
                )
            );
    }

    // TODO: test
    function swapFees(
        uint256 amountIn,
        uint24 fee
    ) internal pure returns (uint256) {
        return (uint256(amountIn) * fee) / 1e6;
    }
}

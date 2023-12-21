// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {FixedPoint96} from "./FixedPoint96.sol";

library SwapMath {
    /// @notice Computes amounts in and out on swap without fees
    /// @dev amount > 0 is amountIn, amount < 0 is amountOut
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

    /// @notice Computes swap fee on amount in
    /// @dev Can revert when amount > type(uint232).max, but irrelevant for SwapMath.sol::swapAmounts output and pool fee rate constant
    /// @param amount Amount in to calculate swap fees off of
    /// @param fee Fee rate applied on amount in to pool
    /// @param lessFee Whether `amount` excludes swap fee amount
    /// @return Total swap fees taken from amount in to pool
    function swapFees(
        uint256 amount,
        uint24 fee,
        bool lessFee
    ) internal pure returns (uint256) {
        return (!lessFee ? (amount * fee) / 1e6 : (amount * fee) / (1e6 - fee));
    }
}

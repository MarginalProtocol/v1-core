// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "./FixedPoint96.sol";
import {SqrtPriceMath} from "./SqrtPriceMath.sol";

library LiquidityMath {
    using SafeCast for uint256;

    /// @notice Transforms (L, sqrtP) values into (X, Y) reserve amounts
    /// @param liquidity Pool liquidity in (L, sqrtP) space
    /// @param sqrtPriceX96 Pool price in (L, sqrtP) space
    /// @return amount0 The amount of token0 associated with the given (L, sqrtP) values
    /// @return amount1 The amount of token1 associated with the given (L, sqrtP) values
    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96
    ) internal pure returns (uint256 amount0, uint256 amount1) {
        // x = L / sqrt(P); y = L * sqrt(P)
        amount0 =
            (uint256(liquidity) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96;
        amount1 = Math.mulDiv(liquidity, sqrtPriceX96, FixedPoint96.Q96);
    }

    /// @notice Transforms (X, Y) reserve amounts into (L, sqrtP) values
    /// @dev Reverts on overflow if reserve0 * reserve1 > type(uint256).max as liquidity must fit into uint128
    /// @param reserve0 The amount of token0 in reserves
    /// @param reserve1 The amount of token1 in reserves
    /// @return liquidity Pool liquidity associated with reserve amounts
    /// @return sqrtPriceX96 Pool price associated with reserve amounts
    function toLiquiditySqrtPriceX96(
        uint256 reserve0,
        uint256 reserve1
    ) internal pure returns (uint128 liquidity, uint160 sqrtPriceX96) {
        // L = sqrt(x * y); sqrt(P) = sqrt(y / x)
        liquidity = Math.sqrt(reserve0 * reserve1).toUint128();

        uint256 _sqrtPriceX96 = (uint256(liquidity) <<
            FixedPoint96.RESOLUTION) / reserve0;
        if (
            !(_sqrtPriceX96 >= SqrtPriceMath.MIN_SQRT_RATIO &&
                _sqrtPriceX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert SqrtPriceMath.InvalidSqrtPriceX96();
        sqrtPriceX96 = uint160(_sqrtPriceX96);
    }

    /// @notice Calculates (L, sqrtP) after adding/removing amounts to/from pool reserves
    /// @param liquidity Pool liquidity before adding/removing reserves
    /// @param sqrtPriceX96 Pool price before adding/removing reserves
    /// @param amount0 The amount of token0 to add (positive) or remove (negative)
    /// @param amount1 The amount of token1 to add (positive) or remove (negative)
    /// @return liquidityNext Pool liquidity after adding/removing reserves
    /// @return sqrtPriceX96Next Pool price after adding/removing reserves
    function liquiditySqrtPriceX96Next(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        int256 amount0,
        int256 amount1
    ) internal pure returns (uint128 liquidityNext, uint160 sqrtPriceX96Next) {
        (uint256 reserve0, uint256 reserve1) = toAmounts(
            liquidity,
            sqrtPriceX96
        );

        if (amount0 < 0 && uint256(-amount0) >= reserve0)
            revert SqrtPriceMath.Amount0ExceedsReserve0();
        if (amount1 < 0 && uint256(-amount1) >= reserve1)
            revert SqrtPriceMath.Amount1ExceedsReserve1();

        uint256 reserve0Next = amount0 >= 0
            ? reserve0 + uint256(amount0)
            : reserve0 - uint256(-amount0);
        uint256 reserve1Next = amount1 >= 0
            ? reserve1 + uint256(amount1)
            : reserve1 - uint256(-amount1);

        (liquidityNext, sqrtPriceX96Next) = toLiquiditySqrtPriceX96(
            reserve0Next,
            reserve1Next
        );
    }
}

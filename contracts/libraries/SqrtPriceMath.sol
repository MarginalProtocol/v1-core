// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {FixedPoint96} from "./FixedPoint96.sol";

library SqrtPriceMath {
    /// @dev Adopts Uni V3 tick limits of (-887272, 887272)
    uint160 internal constant MIN_SQRT_RATIO = 4295128739;
    uint160 internal constant MAX_SQRT_RATIO =
        1461446703485210103287273052203988822378723970342;

    error InvalidSqrtPriceX96();
    error Amount0ExceedsReserve0();
    error Amount1ExceedsReserve1();

    /// @notice Calculates sqrtP after opening a position
    /// @dev Choice of insurance function made in this function
    function sqrtPriceX96NextOpen(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint24 maintenance
    ) internal pure returns (uint160) {
        uint256 prod = uint256(liquidityDelta) *
            uint256(liquidity - liquidityDelta);
        prod = Math.mulDiv(prod, 1e6, 1e6 + maintenance);

        // @dev root round down ensures no free size but can have nextX96 go opposite of intended direction
        // @dev as liquidityDelta -> 0. position.assemble will revert tho if so
        uint256 under = uint256(liquidity) ** 2 - 4 * prod;
        uint256 root = Math.sqrt(under);

        uint256 nextX96 = !zeroForOne
            ? Math.mulDiv(
                sqrtPriceX96,
                uint256(liquidity) + root,
                2 * uint256(liquidity - liquidityDelta)
            )
            : Math.mulDiv(
                sqrtPriceX96,
                2 * uint256(liquidity - liquidityDelta),
                uint256(liquidity) + root
            );
        if (!(nextX96 >= MIN_SQRT_RATIO && nextX96 < MAX_SQRT_RATIO))
            revert InvalidSqrtPriceX96();

        return uint160(nextX96);
    }

    /// @notice Calculates sqrtP after swapping tokens
    /// @dev Assumes amountSpecified != 0
    function sqrtPriceX96NextSwap(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        bool zeroForOne,
        int256 amountSpecified
    ) internal pure returns (uint160) {
        bool exactInput = amountSpecified > 0;

        uint256 nextX96;
        if (exactInput) {
            if (!zeroForOne) {
                // 1 is known
                // sqrt(P') = sqrt(P) + del y / L
                uint256 prod = Math.mulDiv(
                    uint256(amountSpecified),
                    FixedPoint96.Q96,
                    liquidity
                ); // TODO: uint256(amountSpecified) <= type(uint160).max if have contract size left
                nextX96 = sqrtPriceX96 + prod;
            } else {
                // 0 is known
                // sqrt(P') = sqrt(P) - (del x * sqrt(P)) / (L / sqrt(P) + del x)
                uint256 reserve0 = (uint256(liquidity) <<
                    FixedPoint96.RESOLUTION) / sqrtPriceX96;
                uint256 prod = Math.mulDiv(
                    uint256(amountSpecified),
                    sqrtPriceX96,
                    reserve0 + uint256(amountSpecified)
                ); // TODO: uint256(amountSpecified) <= type(uint96).max if have contract size left
                nextX96 = sqrtPriceX96 - prod;
            }
        } else {
            if (!zeroForOne) {
                // 0 is known
                // sqrt(P') = sqrt(P) - (del x * sqrt(P)) / (L / sqrt(P) + del x)
                uint256 reserve0 = (uint256(liquidity) <<
                    FixedPoint96.RESOLUTION) / sqrtPriceX96;
                if (reserve0 <= uint256(-amountSpecified))
                    revert Amount0ExceedsReserve0();

                uint256 prod = Math.mulDiv(
                    uint256(-amountSpecified),
                    sqrtPriceX96,
                    reserve0 - uint256(-amountSpecified)
                ); // TODO: uint256(-amountSpecified) <= type(uint96).max if have contract size left
                nextX96 = sqrtPriceX96 + prod;
            } else {
                // 1 is known
                // sqrt(P') = sqrt(P) + del y / L
                uint256 reserve1 = Math.mulDiv(
                    liquidity,
                    sqrtPriceX96,
                    FixedPoint96.Q96
                );
                if (reserve1 <= uint256(-amountSpecified))
                    revert Amount1ExceedsReserve1();

                uint256 prod = Math.mulDiv(
                    uint256(-amountSpecified),
                    FixedPoint96.Q96,
                    liquidity
                ); // TODO: uint256(-amountSpecified) <= type(uint160).max if have contract size left
                nextX96 = sqrtPriceX96 - prod;
            }
        }
        if (!(nextX96 >= MIN_SQRT_RATIO && nextX96 < MAX_SQRT_RATIO))
            revert InvalidSqrtPriceX96();
        return uint160(nextX96);
    }
}

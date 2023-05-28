// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {FixedPoint96} from "./FixedPoint96.sol";
import {SqrtPriceMath} from "./SqrtPriceMath.sol";

// TODO: worry about safe cast as amounts with sqrtPriceX96 min can be as large as uint192
// TODO: worry about rounding issues since used in mint/burn of shares + token balances
library LiquidityMath {
    using SafeCast for uint256;

    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96
    ) internal pure returns (uint128 amount0, uint128 amount1) {
        // x = L / sqrt(P); y = L * sqrt(P)
        amount0 = ((uint256(liquidity) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96).toUint128();
        amount1 = (Math.mulDiv(liquidity, sqrtPriceX96, FixedPoint96.Q96))
            .toUint128();
    }

    function toLiquiditySqrtPriceX96(
        uint128 reserve0,
        uint128 reserve1
    ) internal pure returns (uint128 liquidity, uint160 sqrtPriceX96) {
        // L = sqrt(x * y); sqrt(P) = sqrt(y / x)
        liquidity = Math
            .sqrt(uint256(reserve0) * uint256(reserve1))
            .toUint128();

        uint256 _sqrtPriceX96 = (uint256(liquidity) <<
            FixedPoint96.RESOLUTION) / reserve0;
        require(
            _sqrtPriceX96 >= SqrtPriceMath.MIN_SQRT_RATIO &&
                _sqrtPriceX96 < SqrtPriceMath.MAX_SQRT_RATIO,
            "sqrtPriceX96 exceeds min/max"
        );
        sqrtPriceX96 = uint160(_sqrtPriceX96);
    }
}

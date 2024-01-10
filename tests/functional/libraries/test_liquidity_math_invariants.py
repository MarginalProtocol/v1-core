import pytest

from math import sqrt


def test_liquidity_math__to_amounts_to_liquidity_sqrt_price_x96(liquidity_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    result = liquidity_math_lib.toLiquiditySqrtPriceX96(reserve0, reserve1)
    assert pytest.approx(result.liquidity, rel=1e-14) == liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-14) == sqrt_price_x96


def test_liquidity_math__to_liquidity_sqrt_price_x96_to_amounts(liquidity_math_lib):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves

    (liquidity, sqrt_price_x96) = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0, reserve1
    )
    result = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    assert pytest.approx(result.amount0, rel=1e-18) == reserve0
    assert pytest.approx(result.amount1, rel=1e-18) == reserve1


# TODO: fuzz

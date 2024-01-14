import pytest

from datetime import timedelta
from hypothesis import given, settings, strategies as st
from math import sqrt

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MINIMUM_LIQUIDITY,
    MINIMUM_SIZE,
)
from utils.utils import calc_liquidity_sqrt_price_x96_from_reserves


def test_liquidity_math_to_amounts_to_liquidity_sqrt_price_x96(liquidity_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    result = liquidity_math_lib.toLiquiditySqrtPriceX96(reserve0, reserve1)
    assert pytest.approx(result.liquidity, rel=1e-14) == liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-14) == sqrt_price_x96


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=MINIMUM_LIQUIDITY, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
)
def test_liquidity_math_to_amounts_to_liquidity_sqrt_price_x96__with_fuzz(
    liquidity_math_lib,
    liquidity,
    sqrt_price_x96,
):
    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    if reserve0 < MINIMUM_SIZE or reserve1 < MINIMUM_SIZE:
        # @dev ignore dust calcs for fuzz
        return

    # calc first to check for revert due to safecast or price out of bounds which ignore for fuzz
    (calc_liquidity, calc_sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    if calc_liquidity >= 2**128:
        return
    elif (
        calc_sqrt_price_x96 <= MIN_SQRT_RATIO * 1.0001
        or calc_sqrt_price_x96
        >= MAX_SQRT_RATIO * 0.9999  # to be extra safe in avoiding reverts
    ):
        return

    result = liquidity_math_lib.toLiquiditySqrtPriceX96(reserve0, reserve1)
    assert pytest.approx(result.liquidity, rel=1e-4, abs=5) == liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-4, abs=5) == sqrt_price_x96

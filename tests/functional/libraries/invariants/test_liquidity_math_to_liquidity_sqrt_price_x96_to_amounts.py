import pytest

from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MINIMUM_SIZE,
)
from utils.utils import calc_liquidity_sqrt_price_x96_from_reserves


def test_liquidity_math_to_liquidity_sqrt_price_x96_to_amounts(liquidity_math_lib):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves

    (liquidity, sqrt_price_x96) = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0, reserve1
    )
    result = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    assert pytest.approx(result.amount0, rel=1e-18) == reserve0
    assert pytest.approx(result.amount1, rel=1e-18) == reserve1


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000), max_examples=10000)
@given(
    reserve0=st.integers(min_value=MINIMUM_SIZE, max_value=2**256 - 1),
    reserve1=st.integers(min_value=MINIMUM_SIZE, max_value=2**256 - 1),
)
def test_liquidity_math_to_liquidity_sqrt_price_x96_to_amounts__with_fuzz(
    liquidity_math_lib,
    reserve0,
    reserve1,
):
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

    (liquidity, sqrt_price_x96) = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0, reserve1
    )

    result = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    assert pytest.approx(result.amount0, rel=1e-4, abs=5) == reserve0
    assert pytest.approx(result.amount1, rel=1e-4, abs=5) == reserve1

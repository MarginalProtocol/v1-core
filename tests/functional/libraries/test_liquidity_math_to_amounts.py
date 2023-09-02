import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


def test_liquidity_math_to_amounts(liquidity_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    result = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    assert result == (amount0, amount1)


@pytest.mark.fuzzing
@given(
    liquidity=st.integers(min_value=1, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
)
def test_liquidity_math_to_amounts__with_fuzz(
    liquidity_math_lib, liquidity, sqrt_price_x96
):
    # TODO: fix for safe cast and anvil issues
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    result = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    assert result == (amount0, amount1)

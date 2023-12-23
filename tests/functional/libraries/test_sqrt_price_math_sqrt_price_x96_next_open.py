import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_sqrt_price_x96_next_open


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_sqrt_price_math_sqrt_price_x96_next_open__with_zero_for_one(
    sqrt_price_math_lib, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    # position size of ~5/(1+1/M)% of pool w about 5-5/(1+1/M)% to insurance
    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    assert (
        pytest.approx(result, rel=1e-15) == sqrt_price_x96_next
    )  # TQ: is this enough?
    assert (result >> 96) == (sqrt_price_x96_next >> 96)  # TQ: is this enough?


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_sqrt_price_math_sqrt_price_x96_next_open__with_one_for_zero(
    sqrt_price_math_lib, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    # position size of ~5/(1+1/M)% of pool w about 5-5/(1+1/M)% to insurance
    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    assert (
        pytest.approx(result, rel=1e-15) == sqrt_price_x96_next
    )  # TQ: is this enough?
    assert (result >> 96) == (sqrt_price_x96_next >> 96)  # TQ: is this enough?


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@given(
    liquidity=st.integers(min_value=1000, max_value=2**128 - 1),
    liquidity_delta=st.integers(min_value=1, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(
        min_value=MIN_SQRT_RATIO + 1, max_value=MAX_SQRT_RATIO - 1
    ),
    zero_for_one=st.booleans(),
)
def test_sqrt_price_math_sqrt_price_x96_next_open__with_fuzz(
    sqrt_price_math_lib,
    liquidity,
    liquidity_delta,
    sqrt_price_x96,
    zero_for_one,
    maintenance,
):
    if liquidity_delta >= liquidity:
        return

    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    # pass if invalid sqrt price next
    if (zero_for_one and sqrt_price_x96_next >= sqrt_price_x96 - 1) or (
        not zero_for_one and sqrt_price_x96_next <= sqrt_price_x96 + 1
    ):
        return
    elif sqrt_price_x96_next <= MIN_SQRT_RATIO or sqrt_price_x96_next >= MAX_SQRT_RATIO:
        return

    result_x96 = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    assert pytest.approx(result_x96, rel=1e-9, abs=1) == sqrt_price_x96_next

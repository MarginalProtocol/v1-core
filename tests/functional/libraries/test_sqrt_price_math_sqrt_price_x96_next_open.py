import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

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
    x=st.integers(min_value=100, max_value=2**128 - 1),
    y=st.integers(min_value=100, max_value=2**128 - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000 - 1),
    zero_for_one=st.booleans(),
)
def test_sqrt_price_math_sqrt_price_x96_next__with_fuzz(
    sqrt_price_math_lib, x, y, liquidity_delta_pc, zero_for_one, maintenance
):
    liquidity = int(sqrt(x * y))
    if liquidity >= 2**128:
        liquidity = 2**128 - 1

    liquidity_delta = (liquidity * liquidity_delta_pc) // 1000000

    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    sqrt_price_next = sqrt_price_x96_next >> 96

    result_x96 = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    result = result_x96 >> 96

    # TODO: fix for anvil errors
    assert pytest.approx(result_x96, rel=1e-15) == sqrt_price_x96_next
    assert pytest.approx(result, rel=1e-15) == sqrt_price_next
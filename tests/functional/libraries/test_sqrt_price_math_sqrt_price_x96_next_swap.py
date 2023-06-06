import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import (
    calc_sqrt_price_x96_next_swap,
    calc_amounts_from_liquidity_sqrt_price_x96,
)


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_input_zero_for_one(
    sqrt_price_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = x * 1 // 100  # 1% of reserves in
    zero_for_one = True
    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-15) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_input_one_for_zero(
    sqrt_price_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = y * 1 // 100  # 1% of reserves in
    zero_for_one = False

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-15) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_output_zero_for_one(
    sqrt_price_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = -y * 1 // 100  # 1% of reserves out
    zero_for_one = True

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-15) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_output_one_for_zero(
    sqrt_price_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = -x * 1 // 100  # 1% of reserves out
    zero_for_one = False

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-15) == sqrt_price_x96_next
    )  # TQ: is this enough?


@pytest.mark.fuzzing
@given(
    liquidity=st.integers(min_value=1000, max_value=2**128 - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    zero_for_one=st.booleans(),
    exact_input=st.booleans(),
)
def test_sqrt_price_math_sqrt_price_x96_next_swap__with_fuzz(
    sqrt_price_math_lib,
    liquidity,
    liquidity_delta_pc,
    sqrt_price_x96,
    zero_for_one,
    exact_input,
):
    liquidity_delta = (liquidity * liquidity_delta_pc) // 1000000
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, sqrt_price_x96
    )

    amount_specified = 0
    if exact_input and zero_for_one:
        amount_specified = amount0
    elif exact_input and not zero_for_one:
        amount_specified = amount1
    elif not exact_input and zero_for_one:
        amount_specified = -amount1
    else:
        amount_specified = -amount0

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )
    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )
    assert pytest.approx(result, rel=1e-15) == sqrt_price_x96_next

import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_LIQUIDITY
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
    assert amount_specified < 2**96
    zero_for_one = True
    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_input_zero_for_one_amount_greater_than_uint96(
    sqrt_price_math_lib,
):
    liquidity = 2**128 - 1
    sqrt_price_x96 = MAX_SQRT_RATIO - 1

    amount_specified = 2**112
    zero_for_one = True

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
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
    assert amount_specified < 2**160
    zero_for_one = False

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_input_one_for_zero_amount_greater_than_uint160(
    sqrt_price_math_lib,
):
    liquidity = 2**128 - 1
    sqrt_price_x96 = MIN_SQRT_RATIO

    amount_specified = 2**176
    zero_for_one = False

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
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
    assert (-amount_specified) <= 2**160
    zero_for_one = True

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_output_zero_for_one_amount_greater_than_uint160(
    sqrt_price_math_lib,
):
    liquidity = 2**128 - 1
    sqrt_price_x96 = MAX_SQRT_RATIO - 1

    y = int((liquidity * sqrt_price_x96) // (1 << 96))
    amount_specified = -((y * 3) // 4)  # 75%
    assert (-amount_specified) >= 2**160

    zero_for_one = True

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
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
    assert (-amount_specified) < 2**96
    zero_for_one = False

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
    )  # TQ: is this enough?


def test_sqrt_price_math_sqrt_price_x96_next_swap__with_exact_output_one_for_zero_amount_greater_than_uint96(
    sqrt_price_math_lib,
):
    liquidity = 2**128 - 1
    sqrt_price_x96 = MIN_SQRT_RATIO

    x = int((liquidity * (1 << 96)) // sqrt_price_x96)
    amount_specified = -((x * 3) // 4)  # 75%
    assert (-amount_specified) >= 2**96

    zero_for_one = False

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert (
        pytest.approx(result, rel=1e-14) == sqrt_price_x96_next
    )  # TQ: is this enough?


@pytest.mark.fuzzing
@given(
    liquidity=st.integers(min_value=MINIMUM_LIQUIDITY, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    zero_for_one=st.booleans(),
    amount_specified=st.integers(min_value=-(2**255 - 1), max_value=2**255 - 1),
)
def test_sqrt_price_math_sqrt_price_x96_next_swap__with_fuzz(
    sqrt_price_math_lib,
    liquidity,
    sqrt_price_x96,
    zero_for_one,
    amount_specified,
):
    # ignore cases where actual reserves are zero
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    if reserve0 == 0 or reserve1 == 0:
        return

    # ignore cases where amount specified not valid
    if amount_specified == 0:
        return
    elif amount_specified < 0 and not zero_for_one and -amount_specified >= reserve0:
        return
    elif amount_specified < 0 and zero_for_one and -amount_specified >= reserve1:
        return

    sqrt_price_x96_next = calc_sqrt_price_x96_next_swap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    # exit out if calculated sqrt price is out of tick range bounds
    if sqrt_price_x96_next <= MIN_SQRT_RATIO or sqrt_price_x96_next >= MAX_SQRT_RATIO:
        return

    result = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    assert pytest.approx(result, rel=1e-6, abs=1) == sqrt_price_x96_next

import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_swap_amounts


def test_swap_math_swap_amounts__with_exact_input_zero_for_one(
    swap_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = x * 1 // 100  # 1% of reserves in
    zero_for_one = True
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = swap_math_lib.swapAmounts(liquidity, sqrt_price_x96, sqrt_price_x96_next)
    (amount0_delta, amount1_delta) = calc_swap_amounts(
        liquidity, sqrt_price_x96, sqrt_price_x96_next
    )
    assert pytest.approx(result[0], rel=1e-15) == amount0_delta
    assert pytest.approx(result[1], rel=1e-15) == amount1_delta


def test_swap_math_swap_amounts__with_exact_input_one_for_zero(
    swap_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = y * 1 // 100  # 1% of reserves in
    zero_for_one = False
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = swap_math_lib.swapAmounts(liquidity, sqrt_price_x96, sqrt_price_x96_next)
    (amount0_delta, amount1_delta) = calc_swap_amounts(
        liquidity, sqrt_price_x96, sqrt_price_x96_next
    )
    assert pytest.approx(result[0], rel=1e-15) == amount0_delta
    assert pytest.approx(result[1], rel=1e-15) == amount1_delta


def test_swap_math_swap_amounts__with_exact_output_zero_for_one(
    swap_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = -y * 1 // 100  # 1% of reserves in
    zero_for_one = True
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = swap_math_lib.swapAmounts(liquidity, sqrt_price_x96, sqrt_price_x96_next)
    (amount0_delta, amount1_delta) = calc_swap_amounts(
        liquidity, sqrt_price_x96, sqrt_price_x96_next
    )

    assert pytest.approx(result[0], rel=1e-15) == amount0_delta
    assert pytest.approx(result[1], rel=1e-15) == amount1_delta


def test_swap_math_swap_amounts__with_exact_output_one_for_zero(
    swap_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    amount_specified = -x * 1 // 100  # 1% of reserves in
    zero_for_one = False
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        liquidity, sqrt_price_x96, zero_for_one, amount_specified
    )

    result = swap_math_lib.swapAmounts(liquidity, sqrt_price_x96, sqrt_price_x96_next)
    (amount0_delta, amount1_delta) = calc_swap_amounts(
        liquidity, sqrt_price_x96, sqrt_price_x96_next
    )

    assert pytest.approx(result[0], rel=1e-15) == amount0_delta
    assert pytest.approx(result[1], rel=1e-15) == amount1_delta


@pytest.mark.fuzzing
@given(
    liquidity=st.integers(min_value=1000, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    sqrt_price_x96_next=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
)
def test_swap_math_swap_amounts__with_fuzz(
    swap_math_lib, liquidity, sqrt_price_x96, sqrt_price_x96_next
):
    result = swap_math_lib.swapAmounts(liquidity, sqrt_price_x96, sqrt_price_x96_next)
    (amount0_delta, amount1_delta) = calc_swap_amounts(
        liquidity, sqrt_price_x96, sqrt_price_x96_next
    )
    assert pytest.approx(result[0], rel=1e-15) == amount0_delta
    assert pytest.approx(result[1], rel=1e-15) == amount1_delta

import pytest
from ape import reverts

from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MINIMUM_LIQUIDITY,
    MINIMUM_SIZE,
)
from utils.utils import calc_liquidity_sqrt_price_x96_from_reserves


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_positive_amount1_positive(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics mint
    amount0 = reserve0 * 100 // 10000  # 1% of liquidity added
    amount1 = reserve1 * 100 // 10000  # 1% of liquidity added

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )
    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_negative_amount1_negative(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics burn
    amount0 = -reserve0 * 100 // 10000  # 1% of liquidity removed
    amount1 = -reserve1 * 100 // 10000  # 1% of liquidity removed

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )
    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_positive_amount1_negative(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics swap of zero for one
    amount0 = reserve0 * 100 // 10000  # 1% of liquidity added
    amount1 = (
        liquidity**2 // (reserve0 + amount0) - reserve1
    )  # ~1% of liquidity removed

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_negative_amount1_positive(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics swap of one for zero
    amount0 = -reserve0 * 100 // 10000  # 1% of liquidity removed
    amount1 = (
        liquidity**2 // (reserve0 + amount0) - reserve1
    )  # ~1% of liquidity added

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_positive_amount1_zero(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics adding fees
    amount0 = reserve0 * 1 // 10000  # 0.01% of liquidity added
    amount1 = 0

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_zero_amount1_positive(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics adding fees
    amount0 = 0
    amount1 = reserve1 * 1 // 10000  # 0.01% of liquidity added

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__reverts_when_amount1_out_greater_than_reserve(
    liquidity_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(x, y)
    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)

    amount0 = reserve0 * 100 // 10000  # 1% of liquidity added
    amount1 = -reserve1

    with reverts(sqrt_price_math_lib.Amount1ExceedsReserve1):
        liquidity_math_lib.liquiditySqrtPriceX96Next(
            liquidity,
            sqrt_price_x96,
            amount0,
            amount1,
        )


def test_liquidity_math_liquidity_sqrt_price_x96_next__reverts_when_amount0_out_greater_than_reserve(
    liquidity_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(x, y)
    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)

    amount0 = -reserve0
    amount1 = reserve1 * 100 // 10000  # 1% of liquidity added

    with reverts(sqrt_price_math_lib.Amount0ExceedsReserve0):
        liquidity_math_lib.liquiditySqrtPriceX96Next(
            liquidity,
            sqrt_price_x96,
            amount0,
            amount1,
        )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=MINIMUM_LIQUIDITY, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    amount0=st.integers(min_value=-(2**255), max_value=2**255 - 1),
    amount1=st.integers(min_value=-(2**255), max_value=2**255 - 1),
)
def test_liquidity_math_liquidity_sqrt_price_x96_next__with_fuzz(
    liquidity_math_lib,
    liquidity,
    sqrt_price_x96,
    amount0,
    amount1,
):
    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)
    if reserve0 < MINIMUM_SIZE or reserve1 < MINIMUM_SIZE:
        # @dev ignore dust
        return
    elif reserve0 + amount0 <= 0 or reserve1 + amount1 <= 0:
        return

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )
    if liquidity_next >= 2**128:
        return
    elif (
        sqrt_price_x96_next <= 1.0001 * MIN_SQRT_RATIO
        or sqrt_price_x96_next >= 0.9999 * MAX_SQRT_RATIO
    ):
        return

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )
    assert pytest.approx(result[0], rel=1e-6, abs=1) == liquidity_next
    assert pytest.approx(result[1], rel=1e-6, abs=1) == sqrt_price_x96_next

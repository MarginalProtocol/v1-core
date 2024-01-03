import pytest

from datetime import timedelta
from hypothesis import given, settings
from hypothesis import strategies as st
from math import sqrt

from utils.constants import (
    MINIMUM_LIQUIDITY,
    MINIMUM_SIZE,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
)
from utils.utils import calc_sqrt_price_x96_next_open, calc_insurances, calc_debts


def test_position_debt_plus_insurance_product__with_zero_for_one(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    result = int(sqrt((insurance0 + debt0) * (insurance1 + debt1)))

    assert pytest.approx(result, rel=1e-13) == liquidity_delta  # TODO: rel error ok?


def test_position_debt_plus_insurance_product__with_one_for_zero(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    result = int(sqrt((insurance0 + debt0) * (insurance1 + debt1)))

    assert pytest.approx(result, rel=1e-13) == liquidity_delta  # TODO: rel error ok?


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@settings(deadline=timedelta(milliseconds=1000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=MINIMUM_LIQUIDITY + 2, max_value=2**128 - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    zero_for_one=st.booleans(),
)
def test_position_debt_plus_insurance_product__with_fuzz(
    position_lib,
    sqrt_price_math_lib,
    liquidity,
    liquidity_delta_pc,
    sqrt_price_x96,
    zero_for_one,
    maintenance,
):
    liquidity_delta_max = liquidity - MINIMUM_LIQUIDITY - 1
    liquidity_delta = (liquidity_delta_max * liquidity_delta_pc) // 1000000000
    if liquidity_delta == 0:
        return

    calc_sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    if (
        calc_sqrt_price_x96_next < MIN_SQRT_RATIO
        or calc_sqrt_price_x96_next >= MAX_SQRT_RATIO
    ):
        return

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    # calculate insurance, debt values first to check will fit in uint128
    calc_insurance0, calc_insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    calc_debt0, calc_debt1 = calc_debts(
        sqrt_price_x96_next, liquidity_delta, calc_insurance0, calc_insurance1
    )
    if (
        calc_insurance0 <= 0
        or calc_insurance0 >= 2**128
        or calc_insurance1 <= 0
        or calc_insurance1 >= 2**128
    ):
        return
    elif (
        calc_debt0 <= 0
        or calc_debt0 >= 2**128
        or calc_debt1 <= 0
        or calc_debt1 >= 2**128
    ):
        return

    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )

    result = int(sqrt((insurance0 + debt0) * (insurance1 + debt1)))

    if not (
        insurance0 >= MINIMUM_SIZE
        and debt0 >= MINIMUM_SIZE
        and insurance1 >= MINIMUM_SIZE
        and debt1 >= MINIMUM_SIZE
    ):
        # ignore dust sizes
        return

    assert pytest.approx(result, rel=1e-4) == liquidity_delta

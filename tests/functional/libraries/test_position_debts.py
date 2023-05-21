import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_sqrt_price_x96_next, calc_insurances, calc_debts


def test_position_debts__with_zero_for_one(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = calc_debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )

    result = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    assert result[0] == debt0
    assert result[1] == debt1


# TODO: test invariant of (ix + dx) * (iy + dy)


def test_position_debts__with_one_for_zero(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = calc_debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )

    result = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    assert result[0] == debt0
    assert result[1] == debt1


@pytest.mark.fuzzing
@given(
    liquidity=st.integers(
        min_value=1000, max_value=2**128 - 1
    ),  # TODO: fix min value
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    sqrt_price_x96_next=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000 - 1),
    zero_for_one=st.booleans(),
)
def test_position_debts__with_fuzz(
    position_lib,
    liquidity,
    sqrt_price_x96,
    sqrt_price_x96_next,
    liquidity_delta_pc,
    zero_for_one,
):
    liquidity_delta = (liquidity * liquidity_delta_pc) // 1000000
    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = calc_debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    result = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    assert result[0] == debt0
    assert result[1] == debt1

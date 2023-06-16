import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MAINTENANCE_UNIT, MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_sqrt_price_x96_next_open, calc_tick_from_sqrt_price_x96


# TODO: test for large and small sqrt price x96 values


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_less_than_uint128_with_zero_for_one(
    position_lib, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    zero_for_one = True
    tick_cumulative = 0
    oracle_tick_cumulative = 0

    liquidity_delta = liquidity * 5 // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt0_adjusted * (sqrt_price_x96**2)) // (1 << 192) - position.size
    if margin_min < 0:
        margin_min = 0

    assert (
        pytest.approx(position_lib.marginMinimum(position, maintenance), rel=1e-3)
        == margin_min
    )  # TODO: rel tol too low?


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_less_than_uint128_with_one_for_zero(
    position_lib, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    tick_cumulative = 0
    oracle_tick_cumulative = 0

    liquidity_delta = liquidity * 5 // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt1_adjusted * (1 << 192)) // (sqrt_price_x96**2) - position.size
    if margin_min < 0:
        margin_min = 0

    assert (
        pytest.approx(position_lib.marginMinimum(position, maintenance), rel=1e-3)
        == margin_min
    )  # TODO: rel tol too low?


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_greater_than_uint128_with_zero_for_one(
    position_lib, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(3.30e39)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    zero_for_one = True
    tick_cumulative = 0
    oracle_tick_cumulative = 0

    liquidity_delta = liquidity * 5 // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt0_adjusted * (sqrt_price_x96**2)) // (1 << 192) - position.size
    if margin_min < 0:
        margin_min = 0

    assert (
        pytest.approx(position_lib.marginMinimum(position, maintenance), rel=1e-3)
        == margin_min
    )  # TODO: rel tol too low?


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_greater_than_uint128_with_one_for_zero(
    position_lib, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(3.30e39)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    tick_cumulative = 0
    oracle_tick_cumulative = 0

    liquidity_delta = liquidity * 5 // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt1_adjusted * (1 << 192)) // (sqrt_price_x96**2) - position.size
    if margin_min < 0:
        margin_min = 0

    assert (
        pytest.approx(position_lib.marginMinimum(position, maintenance), rel=1e-3)
        == margin_min
    )  # TODO: rel tol too low?


# TODO: fix for anvil issues
@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@given(
    liquidity=st.integers(
        min_value=1000, max_value=2**128 - 1
    ),  # TODO: fix min value
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    sqrt_price_x96_next=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000 - 1),
    zero_for_one=st.booleans(),
)
def test_position_margin_minimum__with_fuzz(
    position_lib,
    liquidity,
    sqrt_price_x96,
    sqrt_price_x96_next,
    liquidity_delta_pc,
    zero_for_one,
    maintenance,
):
    # TODO: implement
    pass

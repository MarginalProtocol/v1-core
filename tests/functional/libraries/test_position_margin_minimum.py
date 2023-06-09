import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MAINTENANCE_UNIT, MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_sqrt_price_x96_next_open


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__with_zero_for_one(position_lib, maintenance):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
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
        tick_cumulative,
        oracle_tick_cumulative,
    )

    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (
        debt0_adjusted * position.insurance1
    ) // position.insurance0 - position.size
    if margin_min < 0:
        margin_min = 0

    assert position_lib.marginMinimum(position, maintenance) == margin_min


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__with_one_for_zero(position_lib, maintenance):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False
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
        tick_cumulative,
        oracle_tick_cumulative,
    )

    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (
        debt1_adjusted * position.insurance0
    ) // position.insurance1 - position.size
    if margin_min < 0:
        margin_min = 0

    assert position_lib.marginMinimum(position, maintenance) == margin_min


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
    liquidity_delta = (liquidity * liquidity_delta_pc) // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    tick_cumulative = 0
    oracle_tick_cumulative = 0

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    debt = position.debt0 if zero_for_one else position.debt1
    debt_adjusted = debt * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT

    margin_min = (
        (debt_adjusted * position.insurance1) // position.insurance0 - position.size
        if zero_for_one
        else (debt_adjusted * position.insurance0) // position.insurance1
        - position.size
    )
    if margin_min < 0:
        margin_min = 0

    result = position_lib.marginMinimum(position, maintenance)
    assert result == margin_min

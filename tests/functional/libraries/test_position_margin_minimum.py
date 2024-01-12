import pytest

from hypothesis import given, settings, strategies as st
from datetime import timedelta
from math import sqrt

from utils.constants import (
    MAINTENANCE_UNIT,
    MINIMUM_SIZE,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MINIMUM_LIQUIDITY,
)
from utils.utils import (
    calc_sqrt_price_x96_next_open,
    calc_tick_from_sqrt_price_x96,
    calc_debts,
    calc_insurances,
    calc_margin_minimum,
)


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_less_than_uint128_with_zero_for_one(
    position_lib,
    maintenance,
    tick_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    zero_for_one = True
    block_timestamp = 1684675403
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
        block_timestamp,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    _sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(
        tick
    )  # @dev slight shift due to gas savings in storing tick

    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt0_adjusted * (_sqrt_price_x96**2)) // (1 << 192) - position.size
    if margin_min < 0:
        margin_min = 0

    result = position_lib.marginMinimum(position, maintenance)
    assert pytest.approx(result, rel=1e-6) == margin_min

    # sanity check that margin min >= M * size
    assert result >= (position.size * maintenance // MAINTENANCE_UNIT)

    # sanity check that min margin is
    #   cx_min = size * ((1+M) * sqrt(P'/P) - 1) for one for zero
    #   cy_min = size * ((1+M) * sqrt(P/P') - 1) for zero for one
    sqrt_price_slippage = (
        sqrt_price_x96_next / sqrt_price_x96
        if not zero_for_one
        else sqrt_price_x96 / sqrt_price_x96_next
    )
    margin_slippage = (1 + maintenance / MAINTENANCE_UNIT) * sqrt_price_slippage - 1
    expected_margin_min = int(position.size * margin_slippage)
    assert pytest.approx(result, rel=1e-3) == expected_margin_min


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_less_than_uint128_with_one_for_zero(
    position_lib,
    maintenance,
    tick_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False
    block_timestamp = 1684675403
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
        block_timestamp,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    _sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(
        tick
    )  # @dev slight shift due to gas savings in storing tick

    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt1_adjusted * (1 << 192)) // (_sqrt_price_x96**2) - position.size
    if margin_min < 0:
        margin_min = 0

    result = position_lib.marginMinimum(position, maintenance)
    assert pytest.approx(result, rel=1e-6) == margin_min

    # sanity check that margin min >= M * size
    assert result >= (position.size * maintenance // MAINTENANCE_UNIT)

    # sanity check that min margin is
    #   cx_min = size * ((1+M) * sqrt(P'/P) - 1) for one for zero
    #   cy_min = size * ((1+M) * sqrt(P/P') - 1) for zero for one
    sqrt_price_slippage = (
        sqrt_price_x96_next / sqrt_price_x96
        if not zero_for_one
        else sqrt_price_x96 / sqrt_price_x96_next
    )
    margin_slippage = (1 + maintenance / MAINTENANCE_UNIT) * sqrt_price_slippage - 1
    expected_margin_min = int(position.size * margin_slippage)
    assert pytest.approx(result, rel=1e-3) == expected_margin_min


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_greater_than_uint128_with_zero_for_one(
    position_lib,
    maintenance,
    tick_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(3.30e39)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    zero_for_one = True
    block_timestamp = 1684675403
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
        block_timestamp,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    _sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(
        tick
    )  # @dev slight shift due to gas savings in storing tick

    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt0_adjusted * (_sqrt_price_x96**2)) // (1 << 192) - position.size
    if margin_min < 0:
        margin_min = 0

    result = position_lib.marginMinimum(position, maintenance)
    assert pytest.approx(result, rel=1e-6) == margin_min

    # sanity check that margin min >= M * size
    assert result >= (position.size * maintenance // MAINTENANCE_UNIT)

    # sanity check that min margin is
    #   cx_min = size * ((1+M) * sqrt(P'/P) - 1) for one for zero
    #   cy_min = size * ((1+M) * sqrt(P/P') - 1) for zero for one
    sqrt_price_slippage = (
        sqrt_price_x96_next / sqrt_price_x96
        if not zero_for_one
        else sqrt_price_x96 / sqrt_price_x96_next
    )
    margin_slippage = (1 + maintenance / MAINTENANCE_UNIT) * sqrt_price_slippage - 1
    expected_margin_min = int(position.size * margin_slippage)
    assert pytest.approx(result, rel=1e-3) == expected_margin_min


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__when_sqrt_price_x96_greater_than_uint128_with_one_for_zero(
    position_lib,
    maintenance,
    tick_math_lib,
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(3.30e39)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False
    block_timestamp = 1684675403
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
        block_timestamp,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    _sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(
        tick
    )  # @dev slight shift due to gas savings in storing tick

    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    margin_min = (debt1_adjusted * (1 << 192)) // (_sqrt_price_x96**2) - position.size
    if margin_min < 0:
        margin_min = 0

    result = position_lib.marginMinimum(position, maintenance)
    assert pytest.approx(result, rel=1e-6) == margin_min

    # sanity check that margin min >= M * size
    assert result >= (position.size * maintenance // MAINTENANCE_UNIT)

    # sanity check that min margin is
    #   cx_min = size * ((1+M) * sqrt(P'/P) - 1) for one for zero
    #   cy_min = size * ((1+M) * sqrt(P/P') - 1) for zero for one
    sqrt_price_slippage = (
        sqrt_price_x96_next / sqrt_price_x96
        if not zero_for_one
        else sqrt_price_x96 / sqrt_price_x96_next
    )
    margin_slippage = (1 + maintenance / MAINTENANCE_UNIT) * sqrt_price_slippage - 1
    expected_margin_min = int(position.size * margin_slippage)
    assert pytest.approx(result, rel=1e-3) == expected_margin_min


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@settings(deadline=timedelta(milliseconds=2000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=1, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000 - 1),
    zero_for_one=st.booleans(),
    factor=st.floats(min_value=0.5, max_value=2.0),
)
def test_position_margin_minimum__with_fuzz(
    position_lib,
    tick_math_lib,
    liquidity,
    sqrt_price_x96,
    liquidity_delta_pc,
    zero_for_one,
    maintenance,
    factor,
):
    liquidity_delta = (liquidity * liquidity_delta_pc) // 1000000000
    if liquidity_delta >= liquidity - MINIMUM_LIQUIDITY:
        return

    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    if (
        sqrt_price_x96_next <= MIN_SQRT_RATIO
        or sqrt_price_x96_next >= MAX_SQRT_RATIO - 1
    ):
        return
    elif (sqrt_price_x96_next > sqrt_price_x96 and zero_for_one) or (
        sqrt_price_x96_next < sqrt_price_x96 and not zero_for_one
    ):
        return

    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    if insurance0 >= 2**128 or insurance1 >= 2**128:
        return
    elif insurance0 < MINIMUM_SIZE or insurance1 < MINIMUM_SIZE:
        # @dev rounding issues for tiny del L / L (1e-17) values can cause negative insurances that underflow revert
        return

    debt0, debt1 = calc_debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    if debt0 >= 2**128 or debt1 >= 2**128:
        return
    elif debt0 < MINIMUM_SIZE or debt1 < MINIMUM_SIZE:
        return

    if not zero_for_one:
        size = (liquidity * (1 << 96)) // sqrt_price_x96 - (
            liquidity * (1 << 96)
        ) // sqrt_price_x96_next
    else:
        size = (liquidity * (sqrt_price_x96 - sqrt_price_x96_next)) // (1 << 96)

    if size < MINIMUM_SIZE or size >= 2**128:
        return

    # assemble position
    tick = tick_math_lib.getTickAtSqrtRatio(sqrt_price_x96)
    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        0,
        0,
        0,
    )

    if (
        position.size < MINIMUM_SIZE
        or position.debt0 < MINIMUM_SIZE
        or position.debt1 < MINIMUM_SIZE
        or position.insurance0 < MINIMUM_SIZE
        or position.insurance1 < MINIMUM_SIZE
    ):
        return

    # manually adjust position for funding with a factor on debt
    debt0_adjusted = int(factor * position.debt0) if zero_for_one else position.debt0
    debt1_adjusted = position.debt1 if zero_for_one else int(factor * position.debt1)
    if debt0_adjusted >= 2**128 or debt1_adjusted >= 2**128:
        return

    position.debt0 = debt0_adjusted
    position.debt1 = debt1_adjusted

    # calc expected margin minimum
    _sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(
        tick
    )  # @dev slight shift due to gas savings in storing tick
    margin_min = calc_margin_minimum(
        position.size,
        position.debt0,
        position.debt1,
        zero_for_one,
        maintenance,
        _sqrt_price_x96,
    )
    if margin_min < 0:
        margin_min = 0
    elif margin_min >= 2**124:  # to be ultra safe no revert issues
        return

    # sanity check that min margin is
    #   cx_min = size * ((1+M) * factor * sqrt(P'/P) - 1) for one for zero
    #   cy_min = size * ((1+M) * factor * sqrt(P/P') - 1) for zero for one
    sqrt_price_slippage = (
        sqrt_price_x96_next / sqrt_price_x96
        if not zero_for_one
        else sqrt_price_x96 / sqrt_price_x96_next
    )
    margin_slippage = (
        1 + maintenance / MAINTENANCE_UNIT
    ) * factor * sqrt_price_slippage - 1
    expected_margin_min = int(position.size * margin_slippage)
    if expected_margin_min < 0:
        expected_margin_min = 0
    elif margin_slippage < 1e-3:
        # @dev produces near zero margin requirement relative to size so trader can effectively pull almost all margin
        return

    result = position_lib.marginMinimum(position, maintenance)
    assert pytest.approx(result, rel=1e-6, abs=1) == margin_min
    assert pytest.approx(result, rel=5e-2, abs=1) == expected_margin_min

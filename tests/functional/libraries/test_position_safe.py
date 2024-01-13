import pytest

from hypothesis import given, settings, strategies as st
from datetime import timedelta
from math import sqrt

from utils.constants import (
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    TICK_CUMULATIVE_RATE_MAX,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    REWARD_PREMIUM,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MINIMUM_LIQUIDITY,
    MINIMUM_SIZE,
)
from utils.utils import (
    calc_sqrt_price_x96_next_open,
    calc_tick_from_sqrt_price_x96,
    calc_debts,
    calc_insurances,
    calc_margin_minimum,
)


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_unsafe_without_funding_with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M - err term) so slightly less than safe limit
    debt_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted * price) - position.size
    position.margin = int(position.margin * 0.999)

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is False


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_unsafe_without_funding_with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M - err term) so slightly less than safe limit
    debt_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted / price) - position.size
    position.margin = int(position.margin * 0.999)

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is False


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_safe_without_funding_with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M + err term) so slightly more than safe limit
    debt_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted * price) - position.size
    position.margin = int(position.margin * 1.001)

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is True


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_safe_without_funding_with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M + err term) so slightly more than safe limit
    debt_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted / price) - position.size
    position.margin = int(position.margin * 1.001)

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is True


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_unsafe_with_funding_with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M + err term) so slightly more than safe limit to start
    debt_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted * price) - position.size
    position.margin = int(position.margin * 1.001)

    # funding over time makes position unsafe
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * 1.1)
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )

    position = position_lib.sync(
        position,
        block_timestamp_last,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is False


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_unsafe_with_funding_with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M + err term) so slightly more than safe limit
    debt_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted / price) - position.size
    position.margin = int(position.margin * 1.001)

    # funding over time makes position unsafe
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * 0.9)
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )

    position = position_lib.sync(
        position,
        block_timestamp_last,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is False


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_safe_with_funding_with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M + err term) so slightly less than safe limit to start
    debt_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted * price) - position.size
    position.margin = int(position.margin * 0.999)

    # funding over time makes position safer
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * 0.9)
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )

    position = position_lib.sync(
        position,
        block_timestamp_last,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is True


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_safe__when_safe_with_funding_with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

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
        block_timestamp_start,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    # adjust for (1 + M + err term) so slightly less than safe limit
    debt_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted / price) - position.size
    position.margin = int(position.margin * 0.999)

    # funding over time makes position safe
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * 1.1)
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )

    position = position_lib.sync(
        position,
        block_timestamp_last,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
    )
    assert result is True


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@settings(deadline=timedelta(milliseconds=2000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=1, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000 - 1),
    zero_for_one=st.booleans(),
    funding_factor=st.floats(min_value=0.8, max_value=1.2),
    price_factor=st.floats(min_value=0.1, max_value=10.0),
    margin_factor=st.integers(min_value=1.0, max_value=5.0),
)
def test_position_safe__with_fuzz(
    position_lib,
    tick_math_lib,
    liquidity,
    sqrt_price_x96,
    liquidity_delta_pc,
    zero_for_one,
    funding_factor,
    price_factor,
    margin_factor,
    maintenance,
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

    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    # ticks for open and oracle
    tick = tick_math_lib.getTickAtSqrtRatio(sqrt_price_x96)
    _sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(tick)

    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * price_factor)
    oracle_tick = tick_math_lib.getTickAtSqrtRatio(oracle_sqrt_price_x96)
    _oracle_sqrt_price_x96 = tick_math_lib.getSqrtRatioAtTick(oracle_tick)

    # assemble position
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

    # calc min margin after open and use to set margin backing position
    calc_margin_min = calc_margin_minimum(
        position.size,
        position.debt0,
        position.debt1,
        zero_for_one,
        maintenance,
        _sqrt_price_x96,
    )
    if (
        calc_margin_min <= 0 or calc_margin_min >= 2**124
    ):  # to be ultra safe no revert issues
        return

    margin_min = position_lib.marginMinimum(position, maintenance)
    position.margin = int(margin_min * margin_factor)

    debt = position.debt0 if zero_for_one else position.debt1
    debt_adjusted = int(debt * funding_factor)

    debt0_adjusted = debt_adjusted if zero_for_one else position.debt0
    debt1_adjusted = position.debt1 if zero_for_one else debt_adjusted

    if debt0_adjusted >= 2**128 or debt1_adjusted >= 2**128:
        return

    position.debt0 = debt0_adjusted
    position.debt1 = debt1_adjusted

    # get min margin based on oracle tick to use in assessing whether safe
    calc_oracle_margin_min = calc_margin_minimum(
        position.size,
        position.debt0,
        position.debt1,
        zero_for_one,
        maintenance,
        _oracle_sqrt_price_x96,
    )

    # position should be safe if margin >= margin_min calculated off of oracle tick
    safe = position.margin >= calc_oracle_margin_min
    result = position_lib.safe(position, _oracle_sqrt_price_x96, maintenance)
    assert result == safe

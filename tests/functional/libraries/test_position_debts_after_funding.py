import pytest

from hypothesis import given, settings, strategies as st
from datetime import timedelta
from math import sqrt

from utils.constants import (
    REWARD_PREMIUM,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    FUNDING_PERIOD,
    TICK_CUMULATIVE_RATE_MAX,
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
)


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@pytest.mark.parametrize("factor", [0.99, 1.0, 1.01])
def test_position_debts_after_funding__with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance, factor
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
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * factor)

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
    position.margin = position_lib.marginMinimum(position, maintenance)

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    tick_cumulative_delta_last = oracle_tick_cumulative_last - tick_cumulative_last

    result = position_lib.debtsAfterFunding(
        position,
        block_timestamp_last,
        tick_cumulative_delta_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    delta = (oracle_tick_cumulative_last - oracle_tick_cumulative_start) - (
        tick_cumulative_last - tick_cumulative_start
    )
    arithmetic_mean_tick = delta // time_delta

    debt0 = int(
        position.debt0
        * (1.0001**arithmetic_mean_tick) ** (time_delta / FUNDING_PERIOD)
    )
    debt1 = int(position.debt1)

    assert pytest.approx(result.debt0, rel=1e-13) == debt0
    assert result.debt1 == debt1


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@pytest.mark.parametrize("factor", [0.99, 1.0, 1.01])
def test_position_debts_after_funding__with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance, factor
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
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * factor)

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
    position.margin = position_lib.marginMinimum(position, maintenance)

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    tick_cumulative_delta_last = oracle_tick_cumulative_last - tick_cumulative_last
    result = position_lib.debtsAfterFunding(
        position,
        block_timestamp_last,
        tick_cumulative_delta_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    delta = (tick_cumulative_last - tick_cumulative_start) - (
        oracle_tick_cumulative_last - oracle_tick_cumulative_start
    )
    arithmetic_mean_tick = delta // time_delta

    debt0 = int(position.debt0)
    debt1 = int(
        position.debt1
        * (1.0001**arithmetic_mean_tick) ** (time_delta / FUNDING_PERIOD)
    )

    assert result.debt0 == debt0
    assert pytest.approx(result.debt1, rel=1e-13) == debt1


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@pytest.mark.parametrize("factor", [0.80, 1.20])
def test_position_debts_after_funding__when_delta_out_of_range_with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance, factor
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
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * factor)

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
    position.margin = position_lib.marginMinimum(position, maintenance)

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    tick_cumulative_delta_last = oracle_tick_cumulative_last - tick_cumulative_last

    result = position_lib.debtsAfterFunding(
        position,
        block_timestamp_last,
        tick_cumulative_delta_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    delta = (oracle_tick_cumulative_last - oracle_tick_cumulative_start) - (
        tick_cumulative_last - tick_cumulative_start
    )
    delta_max = TICK_CUMULATIVE_RATE_MAX * time_delta

    if delta > delta_max:
        delta = delta_max
    elif delta < -delta_max:
        delta = -delta_max

    arithmetic_mean_tick = delta // time_delta

    debt0 = int(
        position.debt0
        * (1.0001**arithmetic_mean_tick) ** (time_delta / FUNDING_PERIOD)
    )
    debt1 = int(position.debt1)

    assert pytest.approx(result.debt0, rel=1e-13) == debt0
    assert result.debt1 == debt1


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@pytest.mark.parametrize("factor", [0.80, 1.20])
def test_position_debts_after_funding__when_delta_out_of_range_with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance, factor
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
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * factor)

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
    position.margin = position_lib.marginMinimum(position, maintenance)

    base_fee = BASE_FEE_MIN * 2
    position.rewards = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    tick_cumulative_delta_last = oracle_tick_cumulative_last - tick_cumulative_last
    result = position_lib.debtsAfterFunding(
        position,
        block_timestamp_last,
        tick_cumulative_delta_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    delta = (tick_cumulative_last - tick_cumulative_start) - (
        oracle_tick_cumulative_last - oracle_tick_cumulative_start
    )
    delta_max = TICK_CUMULATIVE_RATE_MAX * time_delta

    if delta > delta_max:
        delta = delta_max
    elif delta < -delta_max:
        delta = -delta_max

    arithmetic_mean_tick = delta // time_delta

    debt0 = int(position.debt0)
    debt1 = int(
        position.debt1
        * (1.0001**arithmetic_mean_tick) ** (time_delta / FUNDING_PERIOD)
    )

    assert result.debt0 == debt0
    assert pytest.approx(result.debt1, rel=1e-13) == debt1


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@settings(deadline=timedelta(milliseconds=2000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=1, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000 - 1),
    zero_for_one=st.booleans(),
    factor=st.floats(min_value=0.75, max_value=1.25),
    time_delta=st.integers(
        min_value=FUNDING_PERIOD // 10, max_value=100 * FUNDING_PERIOD
    ),  # 16 hours to 2 years
)
def test_position_debts_after_funding__with_fuzz(
    position_lib,
    tick_math_lib,
    rando_univ3_observations,
    liquidity,
    sqrt_price_x96,
    liquidity_delta_pc,
    zero_for_one,
    factor,
    time_delta,
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

    block_timestamp_start = rando_univ3_observations[0][0]
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    oracle_sqrt_price_x96 = int(sqrt_price_x96_next * factor)

    # assemble position
    tick = tick_math_lib.getTickAtSqrtRatio(sqrt_price_x96)
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

    if (
        position.size < MINIMUM_SIZE
        or position.debt0 < MINIMUM_SIZE
        or position.debt1 < MINIMUM_SIZE
        or position.insurance0 < MINIMUM_SIZE
        or position.insurance1 < MINIMUM_SIZE
    ):
        return

    tick_next = tick_math_lib.getTickAtSqrtRatio(sqrt_price_x96_next)
    oracle_tick = tick_math_lib.getTickAtSqrtRatio(oracle_sqrt_price_x96)

    block_timestamp_last = block_timestamp_start + time_delta
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    tick_cumulative_delta_last = oracle_tick_cumulative_last - tick_cumulative_last

    delta = (tick_cumulative_last - tick_cumulative_start) - (
        oracle_tick_cumulative_last - oracle_tick_cumulative_start
    )
    if zero_for_one:
        delta = -delta

    delta_max = TICK_CUMULATIVE_RATE_MAX * time_delta

    if delta > delta_max:
        delta = delta_max
    elif delta < -delta_max:
        delta = -delta_max

    # @dev expect rounding short circuit to zero if delta // (FUNDING_PERIOD // 2)
    if delta // (FUNDING_PERIOD // 2) == 0:
        delta = 0

    arithmetic_mean_tick = delta // time_delta
    debt = position.debt0 if zero_for_one else position.debt1
    debt_adjusted = int(
        debt * (1.0001**arithmetic_mean_tick) ** (time_delta / FUNDING_PERIOD)
    )

    debt0_adjusted = debt_adjusted if zero_for_one else position.debt0
    debt1_adjusted = position.debt1 if zero_for_one else debt_adjusted

    if debt0_adjusted >= 2**128 or debt1_adjusted >= 2**128:
        return

    result = position_lib.debtsAfterFunding(
        position,
        block_timestamp_last,
        tick_cumulative_delta_last,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    assert pytest.approx(result.debt0, rel=1e-4, abs=1) == debt0_adjusted
    assert pytest.approx(result.debt1, rel=1e-4, abs=1) == debt1_adjusted

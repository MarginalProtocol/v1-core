import pytest

from math import sqrt

from utils.constants import REWARD, FUNDING_PERIOD, TICK_CUMULATIVE_RATE_MAX
from utils.utils import calc_sqrt_price_x96_next_open, calc_tick_from_sqrt_price_x96


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
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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

    assert pytest.approx(result.debt0, rel=1e-13) == debt0  # TODO: rel tol ok?
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
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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
    assert pytest.approx(result.debt1, rel=1e-13) == debt1  # TODO: rel tol ok?


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
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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

    assert pytest.approx(result.debt0, rel=1e-13) == debt0  # TODO: rel tol ok?
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
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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
    assert pytest.approx(result.debt1, rel=1e-13) == debt1  # TODO: rel tol ok?


# TODO:
@pytest.mark.fuzzing
def test_position_debts_after_funding__with_fuzz(position_lib):
    pass

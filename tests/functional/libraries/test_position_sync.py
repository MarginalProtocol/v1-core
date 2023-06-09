from math import sqrt

from utils.constants import REWARD, FUNDING_PERIOD
from utils.utils import calc_sqrt_price_x96_next_open, calc_tick_from_sqrt_price_x96


def test_position_sync__with_zero_for_one(position_lib, rando_univ3_observations):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96

    maintenance = 250000
    factor = 1.1

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
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
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.margin = position_lib.marginMinimum(position, maintenance)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )

    result = position_lib.sync(
        position, tick_cumulative_last, oracle_tick_cumulative_last, FUNDING_PERIOD
    )

    debt0, debt1 = position_lib.debtsAfterFunding(
        position, tick_cumulative_last, oracle_tick_cumulative_last, FUNDING_PERIOD
    )
    position.debt0 = debt0
    position.debt1 = debt1
    position.tickCumulativeStart = tick_cumulative_last
    position.oracleTickCumulativeStart = oracle_tick_cumulative_last

    assert result == position


def test_position_sync__with_one_for_zero(position_lib, rando_univ3_observations):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96

    maintenance = 250000
    factor = 0.9

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
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
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.margin = position_lib.marginMinimum(position, maintenance)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )

    result = position_lib.sync(
        position, tick_cumulative_last, oracle_tick_cumulative_last, FUNDING_PERIOD
    )

    debt0, debt1 = position_lib.debtsAfterFunding(
        position, tick_cumulative_last, oracle_tick_cumulative_last, FUNDING_PERIOD
    )
    position.debt0 = debt0
    position.debt1 = debt1
    position.tickCumulativeStart = tick_cumulative_last
    position.oracleTickCumulativeStart = oracle_tick_cumulative_last

    assert result == position

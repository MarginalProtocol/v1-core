import pytest

from math import sqrt

from utils.constants import FEE, REWARD, FUNDING_PERIOD
from utils.utils import calc_sqrt_price_x96_next, calc_tick_from_sqrt_price_x96


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@pytest.mark.parametrize("factor", [0.9, 1.0, 1.1])
def test_position_debts_after_funding__with_zero_for_one(
    position_lib, rando_univ3_observations, maintenance, factor
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
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
    position.margin = position_lib.marginMinimum(position.size, maintenance)
    position.debt1 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    result = position_lib.debtsAfterFunding(
        position, tick_cumulative_last, oracle_tick_cumulative_last, FUNDING_PERIOD
    )

    tick_cumulative_delta = (
        oracle_tick_cumulative_last - oracle_tick_cumulative_start
    ) - (tick_cumulative_last - tick_cumulative_start)
    arithmetic_mean_tick = tick_cumulative_delta // time_delta

    debt0 = int(
        position.debt0
        * (1.0001**arithmetic_mean_tick) ** (time_delta / FUNDING_PERIOD)
    )
    debt1 = int(position.debt1)

    assert pytest.approx(result.debt0, rel=1e-13) == debt0  # TODO: rel tol ok?
    assert result.debt1 == debt1


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@pytest.mark.parametrize("factor", [0.9, 1.0, 1.1])
def test_position_debts_after_funding__with_one_for_zero(
    position_lib, rando_univ3_observations, maintenance, factor
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))

    price = y / x
    sqrt_price = int(sqrt(price))
    sqrt_price_x96 = sqrt_price << 96

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
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
    position.margin = position_lib.marginMinimum(position.size, maintenance)
    position.debt0 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    oracle_tick = calc_tick_from_sqrt_price_x96(oracle_sqrt_price_x96)

    time_delta = FUNDING_PERIOD // 2
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    result = position_lib.debtsAfterFunding(
        position, tick_cumulative_last, oracle_tick_cumulative_last, FUNDING_PERIOD
    )

    tick_cumulative_delta = (tick_cumulative_last - tick_cumulative_start) - (
        oracle_tick_cumulative_last - oracle_tick_cumulative_start
    )
    arithmetic_mean_tick = tick_cumulative_delta // time_delta

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

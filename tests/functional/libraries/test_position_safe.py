import pytest

from math import sqrt

from utils.constants import MAINTENANCE_UNIT, FEE, REWARD, FUNDING_PERIOD
from utils.utils import calc_sqrt_price_x96_next, calc_tick_from_sqrt_price_x96


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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt1 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    # adjust for (1 + M - err term) so slightly less than safe limit
    debt_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted * price) - position.size
    position.margin = int(position.margin * 0.999)

    tick_cumulative_last = tick_cumulative_start
    oracle_tick_cumulative_last = oracle_tick_cumulative_start

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt0 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    # adjust for (1 + M - err term) so slightly less than safe limit
    debt_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted / price) - position.size
    position.margin = int(position.margin * 0.999)

    tick_cumulative_last = tick_cumulative_start
    oracle_tick_cumulative_last = oracle_tick_cumulative_start

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt1 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    # adjust for (1 + M + err term) so slightly more than safe limit
    debt_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted * price) - position.size
    position.margin = int(position.margin * 1.001)

    tick_cumulative_last = tick_cumulative_start
    oracle_tick_cumulative_last = oracle_tick_cumulative_start

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt0 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

    # adjust for (1 + M + err term) so slightly more than safe limit
    debt_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    position.margin = int(debt_adjusted / price) - position.size
    position.margin = int(position.margin * 1.001)

    tick_cumulative_last = tick_cumulative_start
    oracle_tick_cumulative_last = oracle_tick_cumulative_start

    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt1 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt0 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt1 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
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

    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    tick_cumulative_start = rando_univ3_observations[0][1]
    oracle_tick_cumulative_start = rando_univ3_observations[0][1]

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative_start,
        oracle_tick_cumulative_start,
    )
    position.debt0 += position_lib.fees(position.size, FEE)
    position.rewards = position_lib.liquidationRewards(position.size, REWARD)

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
    tick_cumulative_last = tick_cumulative_start + (tick_next * time_delta)
    oracle_tick_cumulative_last = oracle_tick_cumulative_start + (
        oracle_tick * time_delta
    )
    result = position_lib.safe(
        position,
        sqrt_price_x96,
        maintenance,
        tick_cumulative_last,
        oracle_tick_cumulative_last,
        FUNDING_PERIOD,
    )
    assert result is True


# TODO:
@pytest.mark.fuzzing
def test_position_safe__with_fuzz():
    pass

import pytest

from math import sqrt


def test_oracle_library_oracle_sqrt_price_x96__with_tick_cumulative_delta_greater_than_zero(
    oracle_lib, rando_univ3_observations
):
    obs_start = rando_univ3_observations[0]
    obs_end = rando_univ3_observations[1]

    tick_cumulative_start = obs_start[1]
    tick_cumulative_end = obs_end[1]

    tick_cumulative_delta = tick_cumulative_end - tick_cumulative_start
    time_delta = obs_end[0] - obs_start[0]

    arithmetic_mean_tick = tick_cumulative_delta // time_delta
    oracle_sqrt_price_x96 = int(sqrt(1.0001**arithmetic_mean_tick) * (1 << 96))
    result = oracle_lib.oracleSqrtPriceX96(tick_cumulative_delta, time_delta)
    assert pytest.approx(result, rel=1e-11) == oracle_sqrt_price_x96


def test_oracle_library_oracle_sqrt_price_x96__with_tick_cumulative_delta_less_than_zero(
    oracle_lib, rando_univ3_observations
):
    obs_start = rando_univ3_observations[0]
    obs_end = rando_univ3_observations[1]

    tick_cumulative_start = obs_end[1]
    tick_cumulative_end = obs_start[1]

    tick_cumulative_delta = tick_cumulative_end - tick_cumulative_start
    time_delta = obs_end[0] - obs_start[0]

    arithmetic_mean_tick = tick_cumulative_delta // time_delta
    oracle_sqrt_price_x96 = int(sqrt(1.0001**arithmetic_mean_tick) * (1 << 96))
    result = oracle_lib.oracleSqrtPriceX96(tick_cumulative_delta, time_delta)
    assert pytest.approx(result, rel=1e-11) == oracle_sqrt_price_x96


def test_oracle_library_oracle_sqrt_price_x96__with_tick_cumulative_delta_equals_zero(
    oracle_lib, rando_univ3_observations
):
    obs_start = rando_univ3_observations[0]
    obs_end = rando_univ3_observations[1]

    tick_cumulative_delta = 0  # set to zero for test
    time_delta = obs_end[0] - obs_start[0]

    arithmetic_mean_tick = tick_cumulative_delta // time_delta
    oracle_sqrt_price_x96 = int(sqrt(1.0001**arithmetic_mean_tick) * (1 << 96))
    result = oracle_lib.oracleSqrtPriceX96(tick_cumulative_delta, time_delta)
    assert pytest.approx(result, rel=1e-11) == oracle_sqrt_price_x96

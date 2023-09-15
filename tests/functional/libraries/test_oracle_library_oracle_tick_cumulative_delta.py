def test_oracle_library_oracle_tick_cumulative_delta__with_end_greater_than_start(
    oracle_lib, rando_univ3_observations
):
    obs_start = rando_univ3_observations[0]
    obs_end = rando_univ3_observations[1]

    tick_cumulative_start = obs_start[1]
    tick_cumulative_end = obs_end[1]

    tick_cumulative_delta = tick_cumulative_end - tick_cumulative_start

    result = oracle_lib.oracleTickCumulativeDelta(
        tick_cumulative_start, tick_cumulative_end
    )
    assert result == tick_cumulative_delta


def test_oracle_library_oracle_tick_cumulative_delta__with_start_greater_than_end(
    oracle_lib, rando_univ3_observations
):
    obs_start = rando_univ3_observations[0]
    obs_end = rando_univ3_observations[1]

    tick_cumulative_start = obs_end[1]
    tick_cumulative_end = obs_start[1]

    tick_cumulative_delta = tick_cumulative_end - tick_cumulative_start

    result = oracle_lib.oracleTickCumulativeDelta(
        tick_cumulative_start, tick_cumulative_end
    )
    assert result == tick_cumulative_delta


def test_oracle_library_oracle_tick_cumulative_delta__with_overflow(oracle_lib):
    tick_cumulative_start = 2**55 - 1 - 1  # type(int56).max - 1
    tick_cumulative_end = -(2**55 - 1) + 1  # type(int56).min + 1
    tick_cumulative_delta = (tick_cumulative_end - tick_cumulative_start) % 2**55

    result = oracle_lib.oracleTickCumulativeDelta(
        tick_cumulative_start, tick_cumulative_end
    )
    assert result == tick_cumulative_delta


def test_oracle_library_oracle_tick_cumulative_delta__with_underflow(
    oracle_lib, rando_univ3_observations
):
    tick_cumulative_start = -(2**55 - 1) + 1  # type(int56).min + 1
    tick_cumulative_end = 2**55 - 1 - 1  # type(int56).max - 1
    tick_cumulative_delta = -((tick_cumulative_start - tick_cumulative_end) % 2**55)

    result = oracle_lib.oracleTickCumulativeDelta(
        tick_cumulative_start, tick_cumulative_end
    )
    assert result == tick_cumulative_delta

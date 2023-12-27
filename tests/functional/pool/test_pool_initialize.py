import pytest
from math import sqrt

from utils.constants import SECONDS_AGO
from utils.utils import calc_sqrt_price_x96_from_tick, calc_tick_from_sqrt_price_x96


def test_pool_initialize__updates_state(
    another_pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    mock_univ3_pool,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    total_supply = another_pool.totalSupply()
    assert total_supply == 0

    state = another_pool.state()
    assert state.initialized is False
    assert state.sqrtPriceX96 == 0

    # next sqrt price comes from oracle twap
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([SECONDS_AGO, 0])
    oracle_tick_average = (
        oracle_tick_cumulatives[1] - oracle_tick_cumulatives[0]
    ) // SECONDS_AGO

    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(oracle_tick_average)
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    callee.mint(
        another_pool.address,
        alice.address,
        liquidity_delta,
        sender=sender,
    )

    state.sqrtPriceX96 = sqrt_price_x96
    state.liquidity = liquidity_delta
    state.tick = tick
    state.blockTimestamp = chain.blocks.head.timestamp
    state.tickCumulative = 0
    state.feeProtocol = 0
    state.initialized = True

    result = another_pool.state()

    assert pytest.approx(result.sqrtPriceX96, rel=1e-4) == state.sqrtPriceX96
    assert result.totalPositions == state.totalPositions
    assert result.liquidity == state.liquidity
    assert pytest.approx(result.tick, abs=1) == state.tick
    assert result.tickCumulative == state.tickCumulative
    assert result.feeProtocol == state.feeProtocol
    assert result.initialized == state.initialized


def test_pool_initialize__emits_initialize(
    another_pool,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    mock_univ3_pool,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    total_supply = another_pool.totalSupply()
    assert total_supply == 0

    state = another_pool.state()
    assert state.initialized is False
    assert state.sqrtPriceX96 == 0

    tx = callee.mint(
        another_pool.address,
        alice.address,
        liquidity_delta,
        sender=sender,
    )
    state = another_pool.state()

    events = tx.decode_logs(another_pool.Initialize)
    assert len(events) == 1
    event = events[0]

    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.tick == state.tick

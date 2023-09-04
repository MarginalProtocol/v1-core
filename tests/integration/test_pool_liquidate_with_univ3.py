import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    SECONDS_AGO,
    FUNDING_PERIOD,
    TICK_CUMULATIVE_RATE_MAX,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def open_position(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    callee,
    sender,
    chain,
):
    def open(zero_for_one):
        state = mrglv1_pool_initialized_with_liquidity.state()
        maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()

        liquidity_delta = (
            state.liquidity * 500 // 10000
        )  # 5% of pool reserves leveraged
        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

        (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
            liquidity_delta, state.sqrtPriceX96
        )
        amount = amount1 if zero_for_one else amount0

        size = int(
            amount
            * maintenance
            / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
        )  # @dev: this is an approximation
        margin = int(1.25 * size) * maintenance // MAINTENANCE_UNIT

        tx = callee.open(
            mrglv1_pool_initialized_with_liquidity.address,
            callee.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )
        return int(tx.return_value[0])

    yield open


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_pool_liquidate_with_univ3__sets_position(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    callee,
    alice,
    bob,
    chain,
    position_lib,
    liquidity_math_lib,
    open_position,
):
    position_id = open_position(zero_for_one)

    key = get_position_key(callee.address, position_id)
    position = mrglv1_pool_initialized_with_liquidity.positions(key)

    # position should be liquidatable due to funding
    dt = FUNDING_PERIOD * 52  # 1 year later
    chain.mine(deltatime=dt)

    block_timestamp_next = chain.pending_timestamp
    mrglv1_pool_initialized_with_liquidity.liquidate(
        bob.address,
        callee.address,
        position_id,
        sender=alice,
    )

    # sync position for funding
    state = mrglv1_pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = univ3_pool.observe([SECONDS_AGO, 0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[1],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # position should be liquidated so size, debts, insurance => 0
    position = position_lib.liquidate(position)
    assert mrglv1_pool_initialized_with_liquidity.positions(key) == position
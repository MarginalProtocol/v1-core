import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    REWARD,
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
def test_pool_settle_with_univ3__sets_position(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    callee,
    alice,
    sender,
    chain,
    position_lib,
    liquidity_math_lib,
    open_position,
):
    position_id = open_position(zero_for_one)

    key = get_position_key(callee.address, position_id)
    position = mrglv1_pool_initialized_with_liquidity.positions(key)

    dt = FUNDING_PERIOD // 7
    chain.mine(deltatime=dt)

    block_timestamp_next = chain.pending_timestamp

    callee.settle(
        mrglv1_pool_initialized_with_liquidity.address,
        alice.address,
        position_id,
        sender=sender,
    )

    # sync position for funding
    state = mrglv1_pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # position should be settled so size, debts, insurance => 0
    position = position_lib.settle(position)
    assert mrglv1_pool_initialized_with_liquidity.positions(key) == position


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_pool_settle_with_univ3__transfers_funds(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    callee,
    sender,
    chain,
    position_lib,
    liquidity_math_lib,
    mrglv1_token0,
    mrglv1_token1,
    open_position,
):
    position_id = open_position(zero_for_one)

    key = get_position_key(callee.address, position_id)
    position = mrglv1_pool_initialized_with_liquidity.positions(key)

    dt = FUNDING_PERIOD // 7
    chain.mine(deltatime=dt)

    balance0_pool = mrglv1_token0.balanceOf(
        mrglv1_pool_initialized_with_liquidity.address
    )
    balance1_pool = mrglv1_token1.balanceOf(
        mrglv1_pool_initialized_with_liquidity.address
    )

    balance0_sender = mrglv1_token0.balanceOf(sender.address)
    balance1_sender = mrglv1_token1.balanceOf(sender.address)

    block_timestamp_next = chain.pending_timestamp

    callee.settle(
        mrglv1_pool_initialized_with_liquidity.address,
        sender.address,
        position_id,
        sender=sender,
    )

    # sync position for funding
    state = mrglv1_pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    amount0 = (
        position.debt0 if zero_for_one else -(position.size + position.margin + rewards)
    )
    amount1 = (
        -(position.size + position.margin + rewards) if zero_for_one else position.debt1
    )

    assert (
        mrglv1_token0.balanceOf(mrglv1_pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        mrglv1_token1.balanceOf(mrglv1_pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert mrglv1_token0.balanceOf(sender.address) == balance0_sender - amount0
    assert mrglv1_token1.balanceOf(sender.address) == balance1_sender - amount1

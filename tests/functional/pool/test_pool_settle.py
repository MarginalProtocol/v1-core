import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    FUNDING_PERIOD,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    REWARD,
    TICK_CUMULATIVE_RATE_MAX,
)
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
    calc_tick_from_sqrt_price_x96,
    get_position_key,
)


@pytest.fixture
def zero_for_one_position_id(
    pool_initialized_with_liquidity, callee, sender, token0, token1
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    size = int(
        amount1
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # size will be ~ 1%
    margin = (
        int(1.25 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.25x for breathing room

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    return int(tx.return_value[0])


@pytest.fixture
def one_for_zero_position_id(
    pool_initialized_with_liquidity, callee, sender, token0, token1
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    size = int(
        amount0
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # size will be ~ 1%
    margin = (
        int(1.25 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.25x for breathing room

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    return int(tx.return_value[0])


def test_pool_settle__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    # sync state
    block_timestamp_next = chain.pending_timestamp
    state.tickCumulative += state.tick * (block_timestamp_next - state.blockTimestamp)
    state.blockTimestamp = block_timestamp_next

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # position debt + insurance to reserves
    amount0_reserves = position.debt0 + position.insurance0
    amount1_reserves = position.debt1 + position.insurance1
    (
        liquidity_next,
        sqrt_price_x96_next,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0_reserves,
        amount1_reserves,
    )
    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    assert pool_initialized_with_liquidity.state() == state


def test_pool_settle__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    # sync state
    block_timestamp_next = chain.pending_timestamp
    state.tickCumulative += state.tick * (block_timestamp_next - state.blockTimestamp)
    state.blockTimestamp = block_timestamp_next

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # position debt + insurance to reserves
    amount0_reserves = position.debt0 + position.insurance0
    amount1_reserves = position.debt1 + position.insurance1
    (
        liquidity_next,
        sqrt_price_x96_next,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0_reserves,
        amount1_reserves,
    )
    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    assert pool_initialized_with_liquidity.state() == state


def test_pool_settle__updates_liquidity_locked_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    mock_univ3_pool,
    liquidity_math_lib,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    block_timestamp_next = chain.pending_timestamp

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # liquidity locked in position should be removed from locked liquidity
    liquidity_locked -= position.liquidityLocked
    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked


def test_pool_settle__updates_liquidity_locked_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    mock_univ3_pool,
    liquidity_math_lib,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    block_timestamp_next = chain.pending_timestamp

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # liquidity locked in position should be removed from locked liquidity
    liquidity_locked -= position.liquidityLocked
    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked


def test_pool_settle__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
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
    assert pool_initialized_with_liquidity.positions(key) == position


def test_pool_settle__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
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
    assert pool_initialized_with_liquidity.positions(key) == position


def test_pool_settle__transfers_funds_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance0_sender = token0.balanceOf(sender.address)
    balance1_alice = token1.balanceOf(alice.address)

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    # zero (debt) for one (size)
    amount0 = position.debt0
    amount1 = position.size + position.margin + rewards

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool - amount1
    )
    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert token1.balanceOf(alice.address) == balance1_alice + amount1


def test_pool_settle__transfers_funds_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance1_sender = token1.balanceOf(sender.address)
    balance0_alice = token0.balanceOf(alice.address)

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    # one (debt) for zero (size)
    amount0 = position.size + position.margin + rewards
    amount1 = position.debt1

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool - amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )
    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert token0.balanceOf(alice.address) == balance0_alice + amount0


def test_pool_settle__calls_settle_callback_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    tx = callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    # zero (debt) for one (size)
    amount0 = position.debt0
    amount1 = position.size + position.margin + rewards

    events = tx.decode_logs(callee.SettleCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0  # positive since pool receiving
    assert event.amount1Delta == -amount1  # negative since pool sending out
    assert event.sender == sender.address


def test_pool_settle__calls_settle_callback_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    tx = callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    # one (debt) for zero (size)
    amount0 = position.size + position.margin + rewards
    amount1 = position.debt1

    events = tx.decode_logs(callee.SettleCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == -amount0  # negative since pool sending out
    assert event.amount1Delta == amount1  # positive since pool receiving
    assert event.sender == sender.address


def test_pool_settle__emits_settle_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    tx = callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    # zero (debt) for one (size)
    amount0 = position.debt0
    amount1 = position.size + position.margin + rewards

    events = tx.decode_logs(pool_initialized_with_liquidity.Settle)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == zero_for_one_position_id
    assert event.recipient == alice.address
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.amount0 == amount0  # positive since pool receiving
    assert event.amount1 == -amount1  # negative since pool sending out


def test_pool_settle__emits_settle_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    tx = callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([0])
    position = position_lib.sync(
        position,
        block_timestamp_next,
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )
    rewards = position_lib.liquidationRewards(position.size, REWARD)

    # one (debt) for zero (size)
    amount1 = position.debt1
    amount0 = position.size + position.margin + rewards

    events = tx.decode_logs(pool_initialized_with_liquidity.Settle)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == one_for_zero_position_id
    assert event.recipient == alice.address
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.amount0 == -amount0  # negative since pool sending out
    assert event.amount1 == amount1  # positive since pool receiving


def test_pool_settle__reverts_when_not_position_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
):
    with reverts(pool_initialized_with_liquidity.InvalidPosition):
        callee.settle(
            pool_initialized_with_liquidity.address,
            alice.address,
            one_for_zero_position_id + 1,
            sender=sender,
        )


def test_pool_settle__reverts_when_amount0_less_than_min(
    pool_initialized_with_liquidity,
    callee,
    callee_below_min0,
    alice,
    sender,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    size = int(
        amount1
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # size will be ~ 1%
    margin = (
        int(1.25 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.25x for breathing room

    # callee below min0 as owner
    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee_below_min0.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = int(tx.return_value[0])

    with reverts(pool_initialized_with_liquidity.Amount0LessThanMin):
        callee_below_min0.settle(
            pool_initialized_with_liquidity.address,
            alice.address,
            id,
            sender=sender,
        )


def test_pool_settle__reverts_when_amount1_less_than_min(
    pool_initialized_with_liquidity,
    callee,
    callee_below_min1,
    alice,
    sender,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    size = int(
        amount0
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # size will be ~ 1%
    margin = (
        int(1.25 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.25x for breathing room

    # callee below min1 as owner
    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee_below_min1.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = int(tx.return_value[0])

    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
        callee_below_min1.settle(
            pool_initialized_with_liquidity.address,
            alice.address,
            id,
            sender=sender,
        )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000 - 1),
    zero_for_one=st.booleans(),
    margin=st.integers(min_value=0, max_value=2**128 - 1),
)
def test_pool_settle__with_fuzz(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    sqrt_price_math_lib,
    position_lib,
    rando_univ3_observations,
    liquidity_delta_pc,
    zero_for_one,
    margin,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**128 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**128 - 1 - balance1_sender, sender=sender)

    # balances sender
    balance0_sender = token0.balanceOf(sender.address)  # 2**128-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**128-1

    # set up fuzz test of settle with position open
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    reward = pool_initialized_with_liquidity.reward()
    fee = pool_initialized_with_liquidity.fee()

    liquidity_delta = state.liquidity * liquidity_delta_pc // 1000000000
    sqrt_price_limit_x96 = (
        MAX_SQRT_RATIO - 1 if not zero_for_one else MIN_SQRT_RATIO + 1
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    # position assembly
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    rewards = position_lib.liquidationRewards(position.size, reward)
    fees = position_lib.fees(position.size, fee)

    margin_min = position_lib.marginMinimum(position, maintenance)
    balance = balance0_sender if not zero_for_one else balance1_sender

    # adjust in case outside of range where test would pass
    # TODO: address edge when margin -> infty
    if margin_min > 2**128 - 1 or margin + rewards + fees > balance:
        return
    elif margin < margin_min:
        margin = margin_min

    params = (
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
    )
    tx = callee.open(*params, sender=sender)
    id, _, _ = tx.return_value

    # state prior
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    # position prior
    key = get_position_key(callee.address, id)
    position = pool_initialized_with_liquidity.positions(key)

    # oracle updates
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]
    position = position_lib.sync(
        position,
        block_timestamp_next,
        tick_cumulative,
        oracle_tick_cumulative,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # prep for call to settle
    params = (pool_initialized_with_liquidity.address, alice.address, id)
    tx = callee.settle(*params, sender=sender)

    amount0, amount1 = tx.return_value
    assert amount0 == (
        -(position.size + position.margin + rewards)
        if not zero_for_one
        else position.debt0
    )
    assert amount1 == (
        position.debt1
        if not zero_for_one
        else -(position.size + position.margin + rewards)
    )

    # check pool state transition (including liquidity locked update)
    amount0_reserves = position.debt0 + position.insurance0
    amount1_reserves = position.debt1 + position.insurance1

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0_reserves, reserve1 + amount1_reserves
    )
    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next

    result_state = pool_initialized_with_liquidity.state()
    assert pytest.approx(result_state.liquidity, rel=1e-14) == state.liquidity
    assert pytest.approx(result_state.sqrtPriceX96, rel=1e-14) == state.sqrtPriceX96
    assert result_state.tick == state.tick
    assert result_state.blockTimestamp == state.blockTimestamp
    assert result_state.tickCumulative == state.tickCumulative
    assert result_state.totalPositions == state.totalPositions

    liquidity_locked -= position.liquidityLocked
    result_liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    assert result_liquidity_locked == liquidity_locked

    # check position set
    state = result_state
    position = position_lib.settle(position)
    result_position = pool_initialized_with_liquidity.positions(key)
    assert result_position == position

    # check balances
    amount0_sender = -amount0 if zero_for_one else 0
    amount1_sender = 0 if zero_for_one else -amount1

    amount0_alice = 0 if zero_for_one else -amount0
    amount1_alice = -amount1 if zero_for_one else 0

    balance0_pool += amount0
    balance1_pool += amount1
    balance0_sender += amount0_sender
    balance1_sender += amount1_sender
    balance0_alice += amount0_alice
    balance1_alice += amount1_alice

    result_balance0_sender = token0.balanceOf(sender.address)
    result_balance1_sender = token1.balanceOf(sender.address)
    result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    result_balance0_alice = token0.balanceOf(alice.address)
    result_balance1_alice = token1.balanceOf(alice.address)

    assert result_balance0_sender == balance0_sender
    assert result_balance1_sender == balance1_sender
    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool
    assert result_balance0_alice == balance0_alice
    assert result_balance1_alice == balance1_alice

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Settle)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == id
    assert event.recipient == alice.address
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.amount0 == amount0
    assert event.amount1 == amount1

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

import pytest

from ape import reverts

from utils.constants import (
    FUNDING_PERIOD,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
)
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
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
    return int(tx.return_value)


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
    return int(tx.return_value)


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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
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


def test_pool_settle__updates_reserves_locked_with_zero_for_one(
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
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # amounts locked in position should be removed from locked reserves
    (amount0_unlocked, amount1_unlocked) = position_lib.amountsLocked(position)
    assert pool_initialized_with_liquidity.reservesLocked() == (
        reserve0_locked - amount0_unlocked,
        reserve1_locked - amount1_unlocked,
    )


def test_pool_settle__updates_reserves_locked_with_one_for_zero(
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
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # amounts locked in position should be removed from locked reserves
    (amount0_unlocked, amount1_unlocked) = position_lib.amountsLocked(position)
    assert pool_initialized_with_liquidity.reservesLocked() == (
        reserve0_locked - amount0_unlocked,
        reserve1_locked - amount1_unlocked,
    )


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
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
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
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
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
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # zero (debt) for one (size)
    amount0 = position.debt0
    amount1 = position.size + position.margin + position.rewards

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
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # one (debt) for zero (size)
    amount0 = position.size + position.margin + position.rewards
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
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # zero (debt) for one (size)
    amount0 = position.debt0
    amount1 = position.size + position.margin + position.rewards

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
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # one (debt) for zero (size)
    amount0 = position.size + position.margin + position.rewards
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
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # zero (debt) for one (size)
    amount0 = position.debt0
    amount1 = position.size + position.margin + position.rewards

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
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()

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
        state.tickCumulative,
        oracle_tick_cumulatives[0],
        FUNDING_PERIOD,
    )

    # one (debt) for zero (size)
    amount1 = position.debt1
    amount0 = position.size + position.margin + position.rewards

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
    id = int(tx.return_value)

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
    id = int(tx.return_value)

    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
        callee_below_min1.settle(
            pool_initialized_with_liquidity.address,
            alice.address,
            id,
            sender=sender,
        )


# TODO:
@pytest.mark.fuzzing
def test_pool_settle__with_fuzz():
    pass

import pytest

from ape import reverts

from utils.constants import (
    FUNDING_PERIOD,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
)
from utils.utils import (
    get_position_key,
    calc_amounts_from_liquidity_sqrt_price_x96,
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


def test_pool_adjust__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    # sync state
    block_timestamp_next = chain.pending_timestamp
    state.tickCumulative += state.tick * (block_timestamp_next - state.blockTimestamp)
    state.blockTimestamp = block_timestamp_next

    margin_delta = position.margin  # 2xing margin
    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


def test_pool_adjust__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    # sync state
    block_timestamp_next = chain.pending_timestamp
    state.tickCumulative += state.tick * (block_timestamp_next - state.blockTimestamp)
    state.blockTimestamp = block_timestamp_next

    margin_delta = position.margin  # 2xing margin
    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


def test_pool_adjust__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin  # 2xing margin
    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    position = position_lib.sync(
        position,
        state.tickCumulative,
        position.oracleTickCumulativeStart,  # @dev doesn't change given naive mock implementation
        FUNDING_PERIOD,
    )

    # added margin
    position.margin += margin_delta
    assert pool_initialized_with_liquidity.positions(key) == position


def test_pool_adjust__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin  # 2xing margin
    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )

    # sync position for funding
    state = pool_initialized_with_liquidity.state()
    position = position_lib.sync(
        position,
        state.tickCumulative,
        position.oracleTickCumulativeStart,  # @dev doesn't change given naive mock implementation
        FUNDING_PERIOD,
    )

    # added margin
    position.margin += margin_delta
    assert pool_initialized_with_liquidity.positions(key) == position


def test_pool_adjust__transfers_funds_when_add_margin_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin  # 2xing margin
    margin_before = position.margin
    margin_after = margin_before + margin_delta

    balance1_sender = token1.balanceOf(sender.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance1_alice = token1.balanceOf(alice.address)

    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )

    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + margin_delta
    )
    assert token1.balanceOf(sender.address) == balance1_sender - margin_after
    assert token1.balanceOf(alice.address) == balance1_alice + margin_before


def test_pool_adjust__transfers_funds_when_add_margin_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin  # 2xing margin
    margin_before = position.margin
    margin_after = margin_before + margin_delta

    balance0_sender = token0.balanceOf(sender.address)
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance0_alice = token0.balanceOf(alice.address)

    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + margin_delta
    )
    assert token0.balanceOf(sender.address) == balance0_sender - margin_after
    assert token0.balanceOf(alice.address) == balance0_alice + margin_before


def test_pool_adjust__transfers_funds_when_remove_margin_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    # add some margin first given test callee on open only sends min
    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        position.margin,
        sender=sender,
    )
    position = pool_initialized_with_liquidity.positions(key)

    # remove half of newly added margin
    margin_delta = -position.margin // 2
    margin_before = position.margin
    margin_after = margin_before + margin_delta

    balance1_sender = token1.balanceOf(sender.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance1_alice = token1.balanceOf(alice.address)

    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )

    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + margin_delta
    )
    assert token1.balanceOf(sender.address) == balance1_sender - margin_after
    assert token1.balanceOf(alice.address) == balance1_alice + margin_before


def test_pool_adjust__transfers_funds_when_remove_margin_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    # add some margin first given test callee on open only sends min
    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        position.margin,
        sender=sender,
    )
    position = pool_initialized_with_liquidity.positions(key)

    # remove half of newly added margin
    margin_delta = -position.margin // 2
    margin_before = position.margin
    margin_after = margin_before + margin_delta

    balance0_sender = token0.balanceOf(sender.address)
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance0_alice = token0.balanceOf(alice.address)

    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + margin_delta
    )
    assert token0.balanceOf(sender.address) == balance0_sender - margin_after
    assert token0.balanceOf(alice.address) == balance0_alice + margin_before


def test_pool_adjust__calls_adjust_callback_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin // 2
    margin_before = position.margin
    margin_after = margin_before + margin_delta

    tx = callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )
    events = tx.decode_logs(callee.AdjustCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == 0
    assert event.amount1Owed == margin_after
    assert event.sender == sender.address


def test_pool_adjust__calls_adjust_callback_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin // 2
    margin_before = position.margin
    margin_after = margin_before + margin_delta

    tx = callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )
    events = tx.decode_logs(callee.AdjustCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == margin_after
    assert event.amount1Owed == 0
    assert event.sender == sender.address


def test_pool_adjust__emits_adjust_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    margin_delta = position.margin // 2

    tx = callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )
    events = tx.decode_logs(pool_initialized_with_liquidity.Adjust)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == zero_for_one_position_id
    assert event.recipient == alice.address
    assert event.marginAfter == position.margin + margin_delta


def test_pool_adjust__emits_adjust_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    margin_delta = position.margin // 2

    tx = callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )
    events = tx.decode_logs(pool_initialized_with_liquidity.Adjust)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == one_for_zero_position_id
    assert event.recipient == alice.address
    assert event.marginAfter == position.margin + margin_delta


def test_pool_adjust__reverts_when_not_position_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    with reverts("not position"):
        callee.adjust(
            pool_initialized_with_liquidity.address,
            alice.address,
            one_for_zero_position_id + 1,
            -position.margin,
            sender=sender,
        )


# TODO: test with position lib margin min
def test_pool_adjust__reverts_when_margin_out_greater_than_position_margin(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    with reverts("margin < min"):
        callee.adjust(
            pool_initialized_with_liquidity.address,
            alice.address,
            one_for_zero_position_id,
            -(position.margin + 1),
            sender=sender,
        )


def test_pool_adjust_reverts_when_amount1_less_than_margin_adjust_min(
    pool_initialized_with_liquidity,
    callee,
    callee_below_min1,
    sender,
    alice,
    token0,
    token1,
):
    # create new zero for one position owned by callee below min1
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
        callee_below_min1.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = int(tx.return_value)

    key = get_position_key(callee_below_min1.address, id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin
    with reverts("amount1 < min"):
        callee_below_min1.adjust(
            pool_initialized_with_liquidity.address,
            alice.address,
            id,
            margin_delta,
            sender=sender,
        )


def test_pool_adjust_reverts_when_amount0_less_than_margin_adjust_min(
    pool_initialized_with_liquidity,
    callee,
    callee_below_min0,
    sender,
    alice,
    token0,
    token1,
):
    # create new one for zero position owned by callee below min1
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
        callee_below_min0.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = int(tx.return_value)

    key = get_position_key(callee_below_min0.address, id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin
    with reverts("amount0 < min"):
        callee_below_min0.adjust(
            pool_initialized_with_liquidity.address,
            alice.address,
            id,
            margin_delta,
            sender=sender,
        )


# TODO:
@pytest.mark.fuzzing
def test_pool_adjust__with_fuzz():
    pass

import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    FUNDING_PERIOD,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    TICK_CUMULATIVE_RATE_MAX,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import (
    get_position_key,
    calc_amounts_from_liquidity_sqrt_price_x96,
)


@pytest.fixture
def zero_for_one_position_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    id = tx.decode_logs(callee.OpenReturn)[0].id
    return int(id)


@pytest.fixture
def one_for_zero_position_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    chain,
    position_lib,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    id = tx.decode_logs(callee.OpenReturn)[0].id
    return int(id)


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
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    margin_delta = position.margin  # 2xing margin
    tx = callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.AdjustReturn)[0]
    margin0 = return_log.margin0
    margin1 = return_log.margin1

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

    # added margin
    position.margin += margin_delta
    assert pool_initialized_with_liquidity.positions(key) == position
    assert margin0 == 0
    assert margin1 == position.margin


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
    mock_univ3_pool,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    block_timestamp_next = chain.pending_timestamp

    margin_delta = position.margin  # 2xing margin
    tx = callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.AdjustReturn)[0]
    margin0 = return_log.margin0
    margin1 = return_log.margin1

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

    # added margin
    position.margin += margin_delta
    assert pool_initialized_with_liquidity.positions(key) == position
    assert margin0 == position.margin
    assert margin1 == 0


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

    with reverts(pool_initialized_with_liquidity.InvalidPosition):
        callee.adjust(
            pool_initialized_with_liquidity.address,
            alice.address,
            one_for_zero_position_id + 1,
            -position.margin,
            sender=sender,
        )


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

    with reverts(pool_initialized_with_liquidity.MarginLessThanMin):
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
    chain,
    position_lib,
):
    # create new zero for one position owned by callee below min1
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee_below_min1.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    id = int(tx.decode_logs(callee.OpenReturn)[0].id)

    key = get_position_key(callee_below_min1.address, id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin
    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
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
    chain,
    position_lib,
):
    # create new one for zero position owned by callee below min1
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee_below_min0.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    id = int(tx.decode_logs(callee.OpenReturn)[0].id)

    key = get_position_key(callee_below_min0.address, id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_delta = position.margin
    with reverts(pool_initialized_with_liquidity.Amount0LessThanMin):
        callee_below_min0.adjust(
            pool_initialized_with_liquidity.address,
            alice.address,
            id,
            margin_delta,
            sender=sender,
        )


# TODO: test for extreme small (~0) and large (~liquidity) margin_delta values


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000 - 1),
    zero_for_one=st.booleans(),
    margin=st.integers(min_value=0, max_value=2**128 - 1),
    margin_delta_pc=st.integers(min_value=-1000000000, max_value=1000000000000),
)
def test_pool_adjust__with_fuzz(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    alice,
    sender,
    token0,
    token1,
    liquidity_delta_pc,
    zero_for_one,
    margin,
    margin_delta_pc,
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

    # set up fuzz test of adjust with position open
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )
    fees = position_lib.fees(position.size, fee)

    margin_min = position_lib.marginMinimum(position, maintenance)
    balance = balance0_sender if not zero_for_one else balance1_sender

    # adjust in case outside of range where test would pass
    if margin_min > 2**128 - 1 or margin_min == 0:
        return
    elif margin < margin_min:
        margin = margin_min
    elif margin + fees > balance:
        margin = balance - fees

    params = (
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
    )
    tx = callee.open(*params, sender=sender, value=rewards)
    id = int(tx.decode_logs(callee.OpenReturn)[0].id)

    # state prior
    state = pool_initialized_with_liquidity.state()

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
    margin_min = position_lib.marginMinimum(position, maintenance)

    # prep for call to adjust
    balance = balance0_sender if not zero_for_one else balance1_sender
    margin_delta = (position.margin * margin_delta_pc) // 1000000000
    margin = position.margin + margin_delta

    if margin <= margin_min:
        margin_delta = margin_min - position.margin
        margin = margin_min
    elif margin >= balance:
        margin_delta = balance - position.margin
        margin = balance

    if margin_delta > 2**127 - 1 or margin_delta < -(2**127 - 1):
        # revert to chain state prior to fuzz run
        chain.restore(snapshot)
        return

    params = (pool_initialized_with_liquidity.address, alice.address, id, margin_delta)
    tx = callee.adjust(*params, sender=sender)

    return_log = tx.decode_logs(callee.AdjustReturn)[0]
    margin0 = return_log.margin0
    margin1 = return_log.margin1
    assert margin0 == (0 if zero_for_one else margin)
    assert margin1 == (margin if zero_for_one else 0)

    # received amounts
    amount0 = 0 if zero_for_one else position.margin
    amount1 = position.margin if zero_for_one else 0

    # check pool state transition
    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next
    result_state = pool_initialized_with_liquidity.state()
    assert result_state == state

    # check position set
    state = result_state
    position.margin = margin
    result_position = pool_initialized_with_liquidity.positions(key)
    assert result_position == position

    # check balances
    balance0_alice += amount0
    balance1_alice += amount1
    balance0_pool += margin0 - amount0
    balance1_pool += margin1 - amount1
    balance0_sender -= margin0
    balance1_sender -= margin1

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
    events = tx.decode_logs(pool_initialized_with_liquidity.Adjust)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == id
    assert event.recipient == alice.address
    assert event.marginAfter == margin

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

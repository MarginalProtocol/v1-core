import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    FUNDING_PERIOD,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    SECONDS_AGO,
    TICK_CUMULATIVE_RATE_MAX,
    MINIMUM_SIZE,
)
from utils.utils import (
    get_position_key,
    calc_tick_from_sqrt_price_x96,
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
)


@pytest.fixture
def oracle_next_obs_zero_for_one(rando_univ3_observations):
    obs_last = rando_univ3_observations[-1]
    obs_before = rando_univ3_observations[-2]
    tick = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])

    obs_timestamp = obs_last[0] + SECONDS_AGO
    obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick * 120) // 100
    obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
    obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
    return obs


@pytest.fixture
def oracle_next_obs_one_for_zero(rando_univ3_observations):
    obs_last = rando_univ3_observations[-1]
    obs_before = rando_univ3_observations[-2]
    tick = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])

    obs_timestamp = obs_last[0] + SECONDS_AGO
    obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick * 80) // 100
    obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
    obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
    return obs


@pytest.fixture
def zero_for_one_position_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    mock_univ3_pool,
    oracle_next_obs_zero_for_one,
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
        int(1.15 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.15x for breathing room
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

    # change the oracle price up 20% to make the position unsafe
    mock_univ3_pool.pushObservation(*oracle_next_obs_zero_for_one, sender=sender)

    id = tx.decode_logs(callee.OpenReturn)[0].id
    return int(id)


@pytest.fixture
def one_for_zero_position_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    mock_univ3_pool,
    oracle_next_obs_one_for_zero,
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
        int(1.15 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.15x for breathing room
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

    # change the oracle price down 20% to make the position unsafe
    mock_univ3_pool.pushObservation(*oracle_next_obs_one_for_zero, sender=sender)

    id = tx.decode_logs(callee.OpenReturn)[0].id
    return int(id)


@pytest.fixture
def zero_for_one_position_safe_id(
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
        int(1.15 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.15x for breathing room
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
def one_for_zero_position_safe_id(
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
        int(1.15 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.15x for breathing room
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


def test_pool_liquidate__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    reserve0, reserve1 = liquidity_math_lib.toAmounts(
        state.liquidity, state.sqrtPriceX96
    )

    amount0, amount1 = position_lib.amountsLocked(position)
    liquidity_next, sqrt_price_x96_next = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0 + amount0, reserve1 + amount1
    )
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = tick_next
    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative_next

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )
    assert pool_initialized_with_liquidity.state() == state


def test_pool_liquidate__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    reserve0, reserve1 = liquidity_math_lib.toAmounts(
        state.liquidity, state.sqrtPriceX96
    )

    amount0, amount1 = position_lib.amountsLocked(position)
    liquidity_next, sqrt_price_x96_next = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0 + amount0, reserve1 + amount1
    )
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = tick_next
    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative_next

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )

    result = pool_initialized_with_liquidity.state()
    assert result == state


def test_pool_liquidate__updates_liquidity_locked_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )

    liquidity_locked -= position.liquidityLocked

    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked


def test_pool_liquidate__updates_liquidity_locked_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )

    liquidity_locked -= position.liquidityLocked

    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked


def test_pool_liquidate__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    oracle_next_obs_zero_for_one,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    position_liquidated = position_lib.liquidate(position)
    block_timestamp_next = chain.pending_timestamp

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )

    state = pool_initialized_with_liquidity.state()
    tick_cumulative = state.tickCumulative
    obs = oracle_next_obs_zero_for_one  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    position_liquidated.blockTimestamp = block_timestamp_next
    position_liquidated.tickCumulativeDelta = oracle_tick_cumulative - tick_cumulative

    assert pool_initialized_with_liquidity.positions(key) == position_liquidated


def test_pool_liquidate__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    oracle_next_obs_one_for_zero,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    position_liquidated = position_lib.liquidate(position)
    block_timestamp_next = chain.pending_timestamp

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )

    state = pool_initialized_with_liquidity.state()
    tick_cumulative = state.tickCumulative
    obs = oracle_next_obs_one_for_zero  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    position_liquidated.blockTimestamp = block_timestamp_next
    position_liquidated.tickCumulativeDelta = oracle_tick_cumulative - tick_cumulative

    assert pool_initialized_with_liquidity.positions(key) == position_liquidated


def test_pool_liquidate__transfers_funds_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position.rewards

    balancee_pool = pool_initialized_with_liquidity.balance
    balancee_bob = bob.balance

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )

    assert pool_initialized_with_liquidity.balance == balancee_pool - rewards
    assert bob.balance == balancee_bob + rewards


def test_pool_liquidate__transfers_funds_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position.rewards

    balancee_pool = pool_initialized_with_liquidity.balance
    balancee_bob = bob.balance

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )

    assert pool_initialized_with_liquidity.balance == balancee_pool - rewards
    assert bob.balance == balancee_bob + rewards


def test_pool_liquidate__returns_rewards_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position.rewards

    tx = callee.liquidate(
        pool_initialized_with_liquidity.address,
        bob.address,
        callee.address,
        zero_for_one_position_id,
        sender=alice,
    )
    return_log = tx.decode_logs(callee.LiquidateReturn)[0]
    assert return_log.rewards == rewards


def test_pool_liquidate__returns_rewards_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position.rewards

    tx = callee.liquidate(
        pool_initialized_with_liquidity.address,
        bob.address,
        callee.address,
        one_for_zero_position_id,
        sender=alice,
    )
    return_log = tx.decode_logs(callee.LiquidateReturn)[0]
    assert return_log.rewards == rewards


def test_pool_liquidate__emits_liquidate_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position.rewards

    tx = pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )
    events = tx.decode_logs(pool_initialized_with_liquidity.Liquidate)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.owner == callee.address
    assert event.id == zero_for_one_position_id
    assert event.recipient == bob.address
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.rewards == rewards


def test_pool_liquidate__emits_liquidate_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards = position.rewards

    tx = pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )
    events = tx.decode_logs(pool_initialized_with_liquidity.Liquidate)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.owner == callee.address
    assert event.id == one_for_zero_position_id
    assert event.recipient == bob.address
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.rewards == rewards


def test_pool_liquidate__reverts_when_not_position_id(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
):
    id = zero_for_one_position_id + 1
    with reverts(pool_initialized_with_liquidity.InvalidPosition):
        pool_initialized_with_liquidity.liquidate(
            bob.address, callee.address, id, sender=alice
        )


def test_pool_liquidate__reverts_when_liquidated(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
):
    id = zero_for_one_position_id
    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, id, sender=alice
    )

    with reverts(pool_initialized_with_liquidity.InvalidPosition):
        pool_initialized_with_liquidity.liquidate(
            bob.address, callee.address, id, sender=alice
        )


def test_pool_liquidate__reverts_when_position_safe_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_safe_id,
):
    id = zero_for_one_position_safe_id
    with reverts(pool_initialized_with_liquidity.PositionSafe):
        pool_initialized_with_liquidity.liquidate(
            bob.address, callee.address, id, sender=alice
        )


def test_pool_liquidate__reverts_when_position_safe_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_safe_id,
):
    id = one_for_zero_position_safe_id
    with reverts(pool_initialized_with_liquidity.PositionSafe):
        pool_initialized_with_liquidity.liquidate(
            bob.address, callee.address, id, sender=alice
        )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000 - 1),
    zero_for_one=st.booleans(),
    margin_pc=st.integers(min_value=0, max_value=1000000000000),
)
def test_pool_liquidate__with_fuzz(
    pool_initialized_with_liquidity,
    callee,
    alice,
    bob,
    sender,
    token0,
    token1,
    sqrt_price_math_lib,
    position_lib,
    rando_univ3_observations,
    mock_univ3_pool,
    liquidity_delta_pc,
    zero_for_one,
    margin_pc,
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
    premium = pool_initialized_with_liquidity.rewardPremium()
    fee = pool_initialized_with_liquidity.fee()

    liquidity_delta = state.liquidity * liquidity_delta_pc // 1000000000
    sqrt_price_limit_x96 = (
        MAX_SQRT_RATIO - 1 if not zero_for_one else MIN_SQRT_RATIO + 1
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    base_fee = chain.blocks[-1].base_fee

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
    if (
        position.size < MINIMUM_SIZE
        or position.debt0 < MINIMUM_SIZE
        or position.debt1 < MINIMUM_SIZE
        or position.insurance0 < MINIMUM_SIZE
        or position.insurance1 < MINIMUM_SIZE
    ):
        return

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
    # TODO: address edge when margin -> infty
    margin = (position.size * margin_pc) // 1000000000
    if margin_min > 2**128 - 1 or margin_min == 0 or margin + fees > balance:
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
    tx = callee.open(*params, sender=sender, value=rewards)
    id = int(tx.decode_logs(callee.OpenReturn)[0].id)

    # state prior
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    # balances prior
    balancee_pool = pool_initialized_with_liquidity.balance
    balancee_bob = bob.balance

    # position prior
    key = get_position_key(callee.address, id)
    position = pool_initialized_with_liquidity.positions(key)

    # calculate extreme next oracle tick
    obs_last = rando_univ3_observations[-1]
    obs_before = rando_univ3_observations[-2]
    tick_oracle = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])
    tick_bankrupt = 2 * tick_oracle if zero_for_one else 0

    # set oracle to bankruptcy price to make position unsafe
    obs_timestamp = obs_last[0] + SECONDS_AGO
    obs_tick_cumulative = obs_last[1] + SECONDS_AGO * tick_bankrupt
    obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
    obs_next = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
    mock_univ3_pool.pushObservation(*obs_next, sender=sender)

    # oracle updates
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    oracle_tick_cumulative = obs_next[1]  # oracle tick cumulative
    position = position_lib.sync(
        position,
        block_timestamp_next,
        tick_cumulative,
        oracle_tick_cumulative,
        TICK_CUMULATIVE_RATE_MAX,
        FUNDING_PERIOD,
    )

    # prep for call to liquidate
    params = (bob.address, callee.address, id)
    tx = pool_initialized_with_liquidity.liquidate(*params, sender=alice)
    rewards = position.rewards

    # check pool state transition (including liquidity locked update)
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    (amount0, amount1) = position_lib.amountsLocked(position)
    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
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
    position = position_lib.liquidate(position)
    result_position = pool_initialized_with_liquidity.positions(key)
    assert result_position == position

    # check balances
    balancee_pool -= rewards
    balancee_bob += rewards

    result_balancee_pool = pool_initialized_with_liquidity.balance
    result_balancee_bob = bob.balance

    assert result_balancee_pool == balancee_pool
    assert result_balancee_bob == balancee_bob

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Liquidate)
    assert len(events) == 1
    event = events[0]

    assert event.owner == callee.address
    assert event.id == id
    assert event.recipient == bob.address
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.rewards == rewards

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

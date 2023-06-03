import pytest

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import (
    get_position_key,
    calc_tick_from_sqrt_price_x96,
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
    margin = int(1.10 * size) * maintenance // MAINTENANCE_UNIT  # 1

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
        int(1.10 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.10x for breathing room

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
def zero_for_one_position_adjusted_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    zero_for_one_position_id,
    oracle_sqrt_price_initial_x96,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    maintenance = pool_initialized_with_liquidity.maintenance()
    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    collateral1_req = int(
        debt0_adjusted * (oracle_sqrt_price_initial_x96**2) // (1 << 192)
    )
    margin1 = collateral1_req - position.size
    margin1 *= 1.20  # go 20% larger than reqs to ensure safe

    margin_delta = int(margin1) - position.margin

    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        margin_delta,
        sender=sender,
    )
    return zero_for_one_position_id


@pytest.fixture
def one_for_zero_position_adjusted_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
    oracle_sqrt_price_initial_x96,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    maintenance = pool_initialized_with_liquidity.maintenance()
    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    collateral0_req = int(
        debt1_adjusted * (1 << 192) // (oracle_sqrt_price_initial_x96**2)
    )
    margin0 = collateral0_req - position.size
    margin0 *= 1.20  # go 20% larger than reqs to ensure safe

    margin_delta = int(margin0) - position.margin

    callee.adjust(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        margin_delta,
        sender=sender,
    )
    return one_for_zero_position_id


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

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    reserve0, reserve1 = liquidity_math_lib.toAmounts(
        state.liquidity, state.sqrtPriceX96
    )

    amount0, amount1 = position_lib.amountsLocked(position)
    amount1 += position.margin

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
    amount0 += position.margin

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


def test_pool_liquidate__updates_reserves_locked_with_zero_for_one(
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
    reserves_locked = pool_initialized_with_liquidity.reservesLocked()

    amount0, amount1 = position_lib.amountsLocked(position)
    reserves_locked.token0 -= amount0
    reserves_locked.token1 -= amount1

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )
    assert pool_initialized_with_liquidity.reservesLocked() == reserves_locked


def test_pool_liquidate__updates_reserves_locked_with_one_for_zero(
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
    reserves_locked = pool_initialized_with_liquidity.reservesLocked()

    amount0, amount1 = position_lib.amountsLocked(position)
    reserves_locked.token0 -= amount0
    reserves_locked.token1 -= amount1

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )
    assert pool_initialized_with_liquidity.reservesLocked() == reserves_locked


def test_pool_liquidate__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    rando_univ3_observations,
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

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )

    state = pool_initialized_with_liquidity.state()
    tick_cumulative = state.tickCumulative
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    position_liquidated.tickCumulativeStart = tick_cumulative
    position_liquidated.oracleTickCumulativeStart = oracle_tick_cumulative

    assert pool_initialized_with_liquidity.positions(key) == position_liquidated


def test_pool_liquidate__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    position_lib,
    liquidity_math_lib,
    rando_univ3_observations,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    position_liquidated = position_lib.liquidate(position)

    pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )

    state = pool_initialized_with_liquidity.state()
    tick_cumulative = state.tickCumulative
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    position_liquidated.tickCumulativeStart = tick_cumulative
    position_liquidated.oracleTickCumulativeStart = oracle_tick_cumulative

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
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    rewards1 = position.rewards

    balance0_before = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_before = token1.balanceOf(pool_initialized_with_liquidity.address)

    tx = pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, zero_for_one_position_id, sender=alice
    )

    assert tx.return_value == (0, rewards1)
    assert token0.balanceOf(pool_initialized_with_liquidity.address) == balance0_before
    assert token0.balanceOf(bob.address) == 0

    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_before - rewards1
    )
    assert token1.balanceOf(bob.address) == rewards1


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
    rewards0 = position.rewards

    balance0_before = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_before = token1.balanceOf(pool_initialized_with_liquidity.address)

    tx = pool_initialized_with_liquidity.liquidate(
        bob.address, callee.address, one_for_zero_position_id, sender=alice
    )

    assert tx.return_value == (rewards0, 0)
    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_before - rewards0
    )
    assert token0.balanceOf(bob.address) == rewards0

    assert token1.balanceOf(pool_initialized_with_liquidity.address) == balance1_before
    assert token1.balanceOf(bob.address) == 0


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
    rewards1 = position.rewards

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
    assert event.rewards0 == 0
    assert event.rewards1 == rewards1


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
    rewards0 = position.rewards

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
    assert event.rewards0 == rewards0
    assert event.rewards1 == 0


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
    with reverts("not position"):
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

    with reverts("not position"):
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
    zero_for_one_position_adjusted_id,
):
    id = zero_for_one_position_adjusted_id
    with reverts("position safe"):
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
    one_for_zero_position_adjusted_id,
):
    id = one_for_zero_position_adjusted_id
    with reverts("position safe"):
        pool_initialized_with_liquidity.liquidate(
            bob.address, callee.address, id, sender=alice
        )


# TODO:
@pytest.mark.fuzzing
def test_pool_liquidate__with_fuzz():
    pass

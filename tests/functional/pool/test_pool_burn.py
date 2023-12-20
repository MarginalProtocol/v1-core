import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96

# TODO: test multiple mints, burns & swaps
# TODO: explicitly check: balances for locked + unlocked liquidity, liquidity gained from fees on locked liq burn


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
        sender.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = tx.decode_logs(callee.OpenReturn)[0].id
    return int(id)


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
        sender.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = tx.decode_logs(callee.OpenReturn)[0].id
    return int(id)


def test_pool_burn__updates_state(
    pool_initialized_with_liquidity,
    sender,
    alice,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    shares_burned = shares // 3
    liquidity_burned = state.liquidity // 3

    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    state.liquidity -= liquidity_burned
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    result = pool_initialized_with_liquidity.state()
    assert result.liquidity == state.liquidity
    assert result.sqrtPriceX96 == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions


def test_pool_burn__burns_lp_shares(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()

    shares_burned = shares
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    shares -= shares_burned
    total_shares -= shares_burned

    assert pool_initialized_with_liquidity.balanceOf(sender.address) == shares
    assert pool_initialized_with_liquidity.totalSupply() == total_shares


def test_pool_burn__burns_multiple_lp_shares(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()

    shares_burned = shares // 3
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)

    shares -= 2 * shares_burned
    total_shares -= 2 * shares_burned
    assert pool_initialized_with_liquidity.balanceOf(sender.address) == shares
    assert pool_initialized_with_liquidity.totalSupply() == total_shares


def test_pool_burn__returns_amounts(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()

    state = pool_initialized_with_liquidity.state()
    total_liquidity = state.liquidity

    shares_burned = shares // 3
    liquidity_delta = (total_liquidity * shares_burned) // total_shares
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    tx = callee.burn(
        pool_initialized_with_liquidity.address,
        alice.address,
        shares_burned,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.BurnReturn)[0]
    assert return_log.liquidityDelta == liquidity_delta
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1


def test_pool_burn__transfers_funds(
    pool_initialized_with_liquidity,
    sender,
    alice,
    token0,
    token1,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    state = pool_initialized_with_liquidity.state()
    total_liquidity = state.liquidity

    shares_burned = shares // 3
    liquidity_delta = (total_liquidity * shares_burned) // total_shares
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)

    balance0 -= amount0
    balance1 -= amount1

    assert (
        pytest.approx(
            token0.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance0
    )
    assert (
        pytest.approx(
            token1.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance1
    )


def test_pool_burn__transfers_multiple_funds(
    pool_initialized_with_liquidity,
    sender,
    alice,
    token0,
    token1,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_shares = pool_initialized_with_liquidity.totalSupply()

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    state = pool_initialized_with_liquidity.state()
    total_liquidity = state.liquidity

    shares_burned = shares // 3
    liquidity_delta = (total_liquidity * shares_burned) // total_shares
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )

    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)

    balance0 -= 2 * amount0
    balance1 -= 2 * amount1

    assert (
        pytest.approx(
            token0.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance0
    )
    assert (
        pytest.approx(
            token1.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance1
    )
    assert pytest.approx(token0.balanceOf(alice.address), rel=1e-11) == (2 * amount0)
    assert pytest.approx(token1.balanceOf(alice.address), rel=1e-11) == (2 * amount1)


def test_pool_burn__emits_burn(
    pool_initialized_with_liquidity,
    sender,
    alice,
    token0,
    token1,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    liquidity = pool_initialized_with_liquidity.state().liquidity

    shares_burned = shares // 3
    tx = pool_initialized_with_liquidity.burn(
        alice.address, shares_burned, sender=sender
    )

    liquidity_delta = liquidity - pool_initialized_with_liquidity.state().liquidity
    amount0 = token0.balanceOf(alice.address)
    amount1 = token1.balanceOf(alice.address)

    events = tx.decode_logs(pool_initialized_with_liquidity.Burn)
    assert len(events) == 1
    event = events[0]

    assert event.owner == sender.address
    assert event.recipient == alice.address
    assert event.liquidityDelta == liquidity_delta
    assert event.amount0 == amount0
    assert event.amount1 == amount1


def test_pool_burn__updates_state_with_locked_liquidity_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    chain,
    token0,
    token1,
    zero_for_one_position_id,
):
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_supply = pool_initialized_with_liquidity.totalSupply()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    shares_burned = shares // 3
    total_liquidity = state.liquidity + liquidity_locked
    liquidity_delta = (total_liquidity * shares_burned) // total_supply

    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    state.liquidity -= liquidity_delta
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    result = pool_initialized_with_liquidity.state()

    assert result.liquidity == state.liquidity
    assert result.sqrtPriceX96 == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions


def test_pool_burn__updates_state_with_locked_liquidity_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    chain,
    token0,
    token1,
    one_for_zero_position_id,
):
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    total_supply = pool_initialized_with_liquidity.totalSupply()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    shares_burned = shares // 3
    total_liquidity = state.liquidity + liquidity_locked
    liquidity_delta = (total_liquidity * shares_burned) // total_supply

    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    state.liquidity -= liquidity_delta
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    result = pool_initialized_with_liquidity.state()

    assert result.liquidity == state.liquidity
    assert result.sqrtPriceX96 == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions


def test_pool_burn__transfers_funds_with_locked_liquidity_zero_for_one(
    pool_initialized_with_liquidity,
    sender,
    alice,
    token0,
    token1,
    zero_for_one_position_id,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    total_shares = pool_initialized_with_liquidity.totalSupply()

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    state = pool_initialized_with_liquidity.state()
    total_liquidity = state.liquidity + liquidity_locked

    shares_burned = shares // 3
    liquidity_delta = (total_liquidity * shares_burned) // total_shares
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)

    balance0 -= amount0
    balance1 -= amount1

    assert (
        pytest.approx(
            token0.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance0
    )
    assert (
        pytest.approx(
            token1.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance1
    )


def test_pool_burn__transfers_funds_with_locked_liquidity_one_for_zero(
    pool_initialized_with_liquidity,
    sender,
    alice,
    token0,
    token1,
    one_for_zero_position_id,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    total_shares = pool_initialized_with_liquidity.totalSupply()

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    state = pool_initialized_with_liquidity.state()
    total_liquidity = state.liquidity + liquidity_locked

    shares_burned = shares // 3
    liquidity_delta = (total_liquidity * shares_burned) // total_shares
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)

    balance0 -= amount0
    balance1 -= amount1

    assert (
        pytest.approx(
            token0.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance0
    )
    assert (
        pytest.approx(
            token1.balanceOf(pool_initialized_with_liquidity.address), rel=1e-11
        )
        == balance1
    )


def test_pool_burn__passes_when_shares_zero(
    pool_initialized_with_liquidity,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    total_shares = pool_initialized_with_liquidity.totalSupply()

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    state = pool_initialized_with_liquidity.state()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    shares_burned = 0
    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)

    # update tick cumulative, block timestamp values
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    # check state and balances remain same
    assert pool_initialized_with_liquidity.totalSupply() == total_shares
    assert pool_initialized_with_liquidity.balanceOf(sender.address) == shares

    assert pool_initialized_with_liquidity.state() == state
    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked

    assert token0.balanceOf(pool_initialized_with_liquidity.address) == balance0
    assert token1.balanceOf(pool_initialized_with_liquidity.address) == balance1


def test_pool_burn__reverts_when_shares_greater_than_total_supply(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    shares_burned = pool_initialized_with_liquidity.totalSupply() + 1
    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        pool_initialized_with_liquidity.burn(
            alice.address, shares_burned, sender=sender
        )


def test_pool_burn__reverts_when_liquidity_delta_greater_than_liquidity(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    token0,
    token1,
    zero_for_one_position_id,
):
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)
    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        pool_initialized_with_liquidity.burn(alice.address, shares, sender=sender)


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta=st.integers(min_value=1, max_value=2**128 - 1),
    zero_for_one=st.booleans(),
    shares_pc=st.integers(min_value=1, max_value=1000000000),
)
def test_pool_burn__after_initial_mint_with_fuzz(
    pool_initialized,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    liquidity_delta,
    zero_for_one,
    shares_pc,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**255 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**255 - 1 - balance1_sender, sender=sender)

    # set up fuzz test of burn after initial mint
    shares_alice = pool_initialized.balanceOf(alice.address)
    total_supply = pool_initialized.totalSupply()

    shares = liquidity_delta
    params = (
        pool_initialized.address,
        alice.address,
        liquidity_delta,
    )

    # prep for burn
    shares_burned = (shares * shares_pc) // 1000000000
    if shares_burned == 0:
        shares_burned += 1

    callee.mint(*params, sender=sender)

    # check mint produced expected results
    shares_alice += shares
    total_supply += shares

    assert shares_alice == pool_initialized.balanceOf(alice.address)
    assert total_supply == pool_initialized.totalSupply()

    # balances prior
    balance0_pool = token0.balanceOf(pool_initialized.address)
    balance1_pool = token1.balanceOf(pool_initialized.address)
    balance0_bob = token0.balanceOf(bob.address)
    balance1_bob = token1.balanceOf(bob.address)

    # state prior
    state = pool_initialized.state()
    liquidity_locked = pool_initialized.liquidityLocked()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    liquidity_delta_burned = (state.liquidity * shares_burned) // total_supply
    (amount0_received, amount1_received) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta_burned, state.sqrtPriceX96
    )

    params = (bob.address, shares_burned)
    tx = pool_initialized.burn(*params, sender=alice)

    # check pool state transition (including liquidity locked)
    state.liquidity -= liquidity_delta_burned
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next
    result_state = pool_initialized.state()

    assert result_state == state

    liquidity_locked += 0
    result_liquidity_locked = pool_initialized.liquidityLocked()

    assert result_liquidity_locked == liquidity_locked

    # check balances (including lp shares)
    shares_alice -= shares_burned
    total_supply -= shares_burned
    result_shares_alice = pool_initialized.balanceOf(alice.address)
    result_total_supply = pool_initialized.totalSupply()

    assert result_shares_alice == shares_alice
    assert result_total_supply == total_supply

    balance0_pool -= amount0_received
    balance1_pool -= amount1_received
    balance0_bob += amount0_received
    balance1_bob += amount1_received

    result_balance0_pool = token0.balanceOf(pool_initialized.address)
    result_balance1_pool = token1.balanceOf(pool_initialized.address)
    result_balance0_bob = token0.balanceOf(bob.address)
    result_balance1_bob = token1.balanceOf(bob.address)

    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool
    assert result_balance0_bob == balance0_bob
    assert result_balance1_bob == balance1_bob

    # check events
    events = tx.decode_logs(pool_initialized.Burn)
    assert len(events) == 1
    event = events[0]

    assert event.owner == alice.address
    assert event.recipient == bob.address
    assert event.liquidityDelta == liquidity_delta_burned
    assert event.amount0 == amount0_received
    assert event.amount1 == amount1_received

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta=st.integers(min_value=1, max_value=2**128 - 1),
    zero_for_one=st.booleans(),
    shares_pc=st.integers(min_value=1, max_value=1000000000),
)
def test_pool_burn__after_multiple_mint_with_fuzz(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    liquidity_delta,
    zero_for_one,
    shares_pc,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # open a position so some liquidity locked
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    assert state.liquidity > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0
    assert state.totalPositions == 0

    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta_open = state.liquidity * 10 // 100  # 10% of available liquidity
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1

    (amount0_open, amount1_open) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta_open, state.sqrtPriceX96
    )
    amount_open = amount1_open if zero_for_one else amount0_open

    size = int(
        amount_open
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta_open / state.liquidity)
    )
    margin = int(2 * size) * maintenance // MAINTENANCE_UNIT  # 2x for breathing room
    callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta_open,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    # check liquidity locked after open
    liquidity_locked += liquidity_delta_open
    result_liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    assert result_liquidity_locked == liquidity_locked

    # mint large number of tokens to sender to avoid balance issues
    state = pool_initialized_with_liquidity.state()
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**255 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**255 - 1 - balance1_sender, sender=sender)

    # set up fuzz test of burn after second mint
    shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)
    total_supply = pool_initialized_with_liquidity.totalSupply()

    # adjust liquidity delta is will make totalLiquidityAfter > uint128
    if liquidity_delta + liquidity_locked + state.liquidity > 2**128 - 1:
        liquidity_delta = 2**128 - 1 - liquidity_locked - state.liquidity
    elif liquidity_delta <= (state.liquidity + liquidity_locked) // total_supply:
        liquidity_delta = (state.liquidity + liquidity_locked) // total_supply + 1

    shares = (total_supply * liquidity_delta) // (state.liquidity + liquidity_locked)
    params = (
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
    )

    # prep for burn
    shares_burned = (shares * shares_pc) // 1000000000
    if shares_burned == 0:
        shares_burned += 1

    callee.mint(*params, sender=sender)

    # check mint produced expected results
    shares_alice += shares
    total_supply += shares

    assert shares_alice == pool_initialized_with_liquidity.balanceOf(alice.address)
    assert total_supply == pool_initialized_with_liquidity.totalSupply()

    # balances prior
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance0_bob = token0.balanceOf(bob.address)
    balance1_bob = token1.balanceOf(bob.address)

    # state prior
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    total_liquidity = state.liquidity + liquidity_locked
    liquidity_delta_burned = (total_liquidity * shares_burned) // total_supply
    (amount0_received, amount1_received) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta_burned, state.sqrtPriceX96
    )

    params = (bob.address, shares_burned)
    tx = pool_initialized_with_liquidity.burn(*params, sender=alice)

    # check pool state transition (including liquidity locked)
    state.liquidity -= liquidity_delta_burned
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next
    result_state = pool_initialized_with_liquidity.state()

    assert result_state == state

    liquidity_locked += 0
    result_liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    assert result_liquidity_locked == liquidity_locked

    # check balances (including lp shares)
    shares_alice -= shares_burned
    total_supply -= shares_burned
    result_shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)
    result_total_supply = pool_initialized_with_liquidity.totalSupply()

    assert result_shares_alice == shares_alice
    assert result_total_supply == total_supply

    balance0_pool -= amount0_received
    balance1_pool -= amount1_received
    balance0_bob += amount0_received
    balance1_bob += amount1_received

    result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    result_balance0_bob = token0.balanceOf(bob.address)
    result_balance1_bob = token1.balanceOf(bob.address)

    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool
    assert result_balance0_bob == balance0_bob
    assert result_balance1_bob == balance1_bob

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Burn)
    assert len(events) == 1
    event = events[0]

    assert event.owner == alice.address
    assert event.recipient == bob.address
    assert event.liquidityDelta == liquidity_delta_burned
    assert event.amount0 == amount0_received
    assert event.amount1 == amount1_received

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

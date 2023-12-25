import pytest
from math import sqrt

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


def test_pool_mint__updates_state(
    pool_initialized,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    state = pool_initialized.state()
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)
    state.liquidity += liquidity_delta
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    assert pool_initialized.state() == state


def test_pool_mint__mints_lp_shares(
    pool_initialized,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)
    assert pool_initialized.balanceOf(alice.address) == liquidity_delta
    assert pool_initialized.totalSupply() == liquidity_delta


def test_pool_mint__mints_multiple_lp_shares(
    pool_initialized,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta_alice = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    liquidity_delta_bob = liquidity_spot * 50 // 10000  # 0.5% of spot reserves

    # mint to alice then bob then alice again
    callee.mint(
        pool_initialized.address, alice.address, liquidity_delta_alice, sender=sender
    )
    callee.mint(
        pool_initialized.address, bob.address, liquidity_delta_bob, sender=sender
    )
    callee.mint(
        pool_initialized.address, alice.address, liquidity_delta_alice, sender=sender
    )

    assert pool_initialized.balanceOf(alice.address) == 2 * liquidity_delta_alice
    assert pool_initialized.balanceOf(bob.address) == liquidity_delta_bob
    assert (
        pool_initialized.totalSupply()
        == 2 * liquidity_delta_alice + liquidity_delta_bob
    )


def test_pool_mint__mints_multiple_lp_shares_with_locked_liquidity_zero_for_one(
    pool_initialized,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    position_lib,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)

    # open a short position
    state = pool_initialized.state()
    maintenance = pool_initialized.maintenance()

    premium = pool_initialized.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

    zero_for_one = True
    liquidity_delta_open = liquidity_delta * 10 // 100  # 10% of available liquidity
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

    callee.open(
        pool_initialized.address,
        callee.address,
        zero_for_one,
        liquidity_delta_open,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    total_supply = pool_initialized.totalSupply()
    state = pool_initialized.state()
    liquidity_locked = pool_initialized.liquidityLocked()

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)

    shares_after_open = (total_supply * liquidity_delta) // (
        liquidity_locked + state.liquidity
    )
    assert (
        pool_initialized.balanceOf(alice.address) == liquidity_delta + shares_after_open
    )
    assert pool_initialized.totalSupply() == liquidity_delta + shares_after_open


def test_pool_mint__mints_multiple_lp_shares_with_locked_liquidity_one_for_zero(
    pool_initialized,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    position_lib,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)

    # open a long position
    state = pool_initialized.state()
    maintenance = pool_initialized.maintenance()

    premium = pool_initialized.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

    zero_for_one = False
    liquidity_delta_open = liquidity_delta * 10 // 100  # 10% of available liquidity
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

    callee.open(
        pool_initialized.address,
        callee.address,
        zero_for_one,
        liquidity_delta_open,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    total_supply = pool_initialized.totalSupply()
    state = pool_initialized.state()
    liquidity_locked = pool_initialized.liquidityLocked()

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)

    shares_after_open = (total_supply * liquidity_delta) // (
        liquidity_locked + state.liquidity
    )
    assert (
        pool_initialized.balanceOf(alice.address) == liquidity_delta + shares_after_open
    )
    assert pool_initialized.totalSupply() == liquidity_delta + shares_after_open


def test_pool_mint__transfers_funds(
    pool_initialized,
    sqrt_price_x96_initial,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, sqrt_price_x96_initial
    )
    amount0 += 1
    amount1 += 1  # mint does a rough round up when adding liquidity

    shares_before = pool_initialized.balanceOf(alice.address)

    sender_balance0 = token0.balanceOf(sender.address)
    sender_balance1 = token1.balanceOf(sender.address)

    tx = callee.mint(
        pool_initialized.address, alice.address, liquidity_delta, sender=sender
    )
    shares = pool_initialized.balanceOf(alice.address) - shares_before

    assert token0.balanceOf(pool_initialized.address) == amount0
    assert token1.balanceOf(pool_initialized.address) == amount1

    return_log = tx.decode_logs(callee.MintReturn)[0]
    assert (return_log.shares, return_log.amount0, return_log.amount1) == (
        shares,
        amount0,
        amount1,
    )

    assert token0.balanceOf(sender.address) == sender_balance0 - amount0
    assert token1.balanceOf(sender.address) == sender_balance1 - amount1


def test_pool_mint__calls_mint_callback(
    pool_initialized,
    sqrt_price_x96_initial,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, sqrt_price_x96_initial
    )
    amount0 += 1
    amount1 += 1  # mint does a rough round up when adding liquidity

    tx = callee.mint(
        pool_initialized.address, alice.address, liquidity_delta, sender=sender
    )
    events = tx.decode_logs(callee.MintCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == amount0
    assert event.amount1Owed == amount1
    assert event.sender == sender.address


def test_pool_mint__emits_mint(
    pool_initialized,
    sqrt_price_x96_initial,
    callee,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, sqrt_price_x96_initial
    )
    amount0 += 1
    amount1 += 1  # mint does a rough round up when adding liquidity

    tx = callee.mint(
        pool_initialized.address, alice.address, liquidity_delta, sender=sender
    )
    events = tx.decode_logs(pool_initialized.Mint)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.owner == alice.address
    assert event.liquidityDelta == liquidity_delta
    assert event.amount0 == amount0
    assert event.amount1 == amount1


def test_pool_mint__reverts_when_liquidity_delta_zero(
    pool_initialized,
    sqrt_price_x96_initial,
    callee,
    sender,
    alice,
):
    liquidity_delta = 0
    with reverts(pool_initialized.InvalidLiquidityDelta):
        callee.mint(
            pool_initialized.address, alice.address, liquidity_delta, sender=sender
        )


def test_pool_mint__reverts_when_amount0_transferred_less_than_min(
    pool_initialized,
    sqrt_price_x96_initial,
    callee_below_min0,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    with reverts(pool_initialized.Amount0LessThanMin):
        callee_below_min0.mint(
            pool_initialized.address, alice.address, liquidity_delta, sender=sender
        )


def test_pool_mint__reverts_when_amount1_transferred_less_than_min(
    pool_initialized,
    sqrt_price_x96_initial,
    callee_below_min1,
    sender,
    alice,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    with reverts(pool_initialized.Amount1LessThanMin):
        callee_below_min1.mint(
            pool_initialized.address, alice.address, liquidity_delta, sender=sender
        )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=500))
@given(
    liquidity_delta=st.integers(min_value=1, max_value=2**128 - 1),
)
def test_pool_mint__initial_mint_with_fuzz(
    pool_initialized,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    liquidity_delta,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**255 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**255 - 1 - balance1_sender, sender=sender)

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)  # 2**255-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**255-1
    balance0_pool = token0.balanceOf(pool_initialized.address)
    balance1_pool = token1.balanceOf(pool_initialized.address)

    shares_alice = pool_initialized.balanceOf(alice.address)
    total_supply = pool_initialized.totalSupply()

    # set up fuzz test of initial mint
    state = pool_initialized.state()
    liquidity_locked = pool_initialized.liquidityLocked()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    amount0 += 1
    amount1 += 1  # mint does a rough round up when adding liquidity

    shares = liquidity_delta

    params = (
        pool_initialized.address,
        alice.address,
        liquidity_delta,
    )
    tx = callee.mint(*params, sender=sender)
    return_log = tx.decode_logs(callee.MintReturn)[0]

    assert return_log.shares == shares
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    # check pool state transition (including liquidity locked)
    state.liquidity += liquidity_delta
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next
    result_state = pool_initialized.state()

    assert result_state == state

    liquidity_locked += 0
    result_liquidity_locked = pool_initialized.liquidityLocked()

    assert result_liquidity_locked == liquidity_locked

    # check balances (including lp shares)
    shares_alice += shares
    total_supply += shares
    result_shares_alice = pool_initialized.balanceOf(alice.address)
    result_total_supply = pool_initialized.totalSupply()

    assert result_shares_alice == shares_alice
    assert result_total_supply == total_supply

    balance0_sender -= amount0
    balance1_sender -= amount1
    balance0_pool += amount0
    balance1_pool += amount1

    result_balance0_sender = token0.balanceOf(sender.address)
    result_balance1_sender = token1.balanceOf(sender.address)
    result_balance0_pool = token0.balanceOf(pool_initialized.address)
    result_balance1_pool = token1.balanceOf(pool_initialized.address)

    assert result_balance0_sender == balance0_sender
    assert result_balance1_sender == balance1_sender
    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool

    # check events
    events = tx.decode_logs(pool_initialized.Mint)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.owner == alice.address
    assert event.liquidityDelta == liquidity_delta
    assert event.amount0 == amount0
    assert event.amount1 == amount1

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta=st.integers(min_value=1, max_value=2**128 - 1),
    zero_for_one=st.booleans(),
)
def test_pool_mint__multiple_mint_with_fuzz(
    pool_initialized_with_liquidity,
    callee,
    sender,
    alice,
    bob,
    token0,
    token1,
    liquidity_delta,
    zero_for_one,
    chain,
    position_lib,
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
    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )
    callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta_open,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    # check liquidity locked after open
    liquidity_locked += liquidity_delta_open
    result_liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    assert result_liquidity_locked == liquidity_locked

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**255 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**255 - 1 - balance1_sender, sender=sender)

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)  # 2**255-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**255-1
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)
    total_supply = pool_initialized_with_liquidity.totalSupply()

    # set up fuzz test of second mint
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    # adjust liquidity delta is will make totalLiquidityAfter > uint128
    if liquidity_delta + liquidity_locked + state.liquidity > 2**128 - 1:
        liquidity_delta = 2**128 - 1 - liquidity_locked - state.liquidity

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    amount0 += 1
    amount1 += 1  # mint does a rough round up when adding liquidity

    shares = (liquidity_delta * total_supply) // (state.liquidity + liquidity_locked)
    params = (
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
    )
    tx = callee.mint(*params, sender=sender)
    return_log = tx.decode_logs(callee.MintReturn)[0]

    assert return_log.shares == shares
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    # check pool state transition (including liquidity locked)
    state.liquidity += liquidity_delta
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    result_state = pool_initialized_with_liquidity.state()
    assert result_state == state

    # check balances (including lp shares)
    shares_alice += shares
    total_supply += shares
    result_shares_alice = pool_initialized_with_liquidity.balanceOf(alice.address)
    result_total_supply = pool_initialized_with_liquidity.totalSupply()

    assert result_shares_alice == shares_alice
    assert result_total_supply == total_supply

    balance0_sender -= amount0
    balance1_sender -= amount1
    balance0_pool += amount0
    balance1_pool += amount1

    result_balance0_sender = token0.balanceOf(sender.address)
    result_balance1_sender = token1.balanceOf(sender.address)
    result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    assert result_balance0_sender == balance0_sender
    assert result_balance1_sender == balance1_sender
    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Mint)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.owner == alice.address
    assert event.liquidityDelta == liquidity_delta
    assert event.amount0 == amount0
    assert event.amount1 == amount1

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

import pytest
from math import sqrt

from ape import reverts
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96

# TODO: test multiple mints & swaps, test when reserves locked, test_mint_then_burn


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
    assert (
        pytest.approx(pool_initialized.balanceOf(alice.address), rel=1e-11)
        == liquidity_delta
    )  # TODO: fix for rounding
    assert pytest.approx(pool_initialized.totalSupply(), rel=1e-11) == liquidity_delta


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

    assert pytest.approx(pool_initialized.balanceOf(alice.address), rel=1e-11) == (
        2 * liquidity_delta_alice
    )
    assert (
        pytest.approx(pool_initialized.balanceOf(bob.address), rel=1e-11)
        == liquidity_delta_bob
    )
    assert pytest.approx(pool_initialized.totalSupply(), rel=1e-11) == (
        2 * liquidity_delta_alice + liquidity_delta_bob
    )


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

    sender_balance0 = token0.balanceOf(sender.address)
    sender_balance1 = token1.balanceOf(sender.address)

    tx = callee.mint(
        pool_initialized.address, alice.address, liquidity_delta, sender=sender
    )
    assert token0.balanceOf(pool_initialized.address) == amount0
    assert token1.balanceOf(pool_initialized.address) == amount1
    assert tx.return_value == (amount0, amount1)

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
    with reverts("liquidityDelta == 0"):
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

    with reverts("amount0 < min"):
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

    with reverts("amount1 < min"):
        callee_below_min1.mint(
            pool_initialized.address, alice.address, liquidity_delta, sender=sender
        )


# TODO:
@pytest.mark.fuzzing
def test_pool_mint__with_fuzz():
    pass

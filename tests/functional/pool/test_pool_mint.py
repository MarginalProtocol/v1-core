import pytest
from math import sqrt

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96

# TODO: test multiple mints & swaps
# TODO: explicitly check: balances for locked + unlocked liquidity, liquidity gained from fees on locked liq mint


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
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)

    # open a short position
    state = pool_initialized.state()
    maintenance = pool_initialized.maintenance()
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

    callee.open(
        pool_initialized.address,
        callee.address,
        zero_for_one,
        liquidity_delta_open,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
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
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    callee.mint(pool_initialized.address, alice.address, liquidity_delta, sender=sender)

    # open a short position
    state = pool_initialized.state()
    maintenance = pool_initialized.maintenance()
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

    callee.open(
        pool_initialized.address,
        callee.address,
        zero_for_one,
        liquidity_delta_open,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
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


# TODO:
@pytest.mark.fuzzing
def test_pool_mint__with_fuzz():
    pass

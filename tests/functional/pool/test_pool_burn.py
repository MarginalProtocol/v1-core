import pytest

from ape import reverts
from math import sqrt

from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def pool_initialized_with_liquidity(
    pool_initialized, callee, token0, token1, sender, spot_reserve0, spot_reserve1
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves
    callee.mint(
        pool_initialized.address, sender.address, liquidity_delta, sender=sender
    )
    pool_initialized.approve(pool_initialized.address, 2**256 - 1, sender=sender)
    return pool_initialized


def test_pool_burn__updates_state(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    state = pool_initialized_with_liquidity.state()
    shares = pool_initialized_with_liquidity.balanceOf(sender.address)

    shares_burned = shares // 3
    liquidity_burned = state.liquidity // 3

    pool_initialized_with_liquidity.burn(alice.address, shares_burned, sender=sender)
    state.liquidity -= liquidity_burned

    result = pool_initialized_with_liquidity.state()
    assert (
        pytest.approx(result.liquidity, rel=1e-11) == state.liquidity
    )  # TODO: appropriate rel error?
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
    tx = pool_initialized_with_liquidity.burn(
        alice.address, shares_burned, sender=sender
    )

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

    result_amount0 = token0.balanceOf(alice.address)
    result_amount1 = token1.balanceOf(alice.address)
    assert tx.return_value == (result_amount0, result_amount1)
    assert pytest.approx(result_amount0, rel=1e-11) == amount0
    assert pytest.approx(result_amount1, rel=1e-11) == amount1


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


def test_pool_burn__reverts_when_shares_zero(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    shares_burned = 0
    with reverts("shares == 0"):
        pool_initialized_with_liquidity.burn(
            alice.address, shares_burned, sender=sender
        )


def test_pool_burn__reverts_when_shares_greater_than_total_supply(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    shares_burned = pool_initialized_with_liquidity.totalSupply() + 1
    with reverts("shares > totalSupply"):
        pool_initialized_with_liquidity.burn(
            alice.address, shares_burned, sender=sender
        )


# TODO: with position open
def test_pool_burn__reverts_when_liquidity_delta_greater_than_liquidity():
    pass


# TODO:
@pytest.mark.fuzzing
def test_pool_burn__with_fuzz():
    pass

import pytest
from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


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
    return int(tx.return_value[0])


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
    with reverts(pool_initialized_with_liquidity.InvalidShares):
        pool_initialized_with_liquidity.burn(
            alice.address, shares_burned, sender=sender
        )


def test_pool_burn__reverts_when_shares_greater_than_total_supply(
    pool_initialized_with_liquidity,
    sender,
    alice,
):
    shares_burned = pool_initialized_with_liquidity.totalSupply() + 1
    with reverts(pool_initialized_with_liquidity.InvalidShares):
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


# TODO: tests when reserves locked


# TODO:
@pytest.mark.fuzzing
def test_pool_burn__with_fuzz():
    pass

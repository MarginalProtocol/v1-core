import pytest

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def pool_initialized_with_liquidity_and_protocol_fee(
    pool_initialized_with_liquidity, admin, sender
):
    # turn protocol fees on
    pool_initialized_with_liquidity.setFeeProtocol(10, sender=admin)
    return pool_initialized_with_liquidity


@pytest.fixture
def pool_after_swaps(pool_initialized_with_liquidity_and_protocol_fee, callee, sender):
    state = pool_initialized_with_liquidity_and_protocol_fee.state()
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )

    amount_in = 1 * reserve0 // 100  # 1% of reserves in
    tx = callee.swap(
        pool_initialized_with_liquidity_and_protocol_fee.address,
        sender.address,
        True,
        amount_in,
        MIN_SQRT_RATIO + 1,
        sender=sender,
    )

    _, amount_in = tx.return_value  # amount out (token 1) from first swap
    amount_in = -amount_in
    callee.swap(
        pool_initialized_with_liquidity_and_protocol_fee.address,
        sender.address,
        False,
        amount_in,
        MAX_SQRT_RATIO - 1,
        sender=sender,
    )
    return pool_initialized_with_liquidity_and_protocol_fee


def test_pool_collect_protocol__updates_protocol_fees(pool_after_swaps, admin, alice):
    protocol_fees = pool_after_swaps.protocolFees()
    amount0 = protocol_fees.token0 - 1
    amount1 = protocol_fees.token1 - 1

    pool_after_swaps.collectProtocol(alice.address, sender=admin)

    protocol_fees.token0 -= amount0
    protocol_fees.token1 -= amount1

    assert pool_after_swaps.protocolFees() == protocol_fees


def test_pool_collect_protocol__transfers_funds(
    pool_after_swaps, admin, alice, token0, token1
):
    protocol_fees = pool_after_swaps.protocolFees()
    amount0 = protocol_fees.token0 - 1
    amount1 = protocol_fees.token1 - 1

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_after_swaps.address)
    balance1_pool = token1.balanceOf(pool_after_swaps.address)

    pool_after_swaps.collectProtocol(alice.address, sender=admin)

    assert token0.balanceOf(pool_after_swaps.address) == balance0_pool - amount0
    assert token1.balanceOf(pool_after_swaps.address) == balance1_pool - amount1
    assert token0.balanceOf(alice.address) == balance0_alice + amount0
    assert token1.balanceOf(alice.address) == balance1_alice + amount1


def test_pool_collect_protocol__emits_collect_protocol(pool_after_swaps, admin, alice):
    protocol_fees = pool_after_swaps.protocolFees()
    amount0 = protocol_fees.token0 - 1
    amount1 = protocol_fees.token1 - 1

    tx = pool_after_swaps.collectProtocol(alice.address, sender=admin)
    assert tx.return_value == (amount0, amount1)

    events = tx.decode_logs(pool_after_swaps.CollectProtocol)
    assert len(events) == 1
    event = events[0]

    assert event.sender == admin.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1


def test_pool_collect_protocol__reverts_when_not_factory_owner(pool_after_swaps, alice):
    with reverts(pool_after_swaps.Unauthorized):
        pool_after_swaps.collectProtocol(alice.address, sender=alice)


def test_pool_collect_protocol__reverts_when_protocol_fees_less_than_min(
    pool_initialized_with_liquidity_and_protocol_fee, admin, alice
):
    with reverts(pool_initialized_with_liquidity_and_protocol_fee.InvalidFeeProtocol):
        pool_initialized_with_liquidity_and_protocol_fee.collectProtocol(
            alice.address, sender=admin
        )

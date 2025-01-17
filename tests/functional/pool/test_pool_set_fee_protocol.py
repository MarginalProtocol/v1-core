import pytest

from ape import reverts


@pytest.mark.skip
def test_pool_set_fee_protocol__with_new_fee_greater_than_zero(
    pool_initialized_with_liquidity, admin
):
    pool_initialized_with_liquidity.setFeeProtocol(
        5, sender=admin
    )  # 20% on fees to protocol
    state = pool_initialized_with_liquidity.state()
    assert state.feeProtocol == 5


@pytest.mark.skip
def test_pool_set_fee_protocol__with_new_fee_zero(
    pool_initialized_with_liquidity, admin
):
    # set to > 0 first
    pool_initialized_with_liquidity.setFeeProtocol(5, sender=admin)

    # then set to zero
    pool_initialized_with_liquidity.setFeeProtocol(0, sender=admin)
    state = pool_initialized_with_liquidity.state()
    assert state.feeProtocol == 0


@pytest.mark.skip
def test_pool_set_fee_protocol__emits_set_fee_protocol(
    pool_initialized_with_liquidity, admin
):
    tx = pool_initialized_with_liquidity.setFeeProtocol(5, sender=admin)
    events = tx.decode_logs(pool_initialized_with_liquidity.SetFeeProtocol)
    assert len(events) == 1

    event = events[0]
    assert event.oldFeeProtocol == 0
    assert event.newFeeProtocol == 5


@pytest.mark.skip
def test_pool_set_fee_protocol__reverts_when_not_factory_owner(
    pool_initialized_with_liquidity, alice
):
    with reverts(pool_initialized_with_liquidity.Unauthorized):
        pool_initialized_with_liquidity.setFeeProtocol(5, sender=alice)


@pytest.mark.skip
def test_pool_set_fee_protocol__reverts_when_less_than_min(
    pool_initialized_with_liquidity, admin
):
    with reverts(pool_initialized_with_liquidity.InvalidFeeProtocol):
        pool_initialized_with_liquidity.setFeeProtocol(3, sender=admin)


@pytest.mark.skip
def test_pool_set_fee_protocol__reverts_when_greater_than_min(
    pool_initialized_with_liquidity, admin
):
    with reverts(pool_initialized_with_liquidity.InvalidFeeProtocol):
        pool_initialized_with_liquidity.setFeeProtocol(11, sender=admin)

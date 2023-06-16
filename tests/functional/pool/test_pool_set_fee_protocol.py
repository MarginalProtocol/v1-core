from ape import reverts


def test_pool_set_fee_protocol__with_new_fee_greater_than_zero(pool_initialized, admin):
    pool_initialized.setFeeProtocol(5, sender=admin)  # 20% on fees to protocol
    state = pool_initialized.state()
    assert state.feeProtocol == 5


def test_pool_set_fee_protocol__with_new_fee_zero(pool_initialized, admin):
    # set to > 0 first
    pool_initialized.setFeeProtocol(5, sender=admin)

    # then set to zero
    pool_initialized.setFeeProtocol(0, sender=admin)
    state = pool_initialized.state()
    assert state.feeProtocol == 0


def test_pool_set_fee_protocol__emits_set_fee_protocol(pool_initialized, admin):
    tx = pool_initialized.setFeeProtocol(5, sender=admin)
    events = tx.decode_logs(pool_initialized.SetFeeProtocol)
    assert len(events) == 1

    event = events[0]
    assert event.oldFeeProtocol == 0
    assert event.newFeeProtocol == 5


def test_pool_set_fee_protocol__reverts_when_not_factory_owner(pool_initialized, alice):
    with reverts(pool_initialized.Unauthorized):
        pool_initialized.setFeeProtocol(5, sender=alice)


def test_pool_set_fee_protocol__reverts_when_less_than_min(pool_initialized, admin):
    with reverts(pool_initialized.InvalidFeeProtocol):
        pool_initialized.setFeeProtocol(3, sender=admin)


def test_pool_set_fee_protocol__reverts_when_greater_than_min(pool_initialized, admin):
    with reverts(pool_initialized.InvalidFeeProtocol):
        pool_initialized.setFeeProtocol(11, sender=admin)

from ape import reverts


def test_set_owner__updates_owner(factory, alice, admin):
    factory.setOwner(alice.address, sender=admin)
    assert factory.owner() == alice.address


def test_set_owner__emits_owner_changed(factory, alice, admin):
    tx = factory.setOwner(alice.address, sender=admin)
    events = tx.decode_logs(factory.OwnerChanged)
    assert len(events) == 1

    event = events[0]
    assert event.oldOwner == admin.address
    assert event.newOwner == alice.address


def test_set_owner__reverts_when_not_owner(factory, alice):
    with reverts(factory.Unauthorized):
        factory.setOwner(alice.address, sender=alice)

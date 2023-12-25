from ape import reverts

from utils.constants import MAINTENANCE_UNIT


def test_enable_leverage__updates_get_leverage(factory, admin):
    maintenance = 200000
    leverage = MAINTENANCE_UNIT + (MAINTENANCE_UNIT**2) // (maintenance)
    factory.enableLeverage(maintenance, sender=admin)
    assert factory.getLeverage(maintenance) == leverage


def test_enable_leverage__emits_leverage_enabled(factory, admin):
    maintenance = 200000
    leverage = MAINTENANCE_UNIT + (MAINTENANCE_UNIT**2) // (maintenance)
    tx = factory.enableLeverage(maintenance, sender=admin)

    events = tx.decode_logs(factory.LeverageEnabled)
    assert len(events) == 1
    event = events[0]

    assert event.maintenance == maintenance
    assert event.leverage == leverage


def test_enable_leverage__reverts_when_not_owner(factory, alice):
    maintenance = 200000
    with reverts(factory.Unauthorized):
        factory.enableLeverage(maintenance, sender=alice)


def test_enable_leverage__reverts_when_maintenance_greater_than_max(factory, admin):
    maintenance = 1000001
    with reverts(factory.InvalidMaintenance):
        factory.enableLeverage(maintenance, sender=admin)


def test_enable_leverage__reverts_when_maintenance_less_than_min(factory, admin):
    maintenance = 100000 - 1
    with reverts(factory.InvalidMaintenance):
        factory.enableLeverage(maintenance, sender=admin)


def test_enable_leverage__reverts_when_leverage_enabled(factory, admin):
    maintenance = 250000
    with reverts(factory.LeverageActive):
        factory.enableLeverage(maintenance, sender=admin)

from utils.utils import get_position_key


def test_position_set(position_lib, alice):
    id = 1
    position = (
        1000000,
        100,
        200,
        50,
        60,
        True,
        False,
        100,
        1684675403,
        -100,
        200000,
        50000,
        15000000000000000,
    )
    position_lib.set(alice, id, position, sender=alice)

    key = get_position_key(alice.address, id)
    assert position_lib.positions(key) == position


def test_position_get(position_lib, alice):
    id = 1
    position = (
        1000000,
        100,
        200,
        50,
        60,
        True,
        False,
        100,
        1684675403,
        -100,
        200000,
        50000,
        15000000000000000,
    )
    position_lib.set(alice, id, position, sender=alice)
    assert position_lib.get(alice, id) == position

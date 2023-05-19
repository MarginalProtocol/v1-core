def test_position_set(position_lib, alice):
    id = 1
    position = (1000000, 100, 200, 50, 60, True)
    position_lib.set(id, position, sender=alice)
    assert position_lib.positions(id) == position

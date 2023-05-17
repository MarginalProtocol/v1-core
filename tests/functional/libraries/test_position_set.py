def test_position_set(position_lib, alice):
    id = 1
    position = (1000000, 1, 100, 200, 50, 60)
    position_lib.set(id, position, sender=alice)
    assert position_lib.positions(id) == position

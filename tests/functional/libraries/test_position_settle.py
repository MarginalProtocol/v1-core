def test_position_settle(position_lib):
    position = (1000000, 100, 200, 50, 60, True, False, 100, -100, 200000, 50000)
    result = position_lib.settle(position)

    position_after = (
        0,
        0,
        0,
        0,
        0,
        position[5],
        position[6],
        position[7],
        position[8],
        0,
        0,
    )
    assert result == position_after

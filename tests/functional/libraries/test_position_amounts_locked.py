def test_position_amounts_locked__with_zero_for_one(position_lib):
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
    result = position_lib.amountsLocked(position)
    assert result[0] == position[3]
    assert result[1] == position[0] + position[10] + position[2] + position[4]


def test_position_amounts_locked__with_one_for_zero(position_lib):
    position = (
        1000000,
        100,
        200,
        50,
        60,
        False,
        False,
        100,
        1684675403,
        -100,
        200000,
        50000,
        15000000000000000,
    )
    result = position_lib.amountsLocked(position)
    assert result[0] == position[0] + position[10] + position[1] + position[3]
    assert result[1] == position[4]

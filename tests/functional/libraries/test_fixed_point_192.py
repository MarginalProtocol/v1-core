def test_fixed_point_192__q192(fixed_point_192_lib):
    assert fixed_point_192_lib.Q192() == (1 << 192)


def test_fixed_point_192__resolution(fixed_point_192_lib):
    assert fixed_point_192_lib.RESOLUTION() == 192

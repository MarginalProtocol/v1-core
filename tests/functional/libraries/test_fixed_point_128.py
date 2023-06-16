def test_fixed_point_128__q128(fixed_point_128_lib):
    assert fixed_point_128_lib.Q128() == (1 << 128)


def test_fixed_point_128__resolution(fixed_point_128_lib):
    assert fixed_point_128_lib.RESOLUTION() == 128

def test_fixed_point_64__q64(fixed_point_64_lib):
    assert fixed_point_64_lib.Q64() == (1 << 64)


def test_fixed_point_64__resolution(fixed_point_64_lib):
    assert fixed_point_64_lib.RESOLUTION() == 64

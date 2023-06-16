def test_fixed_point_96__q96(fixed_point_96_lib):
    assert fixed_point_96_lib.Q96() == (1 << 96)


def test_fixed_point_96__resolution(fixed_point_96_lib):
    assert fixed_point_96_lib.RESOLUTION() == 96

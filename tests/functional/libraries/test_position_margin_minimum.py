import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MAINTENANCE_UNIT
from utils.utils import calc_sqrt_price_x96_next


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__with_zero_for_one(position_lib, maintenance):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    size1 = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )

    margin_min = (size1 * maintenance) // MAINTENANCE_UNIT
    result = position_lib.marginMinimum(size1, maintenance)
    assert result == margin_min


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_position_margin_minimum__with_one_for_zero(position_lib, maintenance):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    size0 = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )

    margin_min = (size0 * maintenance) // MAINTENANCE_UNIT
    result = position_lib.marginMinimum(size0, maintenance)
    assert result == margin_min


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@given(
    size=st.integers(min_value=0, max_value=2**128 - 1),
)
def test_position_margin_minimum__with_fuzz(position_lib, size, maintenance):
    margin_min = (size * maintenance) // MAINTENANCE_UNIT
    result = position_lib.marginMinimum(size, maintenance)
    assert result == margin_min

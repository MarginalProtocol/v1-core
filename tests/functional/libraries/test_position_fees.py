import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import FEE, FEE_UNIT
from utils.utils import calc_sqrt_price_x96_next


def test_position_fees__with_zero_for_one(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    size0 = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )

    fees = size0 * FEE // FEE_UNIT
    result = position_lib.fees(size0, FEE)
    assert result == fees


def test_position_fees__with_one_for_zero(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    size1 = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )

    fees = size1 * FEE // FEE_UNIT
    result = position_lib.fees(size1, FEE)
    assert result == fees


@pytest.mark.fuzzing
@given(
    size=st.integers(min_value=0, max_value=2**128 - 1),
    fee=st.integers(min_value=0, max_value=FEE_UNIT - 1),
)
def test_position_fees__with_fuzz(position_lib, size, fee):
    fees = size * fee // FEE_UNIT
    result = position_lib.fees(size, fee)
    assert result == fees

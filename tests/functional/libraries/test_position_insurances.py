import pytest

from hypothesis import given, settings, strategies as st
from datetime import timedelta
from math import sqrt

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MINIMUM_LIQUIDITY,
    MINIMUM_SIZE,
)
from utils.utils import (
    calc_sqrt_price_x96_next_open,
    calc_insurances,
    calc_insurances_from_root,
)


def test_position_insurances__with_zero_for_one(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )

    result = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    assert result[0] == insurance0
    assert result[1] == insurance1

    # check matches with wp root math
    calc_insurance0, calc_insurance1 = calc_insurances_from_root(
        liquidity, sqrt_price_x96, liquidity_delta, maintenance
    )
    assert pytest.approx(result[0], rel=1e-15) == calc_insurance0
    assert pytest.approx(result[1], rel=1e-15) == calc_insurance1


def test_position_insurances__with_one_for_zero(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000
    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )

    result = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    assert result[0] == insurance0
    assert result[1] == insurance1

    # check matches with wp root math
    calc_insurance0, calc_insurance1 = calc_insurances_from_root(
        liquidity, sqrt_price_x96, liquidity_delta, maintenance
    )
    assert pytest.approx(result[0], rel=1e-15) == calc_insurance0
    assert pytest.approx(result[1], rel=1e-15) == calc_insurance1


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@settings(deadline=timedelta(milliseconds=2000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=1, max_value=2**128 - 1),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000000),
    zero_for_one=st.booleans(),
)
def test_position_insurances__with_fuzz(
    position_lib,
    liquidity,
    sqrt_price_x96,
    liquidity_delta_pc,
    zero_for_one,
    maintenance,
):
    liquidity_delta = (liquidity * liquidity_delta_pc) // 1000000000
    if liquidity_delta >= liquidity - MINIMUM_LIQUIDITY:
        return

    sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    if (
        sqrt_price_x96_next <= MIN_SQRT_RATIO
        or sqrt_price_x96_next >= MAX_SQRT_RATIO - 1
    ):
        return
    elif (sqrt_price_x96_next > sqrt_price_x96 and zero_for_one) or (
        sqrt_price_x96_next < sqrt_price_x96 and not zero_for_one
    ):
        return

    insurance0, insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    if insurance0 >= 2**128 or insurance1 >= 2**128:
        return
    elif insurance0 <= MINIMUM_SIZE or insurance1 <= MINIMUM_SIZE:
        # @dev rounding issues for tiny del L / L (1e-17) values can cause negative insurances that underflow revert
        return

    result = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )

    assert result[0] == insurance0
    assert result[1] == insurance1

    # check matches with wp root math
    calc_insurance0, calc_insurance1 = calc_insurances_from_root(
        liquidity, sqrt_price_x96, liquidity_delta, maintenance
    )

    assert pytest.approx(result[0], rel=1e-3, abs=1) == calc_insurance0
    assert pytest.approx(result[1], rel=1e-3, abs=1) == calc_insurance1

import pytest

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_sqrt_price_x96_next


def test_position_size__with_zero_for_one(position_lib):
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

    # size1 is L * (sqrt(P) - sqrt(P'))
    # about ~ 1% of x pool given liquidity delta
    size1 = int((liquidity * (sqrt_price_x96 - sqrt_price_x96_next)) / (1 << 96))
    result = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )
    assert pytest.approx(result, rel=1e-15) == size1


def test_position_size__with_one_for_zero(position_lib):
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

    # size0 is L * (1/sqrt(P) - 1/sqrt(P'))
    # about ~ 1% of x pool given liquidity delta
    size0 = int(liquidity * (1 << 96) / sqrt_price_x96) - int(
        liquidity * (1 << 96) / sqrt_price_x96_next
    )
    result = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )
    assert pytest.approx(result, rel=1e-15) == size0


@pytest.mark.fuzzing
@given(
    liquidity=st.integers(
        min_value=1000, max_value=2**128 - 1
    ),  # TODO: fix min value
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    sqrt_price_x96_next=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO),
    zero_for_one=st.booleans(),
)
def test_position_size__with_fuzz(
    position_lib, liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
):
    # TODO: fix anvil issues w fuzz
    result = position_lib.size(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )

    if not zero_for_one:
        size0 = int(liquidity * (1 << 96) / sqrt_price_x96) - int(
            liquidity * (1 << 96) / sqrt_price_x96_next
        )
        assert pytest.approx(result, rel=1e-15) == size0
    else:
        size1 = int((liquidity * (sqrt_price_x96 - sqrt_price_x96_next)) / (1 << 96))
        assert pytest.approx(result, rel=1e-15) == size1

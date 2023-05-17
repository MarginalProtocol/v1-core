import pytest

from math import sqrt
from utils.utils import calc_sqrt_price_x96_next


def test_position_sizes__with_zero_for_one(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    maintenance = 2500
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    # size0 is L * (1/sqrt(P) - 1/sqrt(P'))
    # about ~ 1% of x pool given liquidity delta
    size0 = int(liquidity * (1 << 96) / sqrt_price_x96) - int(
        liquidity * (1 << 96) / sqrt_price_x96_next
    )
    size1 = 0

    result = position_lib.sizes(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )
    assert pytest.approx(result[0], rel=1e-15) == size0
    assert result[1] == size1


def test_position_sizes__with_one_for_zero(position_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    maintenance = 2500
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    # size1 is L * (sqrt(P) - sqrt(P'))
    # about ~ 1% of x pool given liquidity delta
    size0 = 0
    size1 = int((liquidity * (sqrt_price_x96 - sqrt_price_x96_next)) / (1 << 96))

    result = position_lib.sizes(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, zero_for_one
    )
    assert result[0] == size0
    assert pytest.approx(result[1], rel=1e-15) == size1

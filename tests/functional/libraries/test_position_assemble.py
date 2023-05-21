from math import sqrt

from utils.constants import FEE
from utils.utils import calc_sqrt_price_x96_next


def test_position_assemble__with_zero_for_one(position_lib):
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
    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )

    # add fees to the x debt (margin token)
    fees = position_lib.fees(size0, FEE)
    debt0 += fees

    position = (size0, debt0, debt1, insurance0, insurance1, zero_for_one)
    result = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        FEE,
    )
    assert result == position


def test_position_assemble__with_one_for_zero(position_lib):
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
    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )

    # add fees to the y debt (margin token)
    fees = position_lib.fees(size1, FEE)
    debt1 += fees

    position = (size1, debt0, debt1, insurance0, insurance1, zero_for_one)
    result = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        FEE,
    )
    assert result == position

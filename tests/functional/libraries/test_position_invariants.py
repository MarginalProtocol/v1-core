import pytest

from math import sqrt
from utils.utils import calc_sqrt_price_x96_next_open


def test_position_debt_plus_insurance_product__with_zero_for_one(position_lib):
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

    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    result = int(sqrt((insurance0 + debt0) * (insurance1 + debt1)))
    assert pytest.approx(result, rel=1e-13) == liquidity_delta  # TODO: rel error ok?


def test_position_debt_plus_insurance_product__with_one_for_zero(position_lib):
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

    insurance0, insurance1 = position_lib.insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    debt0, debt1 = position_lib.debts(
        sqrt_price_x96_next, liquidity_delta, insurance0, insurance1
    )
    result = int(sqrt((insurance0 + debt0) * (insurance1 + debt1)))
    assert pytest.approx(result, rel=1e-13) == liquidity_delta  # TODO: rel error ok?

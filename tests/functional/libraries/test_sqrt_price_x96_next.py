import pytest
from math import sqrt


def test_sqrt_price_math_x96_next__with_zero_for_one(sqrt_price_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    # position size of ~1% of pool w about 4% to insurance
    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    maintenance = 2500
    munit = 10000

    # sqrt_price_next = sqrt_price * (liquidity + root) / (2 * (liquidity - liquidity_delta))
    prod = (liquidity_delta * (liquidity - liquidity_delta) * munit) // (
        munit + maintenance
    )
    under = liquidity**2 - 4 * prod
    root = int(sqrt(under))

    # sqrt price should be ~ 1% higher
    sqrt_price_x96_next = int(sqrt_price_x96 * (liquidity + root)) // (
        2 * (liquidity - liquidity_delta)
    )

    assert (
        pytest.approx(
            sqrt_price_math_lib.sqrtPriceX96Next(
                liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
            ),
            rel=1e-16,
        )
        == sqrt_price_x96_next
    )
    assert (
        sqrt_price_math_lib.sqrtPriceX96Next(
            liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
        )
        >> 96
    ) == sqrt_price_x96_next >> 96


def test_sqrt_price_math_x96_next__with_one_for_zero(sqrt_price_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    # position size of ~1% of pool w about 4% to insurance
    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    maintenance = 2500
    munit = 10000

    # sqrt_price_next = sqrt_price * (2 * (liquidity - liquidity_delta)) / (liquidity + root)
    prod = (liquidity_delta * (liquidity - liquidity_delta) * munit) // (
        munit + maintenance
    )
    under = liquidity**2 - 4 * prod
    root = int(sqrt(under))

    # sqrt price should be about 1% lower
    sqrt_price_x96_next = int(sqrt_price_x96 * 2 * (liquidity - liquidity_delta)) // (
        liquidity + root
    )

    assert (
        pytest.approx(
            sqrt_price_math_lib.sqrtPriceX96Next(
                liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
            ),
            rel=1e-16,
        )
        == sqrt_price_x96_next
    )
    assert (
        sqrt_price_math_lib.sqrtPriceX96Next(
            liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
        )
        >> 96
    ) == sqrt_price_x96_next >> 96

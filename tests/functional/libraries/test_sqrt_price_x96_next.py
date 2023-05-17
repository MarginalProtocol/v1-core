import pytest
import ape

from hypothesis import given
from hypothesis import strategies as st
from math import sqrt


MAINTENANCE_UNIT = 10000


def calc_sqrt_price_x96_next(
    liquidity: int,
    sqrt_price_x96: int,
    liquidity_delta: int,
    zero_for_one: bool,
    maintenance: int,
) -> int:
    # sqrt_price_next = sqrt_price * (liquidity + root) / (2 * (liquidity - liquidity_delta))
    prod = (liquidity_delta * (liquidity - liquidity_delta) * MAINTENANCE_UNIT) // (
        MAINTENANCE_UNIT + maintenance
    )
    under = liquidity**2 - 4 * prod
    root = int(sqrt(under))

    sqrt_price_x96_next = (
        int(sqrt_price_x96 * (liquidity + root)) // (2 * (liquidity - liquidity_delta))
        if zero_for_one
        else int(sqrt_price_x96 * 2 * (liquidity - liquidity_delta))
        // (liquidity + root)
    )

    return sqrt_price_x96_next


@pytest.mark.parametrize("maintenance", [2500, 5000, 10000])
def test_sqrt_price_math_x96_next__with_zero_for_one(sqrt_price_math_lib, maintenance):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    # position size of ~5/(1+1/M)% of pool w about 5-5/(1+1/M)% to insurance
    liquidity_delta = liquidity * 5 // 100
    zero_for_one = True
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    assert (
        pytest.approx(
            sqrt_price_math_lib.sqrtPriceX96Next(
                liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
            ),
            rel=1e-15,  # TQ: is this enough?
        )
        == sqrt_price_x96_next
    )
    assert (
        sqrt_price_math_lib.sqrtPriceX96Next(
            liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
        )
        >> 96
    ) == (sqrt_price_x96_next >> 96)


@pytest.mark.parametrize("maintenance", [2500, 5000, 10000])
def test_sqrt_price_math_x96_next__with_one_for_zero(sqrt_price_math_lib, maintenance):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    # position size of ~5/(1+1/M)% of pool w about 5-5/(1+1/M)% to insurance
    liquidity_delta = liquidity * 5 // 100
    zero_for_one = False
    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    assert (
        pytest.approx(
            sqrt_price_math_lib.sqrtPriceX96Next(
                liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
            ),
            rel=1e-15,  # Q: is this enough?
        )
        == sqrt_price_x96_next
    )
    assert (
        sqrt_price_math_lib.sqrtPriceX96Next(
            liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
        )
        >> 96
    ) == (sqrt_price_x96_next >> 96)


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [2500, 5000, 10000])
@given(
    x=st.integers(min_value=100, max_value=2**128 - 1),
    y=st.integers(min_value=100, max_value=2**128 - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=1000000 - 1),
    zero_for_one=st.booleans(),
)
def test_sqrt_price_math_x96_next__with_fuzz(
    sqrt_price_math_lib, x, y, liquidity_delta_pc, zero_for_one, maintenance
):
    liquidity = int(sqrt(x * y))
    if liquidity >= 2**128:
        liquidity = 2**128 - 1

    liquidity_delta = liquidity * liquidity_delta_pc // 1000000

    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    sqrt_price_x96_next = calc_sqrt_price_x96_next(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    sqrt_price_next = sqrt_price_x96_next >> 96

    try:
        # Q: is this rel tol enough?
        result_x96 = sqrt_price_math_lib.sqrtPriceX96Next(
            liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
        )
        result = result_x96 >> 96
        assert pytest.approx(result_x96, rel=1e-15) == sqrt_price_x96_next
        assert pytest.approx(result, rel=1e-15) == sqrt_price_next
    except ape.exceptions.ProviderError:
        # some issues with anvil and fuzzing sometimes; ignore these runs
        # TODO: fix
        return

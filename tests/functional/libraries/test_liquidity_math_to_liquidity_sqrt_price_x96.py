import pytest

from hypothesis import given
from hypothesis import strategies as st

from utils.utils import calc_liquidity_sqrt_price_x96_from_reserves


def test_liquidity_math_to_liquidity_sqrt_price_x96(liquidity_math_lib):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves

    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )
    result = liquidity_math_lib.toLiquiditySqrtPriceX96(reserve0, reserve1)
    assert (
        pytest.approx(liquidity, rel=1e-15) == result[0]
    )  # TODO: appropriate rel error?
    assert pytest.approx(sqrt_price_x96, rel=1e-15) == result[1]


@pytest.mark.fuzzing
@given(
    reserve0=st.integers(min_value=1, max_value=2**256 - 1),
    reserve1=st.integers(min_value=1, max_value=2**256 - 1),
)
def test_liquidity_math_to_liquidity_sqrt_price_x96__with_fuzz(
    liquidity_math_lib, reserve0, reserve1
):
    # ignore cases where liquidity won't fit in uint128
    if reserve0 * reserve1 > 2**256 - 1:
        return

    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )
    result = liquidity_math_lib.toLiquiditySqrtPriceX96(reserve0, reserve1)
    assert (
        pytest.approx(liquidity, rel=1e-15) == result[0]
    )  # TODO: appropriate rel error?
    assert pytest.approx(sqrt_price_x96, rel=1e-15) == result[1]

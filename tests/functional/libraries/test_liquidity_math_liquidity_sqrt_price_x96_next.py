import pytest
from ape import reverts

from utils.utils import calc_liquidity_sqrt_price_x96_from_reserves


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_positive_amount1_positive(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics mint
    amount0 = reserve0 * 100 // 10000  # 1% of liquidity added
    amount1 = reserve1 * 100 // 10000  # 1% of liquidity added

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )
    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_negative_amount1_negative(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics burn
    amount0 = -reserve0 * 100 // 10000  # 1% of liquidity removed
    amount1 = -reserve1 * 100 // 10000  # 1% of liquidity removed

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )
    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_positive_amount1_negative(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics swap of zero for one
    amount0 = reserve0 * 100 // 10000  # 1% of liquidity added
    amount1 = (
        liquidity**2 // (reserve0 + amount0) - reserve1
    )  # ~1% of liquidity removed

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_negative_amount1_positive(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics swap of one for zero
    amount0 = -reserve0 * 100 // 10000  # 1% of liquidity removed
    amount1 = (
        liquidity**2 // (reserve0 + amount0) - reserve1
    )  # ~1% of liquidity added

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_positive_amount1_zero(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics adding fees
    amount0 = reserve0 * 1 // 10000  # 0.01% of liquidity added
    amount1 = 0

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__with_amount0_zero_amount1_positive(
    liquidity_math_lib,
):
    reserve0 = int(125.04e12)  # e.g. USDC reserves
    reserve1 = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0, reserve1
    )

    # mimics adding fees
    amount0 = 0
    amount1 = reserve1 * 1 // 10000  # 0.01% of liquidity added

    result = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        amount0,
        amount1,
    )

    (liquidity_next, sqrt_price_x96_next) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )

    assert pytest.approx(result[0], rel=1e-16) == liquidity_next
    assert pytest.approx(result[1], rel=1e-16) == sqrt_price_x96_next


def test_liquidity_math_liquidity_sqrt_price_x96_next__reverts_when_amount1_out_greater_than_reserve(
    liquidity_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(x, y)
    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)

    amount0 = reserve0 * 100 // 10000  # 1% of liquidity added
    amount1 = -reserve1

    # TODO: fix issues w gh actions
    # TODO: with reverts(sqrt_price_math_lib.Amount1ExceedsReserve1):
    with reverts():
        liquidity_math_lib.liquiditySqrtPriceX96Next(
            liquidity,
            sqrt_price_x96,
            amount0,
            amount1,
        )


def test_liquidity_math_liquidity_sqrt_price_x96_next__reverts_when_amount0_out_greater_than_reserve(
    liquidity_math_lib, sqrt_price_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    (liquidity, sqrt_price_x96) = calc_liquidity_sqrt_price_x96_from_reserves(x, y)
    (reserve0, reserve1) = liquidity_math_lib.toAmounts(liquidity, sqrt_price_x96)

    amount0 = -reserve0
    amount1 = reserve1 * 100 // 10000  # 1% of liquidity added

    # TODO: fix issues w gh actions
    # TODO: with reverts(sqrt_price_math_lib.Amount0ExceedsReserve0):
    with reverts():
        liquidity_math_lib.liquiditySqrtPriceX96Next(
            liquidity,
            sqrt_price_x96,
            amount0,
            amount1,
        )


@pytest.mark.fuzzing
def test_liquidity_math_liquidity_sqrt_price_x96_next__with_fuzz(liquidity_math_lib):
    pass

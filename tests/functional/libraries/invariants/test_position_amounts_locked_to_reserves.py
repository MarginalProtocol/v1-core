import pytest

from math import sqrt
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    MINIMUM_LIQUIDITY,
    MINIMUM_SIZE,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
)
from utils.utils import (
    calc_tick_from_sqrt_price_x96,
    calc_sqrt_price_x96_next_open,
    calc_debts,
    calc_insurances,
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
)


# @dev simulates reserves state transition on liquidate
def test_position_amounts_locked_to_reserves__with_zero_for_one(
    position_lib, sqrt_price_math_lib, liquidity_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    fee = 1000

    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    zero_for_one = True

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000

    # (liquidity_later, sqrt_price_later) are (L, sqrt(P)) pool state before attempt to liquidate
    liquidity_later = (liquidity * 75) // 100
    sqrt_price_x96_later = (
        sqrt_price_x96 * 110
    ) // 100  # price up given position short

    # assemble origin position at (liquidity, sqrt_price_x96) pool state
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity,
        sqrt_price_x96,
        liquidity_delta,
        zero_for_one,
        maintenance,
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        0,  # @dev irrelevant for test
        0,
        0,
    )

    # set margin to minimum to test at lowest liquidity returned levels (excluding funding changes to debt)
    position.margin = position_lib.marginMinimum(position, maintenance)
    assert position.liquidityLocked == liquidity_delta

    # factor in fees on open
    fees = position_lib.fees(position.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    (liquidity_next, _) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity - liquidity_delta, sqrt_price_x96_next, fees0, fees1
    )
    liquidity_delta_fees = liquidity_next - (liquidity - liquidity_delta)

    # simulate liquidation effect on reserves later
    (amount0, amount1) = position_lib.amountsLocked(position)
    assert amount0 == position.insurance0
    assert (
        amount1
        == position.size + position.margin + position.debt1 + position.insurance1
    )

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity_later,
        sqrt_price_x96_later,
        amount0 + fees0,
        amount1 + fees1,
    )

    liquidity_delta_after = liquidity_after - liquidity_later

    assert liquidity_delta_after + liquidity_delta_fees >= position.liquidityLocked
    assert sqrt_price_x96_after > sqrt_price_x96_later  # price pushes further


def test_position_amounts_locked_to_reserves__with_one_for_zero(
    position_lib, sqrt_price_math_lib, liquidity_math_lib
):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    liquidity = int(sqrt(x * y))
    sqrt_price = int(sqrt(y / x))
    fee = 1000

    sqrt_price_x96 = sqrt_price << 96
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    zero_for_one = False

    liquidity_delta = liquidity * 5 // 100
    maintenance = 250000

    # (liquidity_later, sqrt_price_later) are (L, sqrt(P)) pool state before attempt to liquidate
    liquidity_later = (liquidity * 75) // 100
    sqrt_price_x96_later = (
        sqrt_price_x96 * 90
    ) // 100  # price down given position long

    # assemble origin position at (liquidity, sqrt_price_x96) pool state
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity,
        sqrt_price_x96,
        liquidity_delta,
        zero_for_one,
        maintenance,
    )

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        0,  # @dev irrelevant for test
        0,
        0,
    )

    # set margin to minimum to test at lowest liquidity returned levels (excluding funding changes to debt)
    position.margin = position_lib.marginMinimum(position, maintenance)
    assert position.liquidityLocked == liquidity_delta

    # factor in fees on open
    fees = position_lib.fees(position.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    (liquidity_next, _) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity - liquidity_delta, sqrt_price_x96_next, fees0, fees1
    )
    liquidity_delta_fees = liquidity_next - (liquidity - liquidity_delta)

    # simulate liquidation effect on reserves later
    (amount0, amount1) = position_lib.amountsLocked(position)
    assert (
        amount0
        == position.size + position.margin + position.debt0 + position.insurance0
    )
    assert amount1 == position.insurance1

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity_later,
        sqrt_price_x96_later,
        amount0 + fees0,
        amount1 + fees1,
    )

    liquidity_delta_after = liquidity_after - liquidity_later
    assert liquidity_delta_after + liquidity_delta_fees >= position.liquidityLocked
    assert sqrt_price_x96_after < sqrt_price_x96_later  # price pushes further


@pytest.mark.fuzzing
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
@settings(deadline=timedelta(milliseconds=1000), max_examples=10000)
@given(
    liquidity=st.integers(min_value=MINIMUM_LIQUIDITY + 2, max_value=2**128 - 1),
    liquidity_delta_pc=st.integers(min_value=1, max_value=950000000),
    sqrt_price_x96=st.integers(min_value=MIN_SQRT_RATIO, max_value=MAX_SQRT_RATIO - 1),
    liquidity_later=st.integers(
        min_value=MINIMUM_LIQUIDITY + 2, max_value=2**128 - 1
    ),
    sqrt_price_x96_later_pc=st.integers(
        min_value=100000000, max_value=10000000000
    ),  # 10% to 10x
    zero_for_one=st.booleans(),
)
def test_position_amounts_locked_to_reserves__with_fuzz(
    position_lib,
    sqrt_price_math_lib,
    liquidity_math_lib,
    liquidity,
    liquidity_delta_pc,
    sqrt_price_x96,
    liquidity_later,
    sqrt_price_x96_later_pc,
    zero_for_one,
    maintenance,
):
    # calc liquidity, sqrt price before to ignore overflow edge cases
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    if (
        reserve0 <= 0
        or reserve0 >= 2**128 - 1
        or reserve1 <= 0
        or reserve1 >= 2**128 - 1
    ):
        return

    fee = 1000  # 10 bps
    liquidity_delta_max = liquidity - MINIMUM_LIQUIDITY - 1
    liquidity_delta = (liquidity_delta_max * liquidity_delta_pc) // 1000000000
    if liquidity_delta == 0:
        return

    sqrt_price_x96_later = (sqrt_price_x96 * sqrt_price_x96_later_pc) // 1000000000
    calc_sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    if (
        calc_sqrt_price_x96_next < MIN_SQRT_RATIO
        or calc_sqrt_price_x96_next >= MAX_SQRT_RATIO
    ):
        return
    elif (
        sqrt_price_x96_later <= MIN_SQRT_RATIO or sqrt_price_x96_later >= MAX_SQRT_RATIO
    ):
        return
    elif (zero_for_one and sqrt_price_x96_later < sqrt_price_x96) or (
        not zero_for_one and sqrt_price_x96_later > sqrt_price_x96
    ):
        return

    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )

    # calculate insurance, debt values first to check will fit in uint128
    calc_insurance0, calc_insurance1 = calc_insurances(
        liquidity, sqrt_price_x96, sqrt_price_x96_next, liquidity_delta, zero_for_one
    )
    calc_debt0, calc_debt1 = calc_debts(
        sqrt_price_x96_next, liquidity_delta, calc_insurance0, calc_insurance1
    )
    if (
        calc_insurance0 <= 0
        or calc_insurance0 >= 2**128 - 1
        or calc_insurance1 <= 0
        or calc_insurance1 >= 2**128 - 1
    ):
        return
    elif (
        calc_debt0 <= 0
        or calc_debt0 >= 2**128 - 1
        or calc_debt1 <= 0
        or calc_debt1 >= 2**128 - 1
    ):
        return

    position = position_lib.assemble(
        liquidity,
        sqrt_price_x96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick,
        0,  # @dev irrelevant for test
        0,
        0,
    )

    # set margin to minimum to test at lowest liquidity returned levels (excluding funding changes to debt)
    # TODO: margin minimum as utils.py function
    position.margin = position_lib.marginMinimum(position, maintenance)
    assert position.liquidityLocked == liquidity_delta

    if (
        position.size < MINIMUM_SIZE
        or position.debt0 < MINIMUM_SIZE
        or position.debt1 < MINIMUM_SIZE
        or position.insurance0 < MINIMUM_SIZE
        or position.insurance1 < MINIMUM_SIZE
    ):
        return

    # factor in fees on open
    fees = position_lib.fees(position.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    (liquidity_next, _) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity - liquidity_delta, sqrt_price_x96_next, fees0, fees1
    )
    liquidity_delta_fees = liquidity_next - (liquidity - liquidity_delta)

    # simulate liquidation effect on reserves later
    (amount0, amount1) = position_lib.amountsLocked(position)
    if zero_for_one:
        assert amount0 == position.insurance0
        assert (
            amount1
            == position.size + position.margin + position.debt1 + position.insurance1
        )
    else:
        assert (
            amount0
            == position.size + position.margin + position.debt0 + position.insurance0
        )
        assert amount1 == position.insurance1

    # calc liquidity, sqrt price after to ignore overflow edge cases
    (reserve0_later, reserve1_later) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_later, sqrt_price_x96_later
    )
    (
        calc_liquidity_after,
        calc_sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0_later + amount0, reserve1_later + amount1
    )
    if calc_liquidity_after >= 2**128:
        return
    elif (
        calc_sqrt_price_x96_after < MIN_SQRT_RATIO
        or calc_sqrt_price_x96_after >= MAX_SQRT_RATIO
    ):
        return

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity_later,
        sqrt_price_x96_later,
        amount0,
        amount1,
    )

    liquidity_delta_after = liquidity_after - liquidity_later
    assert liquidity_delta_after + liquidity_delta_fees >= position.liquidityLocked

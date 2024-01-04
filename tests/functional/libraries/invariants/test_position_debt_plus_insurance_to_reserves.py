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


# @dev simulates reserves state transition on settle
@pytest.mark.parametrize("liquidity_later_pc", [5000, 7500, 10000, 12500, 15000])
@pytest.mark.parametrize(
    "sqrt_price_x96_later_pc",
    [7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000],
)
def test_position_debt_plus_insurance_to_reserves__with_zero_for_one(
    position_lib,
    sqrt_price_math_lib,
    liquidity_math_lib,
    liquidity_later_pc,
    sqrt_price_x96_later_pc,
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

    # (liquidity_later, sqrt_price_later) are (L, sqrt(P)) pool state before attempt to settle
    liquidity_later = (liquidity * liquidity_later_pc) // 10000
    sqrt_price_x96_later = (sqrt_price_x96 * sqrt_price_x96_later_pc) // 10000

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

    # simulate settlement effect on reserves later
    (amount0_unlocked, amount1_unlocked) = position_lib.amountsLocked(position)
    amount0_to_pool = amount0_unlocked + position.debt0
    amount1_to_pool = amount1_unlocked - position.size - position.margin

    assert amount0_to_pool == position.debt0 + position.insurance0
    assert amount1_to_pool == position.debt1 + position.insurance1

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity_later,
        sqrt_price_x96_later,
        amount0_to_pool,
        amount1_to_pool,
    )

    liquidity_delta_after = liquidity_after - liquidity_later
    assert liquidity_delta_after + liquidity_delta_fees >= position.liquidityLocked


@pytest.mark.parametrize("liquidity_later_pc", [5000, 7500, 10000, 12500, 15000])
@pytest.mark.parametrize(
    "sqrt_price_x96_later_pc",
    [7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000],
)
def test_position_debt_plus_insurance_to_reserves__with_one_for_zero(
    position_lib,
    sqrt_price_math_lib,
    liquidity_math_lib,
    liquidity_later_pc,
    sqrt_price_x96_later_pc,
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

    # (liquidity_later, sqrt_price_later) are (L, sqrt(P)) pool state before attempt to settle
    liquidity_later = (liquidity * liquidity_later_pc) // 10000
    sqrt_price_x96_later = (sqrt_price_x96 * sqrt_price_x96_later_pc) // 10000

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

    # simulate settlement effect on reserves later
    (amount0_unlocked, amount1_unlocked) = position_lib.amountsLocked(position)
    amount0_to_pool = amount0_unlocked - position.size - position.margin
    amount1_to_pool = amount1_unlocked + position.debt1

    assert amount0_to_pool == position.debt0 + position.insurance0
    assert amount1_to_pool == position.debt1 + position.insurance1

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity_later,
        sqrt_price_x96_later,
        amount0_to_pool,
        amount1_to_pool,
    )

    liquidity_delta_after = liquidity_after - liquidity_later
    assert liquidity_delta_after + liquidity_delta_fees >= position.liquidityLocked


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
        min_value=10000, max_value=1000000
    ),  # 1% to 100x
    zero_for_one=st.booleans(),
)
def test_position_debt_plus_insurance_to_reserves__with_fuzz(
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

    sqrt_price_x96_later = (
        (sqrt_price_x96 * sqrt_price_x96_later_pc) // 10000  # short so increasing price
        if zero_for_one
        else (sqrt_price_x96 * 10000)
        // sqrt_price_x96_later_pc  # long so decreasing price
    )
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

    # simulate settlement effect on reserves later
    (amount0_unlocked, amount1_unlocked) = position_lib.amountsLocked(position)
    if zero_for_one:
        amount0_to_pool = amount0_unlocked + position.debt0
        amount1_to_pool = amount1_unlocked - position.size - position.margin
    else:
        amount0_to_pool = amount0_unlocked - position.size - position.margin
        amount1_to_pool = amount1_unlocked + position.debt1

    assert amount0_to_pool == position.debt0 + position.insurance0
    assert amount1_to_pool == position.debt1 + position.insurance1

    # calc liquidity, sqrt price after to ignore overflow edge cases
    (reserve0_later, reserve1_later) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_later, sqrt_price_x96_later
    )
    (
        calc_liquidity_after,
        calc_sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0_later + amount0_to_pool, reserve1_later + amount1_to_pool
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
        amount0_to_pool,
        amount1_to_pool,
    )

    liquidity_delta_after = liquidity_after - liquidity_later
    assert liquidity_delta_after + liquidity_delta_fees >= position.liquidityLocked

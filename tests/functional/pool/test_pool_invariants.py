import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import (
    get_position_key,
    calc_amounts_from_liquidity_sqrt_price_x96,
)


def test_pool_open_then_settle_replicates_swap_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    size = int(
        amount1
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # size will be ~ 1%
    margin = (
        int(1.25 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.25x for breathing room
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    # cache balances prior to check sender receives size from pool
    # for debt sent to pool from sender post open -> settle
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    id = state.totalPositions
    key = get_position_key(callee.address, id)
    callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    result = pool_initialized_with_liquidity.positions(key)
    fees1 = position_lib.fees(result.size, fee)

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # need debt0 == amount0 (in) and size == -amount1 (out)
    assert pytest.approx(result.debt0, rel=1e-14) == amount0
    assert pytest.approx(result.size, rel=1e-14) == -amount1

    # now settle and check state_after liquidity, sqrtPriceX96 do in fact
    # replicate a swap
    callee.settle(
        pool_initialized_with_liquidity.address,
        sender.address,
        id,
        sender=sender,
    )

    state_after = pool_initialized_with_liquidity.state()

    # TODO: fix for factoring in fee contribution so more exact
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-5) == sqrt_price_x96_next
    assert pytest.approx(state_after.liquidity, rel=1e-5) == state.liquidity
    assert state_after.liquidity > state.liquidity  # for fees

    # check balances after open -> settle replicate swap of debt0 (x) in, size (y) out
    balance0_after_sender = token0.balanceOf(sender.address)
    balance1_after_sender = token1.balanceOf(sender.address)

    balance0_after_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_after_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    amount0_to_sender = balance0_after_sender - balance0_sender
    amount1_to_sender = balance1_after_sender - balance1_sender

    amount0_to_pool = balance0_after_pool - balance0_pool
    amount1_to_pool = balance1_after_pool - balance1_pool

    # be sure to factor in fees in margin token from sender to pool
    assert amount0_to_sender == -result.debt0
    assert amount1_to_sender == result.size - fees1

    assert amount0_to_pool == result.debt0
    assert amount1_to_pool == -result.size + fees1


def test_pool_open_then_settle_replicates_swap_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    size = int(
        amount0
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # size will be ~ 1%
    margin = (
        int(1.25 * size) * maintenance // MAINTENANCE_UNIT
    )  # 1.25x for breathing room
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    # cache balances prior to check sender receives size from pool
    # for debt sent to pool from sender post open -> settle
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    id = state.totalPositions
    key = get_position_key(callee.address, id)
    callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    result = pool_initialized_with_liquidity.positions(key)
    fees0 = position_lib.fees(result.size, fee)

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # need debt1 == amount1 (in) and size == -amount0 (out)
    assert pytest.approx(result.debt1, rel=1e-14) == amount1
    assert pytest.approx(result.size, rel=1e-14) == -amount0

    # now settle and check state_after liquidity, sqrtPriceX96 do in fact
    # replicate a swap
    callee.settle(
        pool_initialized_with_liquidity.address,
        sender.address,
        id,
        sender=sender,
    )

    state_after = pool_initialized_with_liquidity.state()

    # TODO: fix for factoring in fee contribution so more exact
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-5) == sqrt_price_x96_next
    assert pytest.approx(state_after.liquidity, rel=1e-5) == state.liquidity
    assert state_after.liquidity > state.liquidity  # for fees

    # check balances after open -> settle replicate swap of debt1 (y) in, size (x) out
    balance0_after_sender = token0.balanceOf(sender.address)
    balance1_after_sender = token1.balanceOf(sender.address)

    balance0_after_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_after_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    amount0_to_sender = balance0_after_sender - balance0_sender
    amount1_to_sender = balance1_after_sender - balance1_sender

    amount0_to_pool = balance0_after_pool - balance0_pool
    amount1_to_pool = balance1_after_pool - balance1_pool

    # be sure to factor in fees in margin token from sender to pool
    assert amount0_to_sender == result.size - fees0
    assert amount1_to_sender == -result.debt1

    assert amount0_to_pool == -result.size + fees0
    assert amount1_to_pool == result.debt1

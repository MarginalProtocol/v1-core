import pytest

from utils.utils import get_position_key, calc_tick_from_sqrt_price_x96


def test_pool_liquidate__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    zero_for_one_position_id,
    chain,
):
    key = get_position_key(sender.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    reserve0, reserve1 = liquidity_math_lib.toAmounts(
        state.liquidity, state.sqrtPriceX96
    )

    amount0, amount1 = position_lib.amountsLocked(position)
    amount1 += position.margin

    liquidity_next, sqrt_price_x96_next = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0 + amount0, reserve1 + amount1
    )
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = tick_next
    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative_next

    pool_initialized_with_liquidity.liquidate(
        bob.address, sender.address, zero_for_one_position_id, sender=alice
    )

    assert pool_initialized_with_liquidity.state() == state


def test_pool_liquidate__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    liquidity_math_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    one_for_zero_position_id,
    chain,
):
    # TODO: fix one_for_zero_position_id fixture when multiple tests run as get state.totalPositions = 2 for some reason
    key = get_position_key(sender.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    reserve0, reserve1 = liquidity_math_lib.toAmounts(
        state.liquidity, state.sqrtPriceX96
    )

    amount0, amount1 = position_lib.amountsLocked(position)
    amount0 += position.margin

    liquidity_next, sqrt_price_x96_next = liquidity_math_lib.toLiquiditySqrtPriceX96(
        reserve0 + amount0, reserve1 + amount1
    )
    tick_next = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = tick_next
    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative_next

    pool_initialized_with_liquidity.liquidate(
        bob.address, sender.address, one_for_zero_position_id, sender=alice
    )

    result = pool_initialized_with_liquidity.state()
    assert result == state


def test_pool_liquidate__updates_reserves_locked_with_zero_for_one():
    pass


def test_pool_liquidate__updates_reserves_locked_with_one_for_zero():
    pass


def test_pool_liquidate__sets_position_with_zero_for_one():
    pass


def test_pool_liquidate__sets_position_with_one_for_zero():
    pass


def test_pool_liquidate__transfers_funds_with_zero_for_one():
    pass


def test_pool_liquidate__transfers_funds_with_one_for_zero():
    pass


def test_pool_liquidate__emits_liquidate_with_zero_for_one():
    pass


def test_pool_liquidate__emits_liquidate_with_one_for_zero():
    pass


def test_pool_liquidate__reverts_when_not_position():
    pass


def test_pool_liquidate__reverts_when_position_safe_with_zero_for_one():
    pass


def test_pool_liquidate__reverts_when_position_safe_with_one_for_zero():
    pass


# TODO:
@pytest.mark.fuzzing
def test_pool_liquidate__with_fuzz():
    pass

import pytest

from utils.constants import (
    FUNDING_PERIOD,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
)
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
    get_position_key,
)


@pytest.fixture
def zero_for_one_position_id(
    pool_initialized_with_liquidity, callee, sender, token0, token1
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
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

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    return int(tx.return_value)


@pytest.fixture
def one_for_zero_position_id(
    pool_initialized_with_liquidity, callee, sender, token0, token1
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
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

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        callee.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    return int(tx.return_value)


def test_pool_settle__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    position_lib,
    liquidity_math_lib,
    chain,
):
    key = get_position_key(callee.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    # sync state
    block_timestamp_next = chain.pending_timestamp
    state.tickCumulative += state.tick * (block_timestamp_next - state.blockTimestamp)
    state.blockTimestamp = block_timestamp_next

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one_position_id,
        sender=sender,
    )

    # sync position for funding
    position = position_lib.sync(
        position,
        state.tickCumulative,
        position.oracleTickCumulativeStart,  # @dev doesn't change given naive mock implementation
        FUNDING_PERIOD,
    )

    # position debt + insurance to reserves
    amount0_reserves = position.debt0 + position.insurance0
    amount1_reserves = position.debt1 + position.insurance1
    (
        liquidity_next,
        sqrt_price_x96_next,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0_reserves,
        amount1_reserves,
    )
    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    assert pool_initialized_with_liquidity.state() == state


def test_pool_settle__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    alice,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    position_lib,
    liquidity_math_lib,
    chain,
):
    key = get_position_key(callee.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    state = pool_initialized_with_liquidity.state()

    # sync state
    block_timestamp_next = chain.pending_timestamp
    state.tickCumulative += state.tick * (block_timestamp_next - state.blockTimestamp)
    state.blockTimestamp = block_timestamp_next

    callee.settle(
        pool_initialized_with_liquidity.address,
        alice.address,
        one_for_zero_position_id,
        sender=sender,
    )

    # sync position for funding
    position = position_lib.sync(
        position,
        state.tickCumulative,
        position.oracleTickCumulativeStart,  # @dev doesn't change given naive mock implementation
        FUNDING_PERIOD,
    )

    # position debt + insurance to reserves
    amount0_reserves = position.debt0 + position.insurance0
    amount1_reserves = position.debt1 + position.insurance1
    (
        liquidity_next,
        sqrt_price_x96_next,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0_reserves,
        amount1_reserves,
    )
    state.liquidity = liquidity_next
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    assert pool_initialized_with_liquidity.state() == state


def test_pool_settle__updates_reserves_locked_with_zero_for_one():
    pass


def test_pool_settle__updates_reserves_locked_with_one_for_zero():
    pass


def test_pool_settle__sets_position_with_zero_for_one():
    pass


def test_pool_settle__sets_position_with_one_for_zero():
    pass


def test_pool_settle__transfers_funds_with_zero_for_one():
    pass


def test_pool_settle__transfers_funds_with_one_for_zero():
    pass


def test_pool_settle__calls_settle_callback_with_zero_for_one():
    pass


def test_pool_settle__calls_settle_callback_with_one_for_zero():
    pass


def test_pool_settle__emits_settle_with_zero_for_one():
    pass


def test_pool_settle__emits_settle_with_one_for_zero():
    pass


def test_pool_settle__reverts_when_not_position_id():
    pass


def test_pool_settle__reverts_when_amount1_less_than_min():
    pass


def test_pool_settle__reverts_when_amount0_less_than_min():
    pass


# TODO:
@pytest.mark.fuzzing
def test_pool_settle__with_fuzz():
    pass

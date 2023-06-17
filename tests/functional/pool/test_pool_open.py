import pytest

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import (
    get_position_key,
    calc_tick_from_sqrt_price_x96,
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
)


def test_pool_open__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

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

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    # factor in fees on size to available liquidity, sqrtP update
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees1 = position_lib.fees(position.size, fee)
    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    # @dev sqrt in OZ solidity results in slight diff with python math.sqrt
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(reserve0, reserve1 + fees1)

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next
    state.totalPositions += 1

    result = pool_initialized_with_liquidity.state()
    assert pytest.approx(result.liquidity, rel=1e-16) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-16) == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions


def test_pool_open__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

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

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    # factor in fees on size to available liquidity, sqrtP update
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees0 = position_lib.fees(position.size, fee)
    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    # @dev sqrt in OZ solidity results in slight diff with python math.sqrt
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(reserve0 + fees0, reserve1)

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next
    state.totalPositions += 1

    result = pool_initialized_with_liquidity.state()
    assert pytest.approx(result.liquidity, rel=1e-16) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-16) == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions


def test_pool_open__updates_reserves_locked_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )

    # get amounts locked to back position
    (amount0_locked, amount1_locked) = position_lib.amountsLocked(position)
    reserve0_locked += amount0_locked
    reserve1_locked += amount1_locked

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.reservesLocked() == (
        reserve0_locked,
        reserve1_locked,
    )


def test_pool_open__updates_reserves_locked_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )

    # get amounts locked to back position
    (amount0_locked, amount1_locked) = position_lib.amountsLocked(position)
    reserve0_locked += amount0_locked
    reserve1_locked += amount1_locked

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.reservesLocked() == (
        reserve0_locked,
        reserve1_locked,
    )


def test_pool_open__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    reward = pool_initialized_with_liquidity.reward()

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

    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    rewards = position_lib.liquidationRewards(position.size, reward)

    position.rewards = rewards
    position.margin = margin

    id = state.totalPositions
    key = get_position_key(alice.address, id)
    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    result = pool_initialized_with_liquidity.positions(key)
    assert tx.return_value[0] == id
    assert tx.return_value[1] == position.size
    assert result == position


def test_pool_open__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    reward = pool_initialized_with_liquidity.reward()

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

    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    rewards = position_lib.liquidationRewards(position.size, reward)

    position.rewards = rewards
    position.margin = margin

    id = state.totalPositions
    key = get_position_key(alice.address, id)
    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    result = pool_initialized_with_liquidity.positions(key)
    assert tx.return_value[0] == id
    assert tx.return_value[1] == position.size
    assert result == position


def test_pool_open__transfers_funds_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()
    reward = pool_initialized_with_liquidity.reward()

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)
    rewards = position_lib.liquidationRewards(position.size, reward)

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    amount0 = token0.balanceOf(pool_initialized_with_liquidity.address) - balance0
    amount1 = token1.balanceOf(pool_initialized_with_liquidity.address) - balance1

    # callee sends margin + fees + rewards in margin token
    assert amount0 == 0
    assert amount1 == margin + fees + rewards


def test_pool_open__transfers_funds_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()
    reward = pool_initialized_with_liquidity.reward()

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)
    rewards = position_lib.liquidationRewards(position.size, reward)

    balance0 = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1 = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    amount0 = token0.balanceOf(pool_initialized_with_liquidity.address) - balance0
    amount1 = token1.balanceOf(pool_initialized_with_liquidity.address) - balance1

    # callee sends margin + fees + rewards in margin token
    assert amount0 == margin + fees + rewards
    assert amount1 == 0


def test_pool_open__adds_protocol_fees_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    admin,
    token0,
    token1,
    chain,
):
    pool_initialized_with_liquidity.setFeeProtocol(10, sender=admin)

    state = pool_initialized_with_liquidity.state()
    protocol_fees = pool_initialized_with_liquidity.protocolFees()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

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

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    # factor in fees on size to available liquidity, sqrtP update
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees1 = position_lib.fees(position.size, fee)
    # factor in protocol fees
    delta = fees1 // state.feeProtocol
    fees1 -= delta
    protocol_fees.token1 += delta

    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    # @dev sqrt in OZ solidity results in slight diff with python math.sqrt
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(reserve0, reserve1 + fees1)

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next
    state.totalPositions += 1

    result = pool_initialized_with_liquidity.state()
    assert pytest.approx(result.liquidity, rel=1e-16) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-16) == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions

    assert pool_initialized_with_liquidity.protocolFees() == protocol_fees


def test_pool_open__adds_protocol_fees_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    admin,
    token0,
    token1,
    chain,
):
    pool_initialized_with_liquidity.setFeeProtocol(10, sender=admin)

    state = pool_initialized_with_liquidity.state()
    protocol_fees = pool_initialized_with_liquidity.protocolFees()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

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

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    # factor in fees on size to available liquidity, sqrtP update
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees0 = position_lib.fees(position.size, fee)
    # factor in protocol fees
    delta = fees0 // state.feeProtocol
    fees0 -= delta
    protocol_fees.token0 += delta

    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    # @dev sqrt in OZ solidity results in slight diff with python math.sqrt
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(reserve0 + fees0, reserve1)

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next
    state.totalPositions += 1

    result = pool_initialized_with_liquidity.state()

    assert pytest.approx(result.liquidity, rel=1e-16) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-16) == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions

    assert pool_initialized_with_liquidity.protocolFees() == protocol_fees


def test_pool_open__calls_open_callback_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()
    reward = pool_initialized_with_liquidity.reward()

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)
    rewards = position_lib.liquidationRewards(position.size, reward)

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    events = tx.decode_logs(callee.OpenCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == 0
    assert event.amount1Owed == margin + fees + rewards
    assert event.sender == sender.address


def test_pool_open__calls_open_callback_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()
    reward = pool_initialized_with_liquidity.reward()

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
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)
    rewards = position_lib.liquidationRewards(position.size, reward)

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )

    events = tx.decode_logs(callee.OpenCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == margin + fees + rewards
    assert event.amount1Owed == 0
    assert event.sender == sender.address


def test_pool_open__emits_open_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

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

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    state = pool_initialized_with_liquidity.state()
    id, _ = tx.return_value

    events = tx.decode_logs(pool_initialized_with_liquidity.Open)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.owner == alice.address
    assert event.id == id
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.margin == margin


def test_pool_open__emits_open_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

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

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    state = pool_initialized_with_liquidity.state()
    id, _ = tx.return_value

    events = tx.decode_logs(pool_initialized_with_liquidity.Open)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.owner == alice.address
    assert event.id == id
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.margin == margin


def test_pool_open__reverts_when_liquidity_delta_greater_than_liquidity_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity
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

    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_liquidity_delta_greater_than_liquidity_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity
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

    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_sqrt_price_limit_x96_greater_than_sqrt_price_x96_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = True
    sqrt_price_limit_x96 = state.sqrtPriceX96 + 1
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

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_sqrt_price_limit_x96_less_than_min_sqrt_ratio_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO
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

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_sqrt_price_limit_x96_less_than_sqrt_price_x96_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = False
    sqrt_price_limit_x96 = state.sqrtPriceX96 - 1

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

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_sqrt_price_limit_x96_greater_than_max_sqrt_ratio_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO

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

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_sqrt_price_x96_next_less_than_sqrt_price_limit_x96_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = True

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity,
        state.sqrtPriceX96,
        liquidity_delta,
        zero_for_one,
        maintenance,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next + 1

    with reverts(
        pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit,
        sqrtPriceX96Next=sqrt_price_x96_next,
    ):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_sqrt_price_x96_next_greater_than_sqrt_price_limit_x96_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = False

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

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity,
        state.sqrtPriceX96,
        liquidity_delta,
        zero_for_one,
        maintenance,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next - 1

    with reverts(
        pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit,
        sqrtPriceX96Next=sqrt_price_x96_next,
    ):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_amount1_transferred_less_than_min_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee_below_min1,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    liquidity_delta = state.liquidity * 5 // 100
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

    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
        callee_below_min1.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_amount0_transferred_less_than_min_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee_below_min0,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 5 // 100
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

    with reverts(pool_initialized_with_liquidity.Amount0LessThanMin):
        callee_below_min0.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_margin_less_than_min_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    margin_min = position_lib.marginMinimum(position, maintenance)
    margin = margin_min - 1

    with reverts(
        pool_initialized_with_liquidity.MarginLessThanMin, marginMinimum=margin_min
    ):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_margin_less_than_min_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    margin_min = position_lib.marginMinimum(position, maintenance)
    margin = margin_min - 1

    with reverts(
        pool_initialized_with_liquidity.MarginLessThanMin, marginMinimum=margin_min
    ):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


# TODO:
@pytest.mark.fuzzing
def test_pool_open__with_fuzz():
    pass

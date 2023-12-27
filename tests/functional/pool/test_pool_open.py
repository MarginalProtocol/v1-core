import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    MINIMUM_LIQUIDITY,
)
from utils.utils import (
    get_position_key,
    calc_tick_from_sqrt_price_x96,
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
    calc_sqrt_price_x96_next_open,
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

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
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
    assert pytest.approx(result.liquidity, rel=1e-15) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-15) == state.sqrtPriceX96
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

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
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
    assert pytest.approx(result.liquidity, rel=1e-15) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-15) == state.sqrtPriceX96
    assert result.tick == state.tick
    assert result.blockTimestamp == state.blockTimestamp
    assert result.tickCumulative == state.tickCumulative
    assert result.totalPositions == state.totalPositions


def test_pool_open__updates_liquidity_locked_with_zero_for_one(
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
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    position.margin = margin

    # get liquidity locked to back position
    liquidity_locked += position.liquidityLocked

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked


def test_pool_open__updates_liquidity_locked_with_one_for_zero(
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
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    position.margin = margin

    # get amounts locked to back position
    liquidity_locked += position.liquidityLocked

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    assert pool_initialized_with_liquidity.liquidityLocked() == liquidity_locked


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

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    block_timestamp = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        block_timestamp,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    position.margin = margin
    position.rewards = rewards

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
        value=rewards,
    )
    return_log = tx.decode_logs(callee.OpenReturn)[0]

    result = pool_initialized_with_liquidity.positions(key)
    assert return_log.id == id
    assert return_log.size == position.size
    assert return_log.debt == position.debt0
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

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    block_timestamp = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        block_timestamp,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    position.margin = margin
    position.rewards = rewards

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
        value=rewards,
    )
    return_log = tx.decode_logs(callee.OpenReturn)[0]

    result = pool_initialized_with_liquidity.positions(key)
    assert return_log.id == id
    assert return_log.size == position.size
    assert return_log.debt == position.debt1
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)

    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    balancee_sender = sender.balance  # ETH balance

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balancee_pool = pool_initialized_with_liquidity.balance  # ETH balance

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    return_log = tx.decode_logs(callee.OpenReturn)[0]

    amount0 = token0.balanceOf(pool_initialized_with_liquidity.address) - balance0_pool
    amount1 = token1.balanceOf(pool_initialized_with_liquidity.address) - balance1_pool

    # callee sends margin + fees in margin token
    assert amount0 == 0
    assert amount1 == margin + fees
    assert return_log.amount0 == 0
    assert return_log.amount1 == margin + fees

    balance0_sender -= amount0
    balance1_sender -= amount1
    assert token0.balanceOf(sender.address) == balance0_sender
    assert token1.balanceOf(sender.address) == balance1_sender

    # callee sends liquidation rewards in gas token
    liq_rewards = pool_initialized_with_liquidity.balance - balancee_pool
    assert liq_rewards == rewards
    balancee_sender -= liq_rewards + tx.gas_used * tx.gas_price
    assert sender.balance == balancee_sender


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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)

    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    balancee_sender = sender.balance  # ETH balance

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balancee_pool = pool_initialized_with_liquidity.balance  # ETH balance

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    return_log = tx.decode_logs(callee.OpenReturn)[0]

    amount0 = token0.balanceOf(pool_initialized_with_liquidity.address) - balance0_pool
    amount1 = token1.balanceOf(pool_initialized_with_liquidity.address) - balance1_pool

    # callee sends margin + fees in margin token
    assert amount0 == margin + fees
    assert amount1 == 0
    assert return_log.amount0 == margin + fees
    assert return_log.amount1 == 0

    balance0_sender -= amount0
    balance1_sender -= amount1
    assert token0.balanceOf(sender.address) == balance0_sender
    assert token1.balanceOf(sender.address) == balance1_sender

    # callee sends liquidation rewards in gas token
    liq_rewards = pool_initialized_with_liquidity.balance - balancee_pool
    assert liq_rewards == rewards
    balancee_sender -= liq_rewards + tx.gas_used * tx.gas_price
    assert sender.balance == balancee_sender


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

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
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
    assert pytest.approx(result.liquidity, rel=1e-15) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-15) == state.sqrtPriceX96
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

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
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

    assert pytest.approx(result.liquidity, rel=1e-15) == state.liquidity
    assert pytest.approx(result.sqrtPriceX96, rel=1e-15) == state.sqrtPriceX96
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    events = tx.decode_logs(callee.OpenCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == 0
    assert event.amount1Owed == margin + fees
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    events = tx.decode_logs(callee.OpenCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Owed == margin + fees
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    state = pool_initialized_with_liquidity.state()
    id = int(tx.decode_logs(callee.OpenReturn)[0].id)

    events = tx.decode_logs(pool_initialized_with_liquidity.Open)
    assert len(events) == 1
    event = events[0]

    assert event.sender.lower() == callee.address.lower()
    assert event.owner.lower() == alice.address.lower()
    assert int(event.id, 0) == id  # @dev ape returns as bytes for some reason
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )
    state = pool_initialized_with_liquidity.state()
    id = int(tx.decode_logs(callee.OpenReturn)[0].id)

    events = tx.decode_logs(pool_initialized_with_liquidity.Open)
    assert len(events) == 1
    event = events[0]

    assert event.sender.lower() == callee.address.lower()
    assert event.owner.lower() == alice.address.lower()
    assert int(event.id, 0) == id  # @dev ape returns as bytes for some reason
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.margin == margin


def test_pool_open__reverts_when_liquidity_delta_is_zero_with_zero_for_one(
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
    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    liquidity_delta = 0
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1
    margin = 0

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
        )


def test_pool_open__reverts_when_liquidity_delta_is_zero_with_one_for_zero(
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
    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    liquidity_delta = 0
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1
    margin = 0

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
        )


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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    liquidity_delta = state.liquidity - MINIMUM_LIQUIDITY
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

    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    liquidity_delta = state.liquidity - MINIMUM_LIQUIDITY
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

    with reverts(pool_initialized_with_liquidity.InvalidLiquidityDelta):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity,
        state.sqrtPriceX96,
        liquidity_delta,
        zero_for_one,
        maintenance,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next - 1

    with reverts(pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
        callee_below_min1.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

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

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    with reverts(pool_initialized_with_liquidity.Amount0LessThanMin):
        callee_below_min0.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    margin_min = position_lib.marginMinimum(position, maintenance)
    margin = margin_min - 1

    with reverts(pool_initialized_with_liquidity.MarginLessThanMin):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
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
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    liquidity_delta = state.liquidity * 5 // 100
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
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
        0,  # @dev irrelevant for this test
    )
    margin_min = position_lib.marginMinimum(position, maintenance)
    margin = margin_min - 1

    with reverts(pool_initialized_with_liquidity.MarginLessThanMin):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
        )


def test_pool_open__reverts_when_rewards_less_than_min_with_zero_for_one(
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

    with reverts(pool_initialized_with_liquidity.RewardsLessThanMin):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


def test_pool_open__reverts_when_rewards_less_than_min_with_one_for_zero(
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

    with reverts(pool_initialized_with_liquidity.RewardsLessThanMin):
        callee.open(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
        )


# TODO: test for extreme small (~0) and large (~liquidity) liquidity_delta values


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=500))
@given(
    liquidity_delta=st.integers(
        min_value=1, max_value=29942224366269116 - MINIMUM_LIQUIDITY
    ),  # max liquidity in init'd pool w liquidity
    zero_for_one=st.booleans(),
    margin=st.integers(min_value=0, max_value=2**128 - 1),
)
def test_pool_open__with_fuzz(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
    liquidity_delta,
    zero_for_one,
    margin,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**128 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**128 - 1 - balance1_sender, sender=sender)

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)  # 2**128-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**128-1
    balancee_sender = sender.balance  # in ETH

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balancee_pool = pool_initialized_with_liquidity.balance  # in ETH

    # set up fuzz test of open
    state = pool_initialized_with_liquidity.state()
    liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[
        -1
    ].base_fee  # comes in ~ 280 gwei given 10,000 gwei initial ape-config.yaml

    # go to max if liquidity delta > state.liquidity
    if liquidity_delta >= state.liquidity:
        liquidity_delta = state.liquidity - 1

    sqrt_price_limit_x96 = (
        MAX_SQRT_RATIO - 1 if not zero_for_one else MIN_SQRT_RATIO + 1
    )
    sqrt_price_x96_next_calculated = calc_sqrt_price_x96_next_open(
        state.liquidity,
        state.sqrtPriceX96,
        liquidity_delta,
        zero_for_one,
        maintenance,
    )
    if (
        sqrt_price_x96_next_calculated >= MAX_SQRT_RATIO - 1
        or sqrt_price_x96_next_calculated <= MIN_SQRT_RATIO + 1
    ):
        return

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextOpen(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    # oracle updates
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]

    # position assembly
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        state.tick,
        block_timestamp_next,
        tick_cumulative,
        oracle_tick_cumulative,
    )

    if position.size == 0 or position.debt0 == 0 or position.debt1 == 0:
        return

    fees = position_lib.fees(position.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    margin_min = position_lib.marginMinimum(position, maintenance)
    balance = balance0_sender if not zero_for_one else balance1_sender

    # adjust in case outside of range where test would pass
    if margin_min > 2**128 - 1 or margin_min == 0:
        return
    elif margin < margin_min:
        margin = margin_min
    elif margin + fees > balance:
        margin = balance - fees

    params = (
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
    )
    tx = callee.open(*params, sender=sender, value=rewards)
    return_log = tx.decode_logs(callee.OpenReturn)[0]

    id = return_log.id
    size = return_log.size
    debt = return_log.debt
    amount0_returned = return_log.amount0
    amount1_returned = return_log.amount1
    assert id == state.totalPositions

    key = get_position_key(alice.address, id)
    result_position = pool_initialized_with_liquidity.positions(key)

    assert size == result_position.size
    assert margin == result_position.margin
    assert debt == (result_position.debt0 if zero_for_one else result_position.debt1)

    result_fees = position_lib.fees(result_position.size, fee)
    assert amount0_returned == (
        0 if zero_for_one else result_position.margin + result_fees
    )
    assert amount1_returned == (
        result_position.margin + result_fees if zero_for_one else 0
    )

    # check pool state transition
    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(reserve0 + fees0, reserve1 + fees1)
    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next
    state.totalPositions += 1

    result_state = pool_initialized_with_liquidity.state()
    assert pytest.approx(result_state.liquidity, rel=1e-14) == state.liquidity
    assert pytest.approx(result_state.sqrtPriceX96, rel=1e-14) == state.sqrtPriceX96
    assert pytest.approx(result_state.tick, abs=1) == state.tick
    assert result_state.blockTimestamp == state.blockTimestamp
    assert result_state.tickCumulative == state.tickCumulative
    assert result_state.totalPositions == state.totalPositions

    liquidity_locked += liquidity_delta
    result_liquidity_locked = pool_initialized_with_liquidity.liquidityLocked()
    assert result_liquidity_locked == liquidity_locked

    # check position set
    state = result_state
    position.rewards = rewards
    position.margin = margin
    assert result_position == position

    # check balances
    amount0 = margin + fees if not zero_for_one else 0
    amount1 = 0 if not zero_for_one else margin + fees

    balance0_sender -= amount0
    balance1_sender -= amount1
    balancee_sender -= rewards + tx.gas_used * tx.gas_price

    balance0_pool += amount0
    balance1_pool += amount1
    balancee_pool += rewards

    result_balance0_sender = token0.balanceOf(sender.address)
    result_balance1_sender = token1.balanceOf(sender.address)
    result_balancee_sender = sender.balance

    result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    result_balancee_pool = pool_initialized_with_liquidity.balance

    assert result_balance0_sender == balance0_sender
    assert result_balance1_sender == balance1_sender
    assert result_balancee_sender == balancee_sender

    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool
    assert result_balancee_pool == balancee_pool

    # TODO: check protocol fees (add fuzz param)

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Open)
    assert len(events) == 1
    event = events[0]

    assert event.sender.lower() == callee.address.lower()
    assert event.owner.lower() == alice.address.lower()
    assert int(event.id, 0) == id  # @dev ape returns as bytes for some reason
    assert event.liquidityAfter == state.liquidity
    assert event.sqrtPriceX96After == state.sqrtPriceX96
    assert event.margin == margin

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

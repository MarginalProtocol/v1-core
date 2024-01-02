import pytest

from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import (
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    SECONDS_AGO,
    MINIMUM_SIZE,
    MINIMUM_LIQUIDITY,
)
from utils.utils import get_position_key, calc_sqrt_price_x96_next_open


@pytest.fixture
def oracle_next_obs(rando_univ3_observations):
    def next_obs(rel_tick_bps: int):
        obs_last = rando_univ3_observations[-1]
        obs_before = rando_univ3_observations[-2]
        tick = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])

        obs_timestamp = obs_last[0] + SECONDS_AGO
        obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick * rel_tick_bps) // 10000
        obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
        obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)
        return obs

    yield next_obs


def test_pool_open_then_liquidate_returns_liquidity__with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    mock_univ3_pool,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    chain,
    oracle_next_obs,
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

    sqrt_price_x96 = state.sqrtPriceX96
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
        state.tick,
        0,
        0,
        0,
    )

    margin_minimum = position_lib.marginMinimum(position, maintenance)
    margin = margin_minimum

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    # cache balances prior to check sender receives size from pool
    # for debt sent to pool from sender post open -> settle
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    balancee_sender = sender.balance

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balancee_alice = alice.balance

    id = state.totalPositions
    key = get_position_key(callee.address, id)
    tx_open = callee.open(
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

    fees = position_lib.fees(result.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    margin0 = 0 if zero_for_one else result.margin
    margin1 = result.margin if zero_for_one else 0

    # change the oracle price up 20% to make the position unsafe
    next_obs = oracle_next_obs(12000)
    mock_univ3_pool.pushObservation(*next_obs, sender=bob)

    # now liquidate and check state_after liquidity increases, sqrtPriceX96 decreases slightly
    # from original state
    tx_liquidate = pool_initialized_with_liquidity.liquidate(
        alice.address, callee.address, id, sender=alice
    )

    state_after = pool_initialized_with_liquidity.state()

    assert state_after.liquidity > state.liquidity
    assert (
        state_after.sqrtPriceX96 > state.sqrtPriceX96
    )  # liquidation overshoots original price

    # factor in margin + fees added to liquidity in pool
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        fees0 + margin0,
        fees1 + margin1,
    )

    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-9) == sqrt_price_x96_after
    assert pytest.approx(state_after.liquidity, rel=1e-9) == liquidity_after

    # check balances after open -> liquidate have margin in to pool with liq rewards to alice
    balance0_after_sender = token0.balanceOf(sender.address)
    balance1_after_sender = token1.balanceOf(sender.address)
    balancee_after_sender = sender.balance

    balance0_after_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_after_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balancee_after_alice = alice.balance

    amount0_to_sender = balance0_after_sender - balance0_sender
    amount1_to_sender = balance1_after_sender - balance1_sender
    amounte_to_sender = balancee_after_sender - balancee_sender

    amount0_to_pool = balance0_after_pool - balance0_pool
    amount1_to_pool = balance1_after_pool - balance1_pool

    amounte_to_alice = balancee_after_alice - balancee_alice

    assert amount0_to_sender == 0
    assert amount1_to_sender == -result.margin - fees
    assert amounte_to_sender == -result.rewards - tx_open.gas_used * tx_open.gas_price

    assert amount0_to_pool == 0
    assert amount1_to_pool == result.margin + fees

    assert (
        amounte_to_alice
        == result.rewards - tx_liquidate.gas_used * tx_liquidate.gas_price
    )


def test_pool_open_then_liquidate_returns_liquidity__with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    mock_univ3_pool,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    chain,
    oracle_next_obs,
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

    sqrt_price_x96 = state.sqrtPriceX96
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
        state.tick,
        0,
        0,
        0,
    )

    margin_minimum = position_lib.marginMinimum(position, maintenance)
    margin = margin_minimum

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    # cache balances prior to check sender receives size from pool
    # for debt sent to pool from sender post open -> settle
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    balancee_sender = sender.balance

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balancee_alice = alice.balance

    id = state.totalPositions
    key = get_position_key(callee.address, id)
    tx_open = callee.open(
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

    fees = position_lib.fees(result.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    margin0 = 0 if zero_for_one else result.margin
    margin1 = result.margin if zero_for_one else 0

    # change the oracle price lower 20% to make the position unsafe
    next_obs = oracle_next_obs(8000)
    mock_univ3_pool.pushObservation(*next_obs, sender=bob)

    # now liquidate and check state_after liquidity increases, sqrtPriceX96 decreases slightly
    # from original state
    tx_liquidate = pool_initialized_with_liquidity.liquidate(
        alice.address, callee.address, id, sender=alice
    )

    state_after = pool_initialized_with_liquidity.state()

    assert state_after.liquidity > state.liquidity
    assert (
        state_after.sqrtPriceX96 < state.sqrtPriceX96
    )  # liquidation overshoots original price

    # factor in margin + fees added to liquidity in pool
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        fees0 + margin0,
        fees1 + margin1,
    )
    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-9) == sqrt_price_x96_after
    assert pytest.approx(state_after.liquidity, rel=1e-9) == liquidity_after

    # check balances after open -> liquidate have margin in to pool with liq rewards to alice
    balance0_after_sender = token0.balanceOf(sender.address)
    balance1_after_sender = token1.balanceOf(sender.address)
    balancee_after_sender = sender.balance

    balance0_after_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_after_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balancee_after_alice = alice.balance

    amount0_to_sender = balance0_after_sender - balance0_sender
    amount1_to_sender = balance1_after_sender - balance1_sender
    amounte_to_sender = balancee_after_sender - balancee_sender

    amount0_to_pool = balance0_after_pool - balance0_pool
    amount1_to_pool = balance1_after_pool - balance1_pool

    amounte_to_alice = balancee_after_alice - balancee_alice

    assert amount0_to_sender == -result.margin - fees
    assert amount1_to_sender == 0
    assert amounte_to_sender == -result.rewards - tx_open.gas_used * tx_open.gas_price

    assert amount0_to_pool == result.margin + fees
    assert amount1_to_pool == 0

    assert (
        amounte_to_alice
        == result.rewards - tx_liquidate.gas_used * tx_liquidate.gas_price
    )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=1000))
@given(
    liquidity_delta=st.integers(
        min_value=MINIMUM_SIZE, max_value=29942224366269116 - MINIMUM_LIQUIDITY
    ),  # max liquidity in init'd pool w liquidity; rough min value of min size although actually larger for token decimals in this pool
    zero_for_one=st.booleans(),
)
def test_pool_open_then_liquidate_returns_liquidity__with_fuzz(
    pool_initialized_with_liquidity,
    callee,
    mock_univ3_pool,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    bob,
    token0,
    token1,
    chain,
    rando_univ3_observations,
    liquidity_delta,
    zero_for_one,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**128 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**128 - 1 - balance1_sender, sender=sender)

    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()
    assert state.totalPositions == 0

    premium = pool_initialized_with_liquidity.rewardPremium()
    base_fee = chain.blocks[-1].base_fee

    liquidity = state.liquidity
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1

    sqrt_price_x96 = state.sqrtPriceX96
    calc_sqrt_price_x96_next = calc_sqrt_price_x96_next_open(
        liquidity, sqrt_price_x96, liquidity_delta, zero_for_one, maintenance
    )
    if (
        calc_sqrt_price_x96_next <= MIN_SQRT_RATIO
        or calc_sqrt_price_x96_next >= MAX_SQRT_RATIO
    ):
        return

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
        state.tick,
        0,
        0,
        0,
    )
    if (
        position.size < MINIMUM_SIZE
        or position.debt0 < MINIMUM_SIZE
        or position.debt1 < MINIMUM_SIZE
        or position.insurance0 < MINIMUM_SIZE
        or position.insurance1 < MINIMUM_SIZE
    ):
        return

    margin_minimum = position_lib.marginMinimum(position, maintenance)
    margin = margin_minimum

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    # cache balances prior to check sender receives size from pool
    # for debt sent to pool from sender post open -> settle
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    balancee_sender = sender.balance

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balancee_alice = alice.balance

    id = state.totalPositions
    key = get_position_key(callee.address, id)
    tx_open = callee.open(
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

    fees = position_lib.fees(result.size, fee)
    fees0 = 0 if zero_for_one else fees
    fees1 = fees if zero_for_one else 0

    margin0 = 0 if zero_for_one else result.margin
    margin1 = result.margin if zero_for_one else 0

    # change the oracle price up/lower 20% to make the position unsafe
    # @dev needed to do out due to hypothesis with function fixtures
    obs_last = rando_univ3_observations[-1]
    obs_before = rando_univ3_observations[-2]
    tick = (obs_last[1] - obs_before[1]) // (obs_last[0] - obs_before[0])

    rel_tick_bps = 12000 if zero_for_one else 8000
    obs_timestamp = obs_last[0] + SECONDS_AGO
    obs_tick_cumulative = obs_last[1] + (SECONDS_AGO * tick * rel_tick_bps) // 10000
    obs_liquidity_cumulative = obs_last[2]  # @dev irrelevant for test
    obs = (obs_timestamp, obs_tick_cumulative, obs_liquidity_cumulative, True)

    mock_univ3_pool.pushObservation(*obs, sender=bob)

    # now liquidate and check state_after liquidity increases, sqrtPriceX96 decreases slightly
    # from original state
    tx_liquidate = pool_initialized_with_liquidity.liquidate(
        alice.address, callee.address, id, sender=alice
    )

    state_after = pool_initialized_with_liquidity.state()
    assert state_after.liquidity > state.liquidity

    if zero_for_one:
        assert (
            state_after.sqrtPriceX96 > state.sqrtPriceX96
        )  # liquidation overshoots original price
    else:
        assert (
            state_after.sqrtPriceX96 < state.sqrtPriceX96
        )  # liquidation overshoots original price

    # factor in margin + fees added to liquidity in pool
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        liquidity,
        sqrt_price_x96,
        fees0 + margin0,
        fees1 + margin1,
    )

    assert pytest.approx(state_after.sqrtPriceX96, rel=1e-9) == sqrt_price_x96_after
    assert pytest.approx(state_after.liquidity, rel=1e-9) == liquidity_after

    # check balances after open -> liquidate have margin in to pool with liq rewards to alice
    balance0_after_sender = token0.balanceOf(sender.address)
    balance1_after_sender = token1.balanceOf(sender.address)
    balancee_after_sender = sender.balance

    balance0_after_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_after_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balancee_after_alice = alice.balance

    amount0_to_sender = balance0_after_sender - balance0_sender
    amount1_to_sender = balance1_after_sender - balance1_sender
    amounte_to_sender = balancee_after_sender - balancee_sender

    amount0_to_pool = balance0_after_pool - balance0_pool
    amount1_to_pool = balance1_after_pool - balance1_pool

    amounte_to_alice = balancee_after_alice - balancee_alice

    assert amount0_to_sender == (0 if zero_for_one else -result.margin - fees)
    assert amount1_to_sender == (-result.margin - fees if zero_for_one else 0)
    assert amounte_to_sender == -result.rewards - tx_open.gas_used * tx_open.gas_price

    assert amount0_to_pool == (0 if zero_for_one else result.margin + fees)
    assert amount1_to_pool == (result.margin + fees if zero_for_one else 0)

    assert (
        amounte_to_alice
        == result.rewards - tx_liquidate.gas_used * tx_liquidate.gas_price
    )

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

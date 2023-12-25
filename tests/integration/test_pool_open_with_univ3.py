import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_pool_open_with_univ3__sets_position(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    position_lib,
    callee,
    alice,
    sender,
    chain,
):
    state = mrglv1_pool_initialized_with_liquidity.state()
    maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()

    premium = mrglv1_pool_initialized_with_liquidity.rewardPremium()

    # mine a few empty blocks to get base fee down a bit
    # base_fee set in ape-config.yaml set for local functional tests
    chain.mine(num_blocks=20)
    base_fee = chain.blocks[-1].base_fee

    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, state.sqrtPriceX96
    )
    amount = amount1 if zero_for_one else amount0

    size = int(
        amount
        * maintenance
        / (maintenance + MAINTENANCE_UNIT - liquidity_delta / state.liquidity)
    )  # @dev: this is an approximation
    margin = int(1.25 * size) * maintenance // MAINTENANCE_UNIT

    rewards = position_lib.liquidationRewards(
        base_fee,
        BASE_FEE_MIN,
        GAS_LIQUIDATE,
        premium,
    )

    tx = callee.open(
        mrglv1_pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
        value=rewards,
    )

    oracle_tick_cumulatives, _ = univ3_pool.observe([0])
    oracle_tick_cumulative = oracle_tick_cumulatives[0]
    state_tick_cumulative = (
        mrglv1_pool_initialized_with_liquidity.state().tickCumulative
    )
    tick_cumulative_delta = oracle_tick_cumulative - state_tick_cumulative

    id = int(tx.decode_logs(callee.OpenReturn)[0].id)
    key = get_position_key(alice.address, id)
    position = mrglv1_pool_initialized_with_liquidity.positions(key)

    assert position.tickCumulativeDelta == tick_cumulative_delta

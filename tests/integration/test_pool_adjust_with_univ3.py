import pytest

from utils.constants import (
    MIN_SQRT_RATIO,
    MAX_SQRT_RATIO,
    MAINTENANCE_UNIT,
    FUNDING_PERIOD,
    BASE_FEE_MIN,
    GAS_LIQUIDATE,
)
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def open_position(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    callee,
    sender,
    chain,
    position_lib,
):
    def open(zero_for_one):
        state = mrglv1_pool_initialized_with_liquidity.state()
        maintenance = mrglv1_pool_initialized_with_liquidity.maintenance()

        premium = mrglv1_pool_initialized_with_liquidity.rewardPremium()
        base_fee = chain.blocks[-1].base_fee

        liquidity_delta = (
            state.liquidity * 500 // 10000
        )  # 5% of pool reserves leveraged
        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

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
            callee.address,
            zero_for_one,
            liquidity_delta,
            sqrt_price_limit_x96,
            margin,
            sender=sender,
            value=rewards,
        )
        id = tx.decode_logs(callee.OpenReturn)[0].id
        return int(id)

    yield open


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
def test_pool_adjust_with_univ3__sets_position(
    mrglv1_pool_initialized_with_liquidity,
    univ3_pool,
    zero_for_one,
    callee,
    alice,
    sender,
    chain,
    position_lib,
    liquidity_math_lib,
    open_position,
):
    position_id = open_position(zero_for_one)

    key = get_position_key(callee.address, position_id)
    position = mrglv1_pool_initialized_with_liquidity.positions(key)

    dt = FUNDING_PERIOD // 7
    chain.mine(deltatime=dt)

    margin_delta = position.margin  # 2xing margin
    callee.adjust(
        mrglv1_pool_initialized_with_liquidity.address,
        alice.address,
        position_id,
        margin_delta,
        sender=sender,
    )

    # added margin
    # @dev position *won't* sync for funding to avoid short circuit rounding issues
    position.margin += margin_delta
    assert mrglv1_pool_initialized_with_liquidity.positions(key) == position

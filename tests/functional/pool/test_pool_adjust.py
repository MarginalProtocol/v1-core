import pytest

# TODO: from ape import reverts
from eth_abi import encode

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import get_position_key


@pytest.fixture
def zero_for_one_position_id(
    pool_initialized_with_liquidity, callee, sender, token0, token1
):
    state = pool_initialized_with_liquidity.state()
    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        sender.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return int(tx.return_value)


@pytest.fixture
def one_for_zero_position_id(
    pool_initialized_with_liquidity, callee, sender, token0, token1
):
    state = pool_initialized_with_liquidity.state()
    liquidity_delta = state.liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    tx = callee.open(
        pool_initialized_with_liquidity.address,
        sender.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return int(tx.return_value)


def test_pool_adjust__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
):
    key = get_position_key(sender.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_in = 2 * position.margin
    margin_out = position.margin
    data = encode(["address"], [sender.address])

    pool_initialized_with_liquidity.adjust(
        callee.address,
        zero_for_one_position_id,
        margin_in,
        margin_out,
        data,
        sender=sender,
    )
    position.margin += margin_in - margin_out
    assert pool_initialized_with_liquidity.positions(key) == position


def test_pool_adjust__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
):
    key = get_position_key(sender.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)

    margin_in = 2 * position.margin
    margin_out = position.margin
    data = encode(["address"], [sender.address])

    pool_initialized_with_liquidity.adjust(
        callee.address,
        one_for_zero_position_id,
        margin_in,
        margin_out,
        data,
        sender=sender,
    )
    position.margin += margin_in - margin_out
    assert pool_initialized_with_liquidity.positions(key) == position


# TODO: test when not position owner


# TODO:
@pytest.mark.fuzzing
def test_pool_adjust__with_fuzz():
    pass

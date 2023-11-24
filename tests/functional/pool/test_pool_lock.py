import pytest

from ape import reverts
from hexbytes import HexBytes
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import calc_amounts_from_liquidity_sqrt_price_x96, get_position_key


@pytest.fixture
def zero_for_one_position_id(
    pool_initialized_with_liquidity,
    callee_for_reentrancy_with_open,
    sender,
    token0,
    token1,
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

    tx = callee_for_reentrancy_with_open.open(
        pool_initialized_with_liquidity.address,
        callee_for_reentrancy_with_open.address,
        zero_for_one,
        liquidity_delta,
        sqrt_price_limit_x96,
        margin,
        sender=sender,
    )
    id = tx.decode_logs(pool_initialized_with_liquidity.Open)[0].id
    return int(id)


@pytest.fixture
def open_reentrancy_calldata(pool_initialized_with_liquidity, alice, chain):
    ecosystem = chain.provider.network.ecosystem
    args = (alice.address, True, 0, MIN_SQRT_RATIO + 1, 0, HexBytes(""))
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.open.abis[0],
        *args
    ).data


@pytest.fixture
def adjust_reentrancy_calldata(pool_initialized_with_liquidity, alice, chain):
    ecosystem = chain.provider.network.ecosystem
    args = (alice.address, 0, 0, HexBytes(""))
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.adjust.abis[0],
        *args
    ).data


@pytest.fixture
def settle_reentrancy_calldata(pool_initialized_with_liquidity, alice, chain):
    ecosystem = chain.provider.network.ecosystem
    args = (alice.address, 0, HexBytes(""))
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.settle.abis[0],
        *args
    ).data


@pytest.fixture
def liquidate_reentrancy_calldata(pool_initialized_with_liquidity, alice, chain):
    ecosystem = chain.provider.network.ecosystem
    args = (
        alice.address,
        alice.address,
        0,
    )
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.liquidate.abis[0],
        *args
    ).data


@pytest.fixture
def swap_reentrancy_calldata(pool_initialized_with_liquidity, alice, chain):
    ecosystem = chain.provider.network.ecosystem
    args = (alice.address, True, 0, MIN_SQRT_RATIO + 1, HexBytes(""))
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.swap.abis[0],
        *args
    ).data


@pytest.fixture
def mint_reentrancy_calldata(
    pool_initialized_with_liquidity, callee_for_reentrancy, alice, chain
):
    ecosystem = chain.provider.network.ecosystem
    args = (callee_for_reentrancy.address, 0, HexBytes(""))
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.mint.abis[0],
        *args
    ).data


@pytest.fixture
def burn_reentrancy_calldata(pool_initialized_with_liquidity, alice, chain):
    ecosystem = chain.provider.network.ecosystem
    args = (
        alice.address,
        0,
    )
    return ecosystem.encode_transaction(
        pool_initialized_with_liquidity.address,
        pool_initialized_with_liquidity.burn.abis[0],
        *args
    ).data


@pytest.fixture
def calldatas_for_reentrancy(
    open_reentrancy_calldata,
    adjust_reentrancy_calldata,
    settle_reentrancy_calldata,
    liquidate_reentrancy_calldata,
    swap_reentrancy_calldata,
    mint_reentrancy_calldata,
    burn_reentrancy_calldata,
):
    return [
        open_reentrancy_calldata,
        adjust_reentrancy_calldata,
        settle_reentrancy_calldata,
        liquidate_reentrancy_calldata,
        swap_reentrancy_calldata,
        mint_reentrancy_calldata,
        burn_reentrancy_calldata,
    ]


def test_pool_lock__reverts_when_reenter_on_mint_callback(
    pool_initialized_with_liquidity,
    sender,
    alice,
    callee_for_reentrancy,
    calldatas_for_reentrancy,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 10 // 10000  # 0.1% of spot reserves

    for calldata in calldatas_for_reentrancy:
        with reverts("Locked() returned"):
            callee_for_reentrancy.mint(
                pool_initialized_with_liquidity.address,
                alice.address,
                liquidity_delta,
                calldata,
                sender=sender,
            )


def test_pool_lock__reverts_when_reenter_on_open_callback(
    pool_initialized_with_liquidity,
    sender,
    alice,
    callee_for_reentrancy,
    calldatas_for_reentrancy,
    token0,
    token1,
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

    for calldata in calldatas_for_reentrancy:
        with reverts("Locked() returned"):
            callee_for_reentrancy.open(
                pool_initialized_with_liquidity.address,
                alice.address,
                zero_for_one,
                liquidity_delta,
                sqrt_price_limit_x96,
                margin,
                calldata,
                sender=sender,
            )


def test_pool_lock__reverts_when_reenter_on_adjust_callback(
    pool_initialized_with_liquidity,
    sender,
    alice,
    callee_for_reentrancy_with_open,
    calldatas_for_reentrancy,
    token0,
    token1,
    zero_for_one_position_id,
):
    id = zero_for_one_position_id

    key = get_position_key(callee_for_reentrancy_with_open.address, id)
    position = pool_initialized_with_liquidity.positions(key)
    margin_delta = position.margin

    for calldata in calldatas_for_reentrancy:
        with reverts("Locked() returned"):
            callee_for_reentrancy_with_open.adjust(
                pool_initialized_with_liquidity.address,
                alice.address,
                id,
                margin_delta,
                calldata,
                sender=sender,
            )


def test_pool_lock__reverts_when_reenter_on_settle_callback(
    pool_initialized_with_liquidity,
    sender,
    alice,
    callee_for_reentrancy_with_open,
    calldatas_for_reentrancy,
    token0,
    token1,
    zero_for_one_position_id,
):
    id = zero_for_one_position_id
    for calldata in calldatas_for_reentrancy:
        with reverts("Locked() returned"):
            callee_for_reentrancy_with_open.settle(
                pool_initialized_with_liquidity.address,
                alice.address,
                id,
                calldata,
                sender=sender,
            )


def test_pool_lock__reverts_when_reenter_on_swap_callback(
    pool_initialized_with_liquidity,
    callee_for_reentrancy,
    calldatas_for_reentrancy,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve0 // 100  # 1% of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    for calldata in calldatas_for_reentrancy:
        with reverts("Locked() returned"):
            callee_for_reentrancy.swap(
                pool_initialized_with_liquidity.address,
                alice.address,
                zero_for_one,
                amount_specified,
                sqrt_price_limit_x96,
                calldata,
                sender=sender,
            )

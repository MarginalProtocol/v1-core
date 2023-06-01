import pytest

from eth_abi import encode
from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MAINTENANCE_UNIT
from utils.utils import get_position_key


@pytest.fixture(scope="module")
def sender(accounts):
    return accounts[3]


@pytest.fixture(scope="module")
def spot_reserve0(pool, token_a, token_b):
    x = int(125.04e12)  # e.g. USDC reserves on spot
    y = int(71.70e21)  # e.g. WETH reserves on spot
    return x if pool.token0() == token_a.address else y


@pytest.fixture(scope="module")
def spot_reserve1(pool, token_a, token_b):
    x = int(125.04e12)  # e.g. USDC reserves on spot
    y = int(71.70e21)  # e.g. WETH reserves on spot
    return y if pool.token1() == token_b.address else x


@pytest.fixture(scope="module")
def spot_liquidity(spot_reserve0, spot_reserve1):
    return int(sqrt(spot_reserve0 * spot_reserve1))


@pytest.fixture(scope="module")
def sqrt_price_x96_initial(spot_reserve0, spot_reserve1):
    sqrt_price = int(sqrt(spot_reserve1 / spot_reserve0))
    return sqrt_price << 96


@pytest.fixture(scope="module")
def pool_initialized(pool, sender, sqrt_price_x96_initial):
    pool.initialize(sqrt_price_x96_initial, sender=sender)
    return pool


@pytest.fixture(scope="module")
def token0(pool_initialized, token_a, token_b, sender, callee, spot_reserve0):
    token0 = token_a if pool_initialized.token0() == token_a.address else token_b
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool_initialized, token_a, token_b, sender, callee, spot_reserve1):
    token1 = token_b if pool_initialized.token1() == token_b.address else token_a
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.mint(sender.address, spot_reserve1, sender=sender)
    return token1


@pytest.fixture(scope="module")
def pool_initialized_with_liquidity(
    pool_initialized, callee, token0, token1, sender, spot_liquidity
):
    liquidity_delta = spot_liquidity * 100 // 10000  # 1% of spot reserves
    callee.mint(
        pool_initialized.address, sender.address, liquidity_delta, sender=sender
    )
    pool_initialized.approve(pool_initialized.address, 2**256 - 1, sender=sender)
    return pool_initialized


@pytest.fixture(scope="module")
def callee_below_min0(project, accounts, token0, token1, sender):
    callee_below = project.TestMarginalV1PoolBelowMin0Callee.deploy(sender=accounts[0])
    token0.approve(callee_below.address, 2**256 - 1, sender=sender)
    token1.approve(callee_below.address, 2**256 - 1, sender=sender)
    return callee_below


@pytest.fixture(scope="module")
def callee_below_min1(project, accounts, token0, token1, sender):
    callee_below = project.TestMarginalV1PoolBelowMin1Callee.deploy(sender=accounts[1])
    token0.approve(callee_below.address, 2**256 - 1, sender=sender)
    token1.approve(callee_below.address, 2**256 - 1, sender=sender)
    return callee_below


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def oracle_sqrt_price_initial_x96(
    pool_initialized_with_liquidity, mock_univ3_pool, oracle_lib
):
    seconds_ago = pool_initialized_with_liquidity.secondsAgo()
    oracle_tick_cumulatives, _ = mock_univ3_pool.observe([seconds_ago, 0])
    sqrt_price_x96 = oracle_lib.oracleSqrtPriceX96(
        oracle_tick_cumulatives[0],
        oracle_tick_cumulatives[1],
        seconds_ago,
    )
    return sqrt_price_x96


@pytest.fixture(scope="module")
def zero_for_one_position_adjusted_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    zero_for_one_position_id,
    oracle_sqrt_price_initial_x96,
):
    key = get_position_key(sender.address, zero_for_one_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    data = encode(["address"], [sender.address])

    maintenance = pool_initialized_with_liquidity.maintenance()
    debt0_adjusted = (
        position.debt0 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    collateral1_req = int(
        debt0_adjusted * (oracle_sqrt_price_initial_x96**2) // (1 << 192)
    )
    margin1 = collateral1_req - position.size
    margin1 *= 1.20  # go 20% larger than reqs to ensure safe

    margin_out = position.margin
    margin_in = int(margin1)

    pool_initialized_with_liquidity.adjust(
        callee.address,
        zero_for_one_position_id,
        margin_in,
        margin_out,
        data,
        sender=sender,
    )
    return zero_for_one_position_id


@pytest.fixture(scope="module")
def one_for_zero_position_adjusted_id(
    pool_initialized_with_liquidity,
    callee,
    sender,
    token0,
    token1,
    one_for_zero_position_id,
    oracle_sqrt_price_initial_x96,
):
    key = get_position_key(sender.address, one_for_zero_position_id)
    position = pool_initialized_with_liquidity.positions(key)
    data = encode(["address"], [sender.address])

    maintenance = pool_initialized_with_liquidity.maintenance()
    debt1_adjusted = (
        position.debt1 * (MAINTENANCE_UNIT + maintenance) // MAINTENANCE_UNIT
    )
    collateral0_req = int(
        debt1_adjusted * (1 << 192) // (oracle_sqrt_price_initial_x96**2)
    )
    margin0 = collateral0_req - position.size
    margin0 *= 1.20  # go 20% larger than reqs to ensure safe

    margin_out = position.margin
    margin_in = int(margin0)

    pool_initialized_with_liquidity.adjust(
        callee.address,
        one_for_zero_position_id,
        margin_in,
        margin_out,
        data,
        sender=sender,
    )
    return one_for_zero_position_id

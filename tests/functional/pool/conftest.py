import pytest

from math import sqrt
from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO


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
def sqrt_price_x96_initial(spot_reserve0, spot_reserve1):
    sqrt_price = int(sqrt(spot_reserve1 / spot_reserve0))
    return sqrt_price << 96


@pytest.fixture(scope="module")
def pool_initialized(pool, deployer, sqrt_price_x96_initial):
    pool.initialize(sqrt_price_x96_initial, sender=deployer)
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
    pool_initialized, callee, token0, token1, sender, spot_reserve0, spot_reserve1
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 100 // 10000  # 1% of spot reserves
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

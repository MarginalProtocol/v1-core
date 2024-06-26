import pytest


@pytest.fixture(scope="session")
def admin(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def alice(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def bob(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def sender(accounts):
    yield accounts[3]


@pytest.fixture(scope="session")
def rando_token_a_address():
    return "0x000000000000000000000000000000000000000A"


@pytest.fixture(scope="session")
def rando_token_b_address():
    return "0x000000000000000000000000000000000000000b"


@pytest.fixture(scope="session")
def create_token(project, accounts):
    def create_token(name, decimals=18):
        return project.Token.deploy(name, decimals, sender=accounts[0])

    yield create_token


@pytest.fixture(scope="session")
def token_a(project, accounts, create_token):
    return create_token("A", decimals=6)


@pytest.fixture(scope="session")
def token_b(project, accounts, create_token):
    return create_token("B", decimals=18)


@pytest.fixture(scope="session")
def rando_univ3_fee():
    return 500


@pytest.fixture(scope="session")
def univ3_factory_address():
    # https://docs.uniswap.org/contracts/v3/reference/deployments
    return "0x1F98431c8aD98523631AE4a59f267346ea31F984"


@pytest.fixture(scope="session")
def rando_univ3_observations():
    # @dev order matters given mock
    # @dev tick average price approx same as sqrt_price_initial_x96 in pool conftest
    return [
        (1684675403, 13002641612327, 151666952020109821882336874706, True),
        (1684718603, 13011354231527, 151666952020109821882336874706, True),
        (1684761803, 13020066850727, 151666987847742632430844074643, True),
    ]


@pytest.fixture(scope="session")
def rando_univ3_pool(
    project,
    accounts,
    rando_token_a_address,
    rando_token_b_address,
    rando_univ3_fee,
    rando_univ3_observations,
):
    univ3_pool = project.MockUniswapV3Pool.deploy(
        rando_token_a_address,
        rando_token_b_address,
        rando_univ3_fee,
        sender=accounts[0],
    )

    for obs in rando_univ3_observations:
        univ3_pool.pushObservation(*obs, sender=accounts[0])

    slot0 = (1815798575707834854825150601403158, 200804, 287, 7200, 7200, 0, True)
    univ3_pool.setSlot0(slot0, sender=accounts[0])

    return univ3_pool


@pytest.fixture(scope="session")
def mock_univ3_pool(
    project,
    accounts,
    token_a,
    token_b,
    rando_univ3_fee,
    rando_univ3_observations,
):
    univ3_pool = project.MockUniswapV3Pool.deploy(
        token_a,
        token_b,
        rando_univ3_fee,
        sender=accounts[0],
    )

    for obs in rando_univ3_observations:
        univ3_pool.pushObservation(*obs, sender=accounts[0])

    slot0 = (1815798575707834854825150601403158, 200804, 287, 7200, 7200, 0, True)
    univ3_pool.setSlot0(slot0, sender=accounts[0])

    return univ3_pool


@pytest.fixture(scope="session")
def mock_univ3_factory(
    project,
    accounts,
    rando_univ3_pool,
    mock_univ3_pool,
):
    univ3_factory = project.MockUniswapV3Factory.deploy(sender=accounts[0])
    univ3_factory.setPool(
        rando_univ3_pool.token0(),
        rando_univ3_pool.token1(),
        rando_univ3_pool.fee(),
        rando_univ3_pool.address,
        sender=accounts[0],
    )  # A/B 0.3% rando spot pool deployed
    univ3_factory.setPool(
        mock_univ3_pool.token0(),
        mock_univ3_pool.token1(),
        mock_univ3_pool.fee(),
        mock_univ3_pool.address,
        sender=accounts[0],
    )  # A/B 0.3% mock spot pool deployed
    return univ3_factory


@pytest.fixture(scope="session")
def factory(
    project,
    accounts,
    univ3_factory_address,
    mock_univ3_factory,
):
    deployer = project.MarginalV1PoolDeployer.deploy(sender=accounts[0])

    deployer_address = deployer.address
    oracle_factory = mock_univ3_factory.address
    obs_cardinality_min = 7200
    return project.MarginalV1Factory.deploy(
        deployer_address, oracle_factory, obs_cardinality_min, sender=accounts[0]
    )


@pytest.fixture(scope="session")
def create_pool(project, accounts, factory):
    def create_pool(token_a, token_b, maintenance, univ3_fee):
        tx = factory.createPool(
            token_a, token_b, maintenance, univ3_fee, sender=accounts[0]
        )
        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        return project.MarginalV1Pool.at(pool_address)

    yield create_pool


# TODO: maintenance parametrization
@pytest.fixture(scope="session")
def pool(project, accounts, mock_univ3_pool, create_pool):
    maintenance = 250000
    return create_pool(
        mock_univ3_pool.token0(),
        mock_univ3_pool.token1(),
        maintenance,
        mock_univ3_pool.fee(),
    )


@pytest.fixture(scope="session")
def another_pool(project, accounts, mock_univ3_pool, create_pool):
    maintenance = 500000
    return create_pool(
        mock_univ3_pool.token0(),
        mock_univ3_pool.token1(),
        maintenance,
        mock_univ3_pool.fee(),
    )


@pytest.fixture(scope="session")
def callee(project, accounts):
    return project.TestMarginalV1PoolCallee.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def sqrt_price_math_lib(project, accounts):
    return project.MockSqrtPriceMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def liquidity_math_lib(project, accounts):
    return project.MockLiquidityMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def oracle_lib(project, accounts):
    return project.MockOracleLibrary.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def position_lib(project, accounts):
    return project.MockPosition.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def swap_math_lib(project, accounts):
    return project.MockSwapMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def tick_math_lib(project, accounts):
    return project.MockTickMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def transfer_helper_lib(project, accounts):
    return project.MockTransferHelper.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def fixed_point_64_lib(project, accounts):
    return project.MockFixedPoint64.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def fixed_point_96_lib(project, accounts):
    return project.MockFixedPoint96.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def fixed_point_128_lib(project, accounts):
    return project.MockFixedPoint128.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def fixed_point_192_lib(project, accounts):
    return project.MockFixedPoint192.deploy(sender=accounts[0])

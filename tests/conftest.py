import pytest


@pytest.fixture(scope="session")
def deployer(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def alice(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def bob(accounts):
    yield accounts[2]


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
def rando_univ3_pool(
    project, accounts, rando_token_a_address, rando_token_b_address, rando_univ3_fee
):
    univ3_pool = project.MockUniswapV3Pool.deploy(
        rando_token_a_address,
        rando_token_b_address,
        rando_univ3_fee,
        sender=accounts[0],
    )
    univ3_pool.pushObservation(
        1684758335,
        12871216193543,
        151666952020109821882336874706,
        True,
        sender=accounts[0],
    )
    univ3_pool.pushObservation(
        1684761803,
        12871914275939,
        151666987847742632430844074643,
        True,
        sender=accounts[0],
    )
    return univ3_pool


@pytest.fixture(scope="session")
def mock_univ3_pool(project, accounts, token_a, token_b, rando_univ3_fee):
    univ3_pool = project.MockUniswapV3Pool.deploy(
        token_a,
        token_b,
        rando_univ3_fee,
        sender=accounts[0],
    )
    univ3_pool.pushObservation(
        1684758335,
        12871216193543,
        151666952020109821882336874706,
        True,
        sender=accounts[0],
    )
    univ3_pool.pushObservation(
        1684761803,
        12871914275939,
        151666987847742632430844074643,
        True,
        sender=accounts[0],
    )
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
def factory(project, networks, accounts, univ3_factory_address, mock_univ3_factory):
    oracle_factory = (
        univ3_factory_address
        if networks.network.name == "mainnet-fork"
        else mock_univ3_factory.address
    )  # TODO: fix
    return project.MarginalV1Factory.deploy(oracle_factory, sender=accounts[0])


@pytest.fixture(scope="session")
def create_pool(project, accounts, factory):
    def create_pool(token_a, token_b, maintenance, univ3_fee):
        tx = factory.createPool(
            token_a, token_b, maintenance, univ3_fee, sender=accounts[0]
        )
        pool_address = tx.return_value
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
def callee(project, accounts):
    return project.TestMarginalV1PoolCallee.deploy(sender=accounts[0])

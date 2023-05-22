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
def rando_univ3_fee():
    return 500


@pytest.fixture(scope="session")
def univ3_factory_address():
    # https://docs.uniswap.org/contracts/v3/reference/deployments
    return "0x1F98431c8aD98523631AE4a59f267346ea31F984"


@pytest.fixture(scope="session")
def mock_univ3_pool(
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
def mock_univ3_factory(
    project,
    accounts,
    rando_token_a_address,
    rando_token_b_address,
    rando_univ3_fee,
    mock_univ3_pool,
):
    univ3_factory = project.MockUniswapV3Factory.deploy(sender=accounts[0])
    univ3_factory.setPool(
        rando_token_a_address,
        rando_token_b_address,
        rando_univ3_fee,
        mock_univ3_pool.address,
        sender=accounts[0],
    )  # A/B 0.3% spot pool deployed
    return univ3_factory


@pytest.fixture(scope="session")
def factory(project, networks, accounts, univ3_factory_address, mock_univ3_factory):
    oracle_factory = (
        univ3_factory_address
        if networks.network.name == "mainnet-fork"
        else mock_univ3_factory.address
    )
    return project.MarginalV1Factory.deploy(oracle_factory, sender=accounts[0])


@pytest.fixture(scope="session")
def create_pool(project, accounts, factory):
    def create_pool(token_a, token_b, maintenance, univ3_fee):
        tx = factory.createPool(token_a, token_b, maintenance, univ3_fee)
        pool_address = tx.return_value
        return project.MarginalV1Pool.at(pool_address)

    yield create_pool


@pytest.fixture(scope="session")
def create_token(project, accounts):
    def create_token(name, decimals=18):
        return project.Token.deploy(name, decimals, sender=accounts[0])

    yield create_token

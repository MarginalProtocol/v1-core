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
def factory(project, accounts):
    return project.MarginalV1Factory.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def create_pool(project, accounts, factory):
    def create_pool(token_a, token_b, maintenance):
        tx = factory.createPool(token_a, token_b, maintenance)
        pool_address = tx.return_value
        return project.MarginalV1Pool.at(pool_address)

    yield create_pool


@pytest.fixture(scope="session")
def create_token(project, accounts):
    def create_token(name, decimals=18):
        return project.Token.deploy(name, decimals, sender=accounts[0])

    yield create_token

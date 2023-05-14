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

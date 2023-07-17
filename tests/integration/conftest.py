import pytest

from ape import Contract


@pytest.fixture(scope="module")
def assert_mainnet_fork(networks):
    assert (
        networks.active_provider.network.name == "mainnet-fork"
    ), "network not set to mainnet-fork"


@pytest.fixture(scope="module")
def WETH9(assert_mainnet_fork):
    return Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


@pytest.fixture(scope="module")
def USDT(assert_mainnet_fork):
    return Contract("0xdAC17F958D2ee523a2206206994597C13D831ec7")


@pytest.fixture(scope="module")
def univ3_factory(assert_mainnet_fork, univ3_factory_address):
    return Contract(univ3_factory_address)


@pytest.fixture(scope="module")
def univ3_pool(assert_mainnet_fork):
    return Contract("0x11b815efB8f581194ae79006d24E0d814B7697F6")

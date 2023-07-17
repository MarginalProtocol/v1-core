import pytest


@pytest.fixture(scope="module")
def assert_mainnet_fork(networks):
    assert (
        networks.active_provider.network.name == "mainnet-fork"
    ), "network not set to mainnet-fork"


@pytest.fixture(scope="module")
def WETH9(assert_mainnet_fork, Contract):
    return Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


@pytest.fixture(scope="module")
def USDC(assert_mainnet_fork, Contract):
    return Contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")


@pytest.fixture(scope="module")
def univ3_factory(assert_mainnet_fork, univ3_factory_address, Contract):
    return Contract(univ3_factory_address)


@pytest.fixture(scope="module")
def univ3_pool(assert_mainnet_fork, Contract):
    return Contract("0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8")


@pytest.fixture(scope="module")
def mrglv1_factory(project, accounts, univ3_factory):
    deployer = project.MarginalV1PoolDeployer.deploy(sender=accounts[0])
    obs_cardinality_min = (
        150  # @dev: too low for actual deployment, but needed to accomodate all tests
    )
    return project.MarginalV1Factory.deploy(
        deployer.address, univ3_factory.address, obs_cardinality_min, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def create_mrglv1_pool(project, accounts, mrglv1_factory, univ3_pool):
    def create_pool(token_a, token_b, maintenance, univ3_fee):
        tx = mrglv1_factory.createPool(
            token_a, token_b, maintenance, univ3_fee, sender=accounts[0]
        )
        pool_address = tx.return_value
        return project.MarginalV1Pool.at(pool_address)

    yield create_pool


@pytest.fixture(scope="module")
def mrglv1_pool(create_mrglv1_pool, univ3_pool):
    maintenance = 250000
    return create_mrglv1_pool(
        univ3_pool.token0(), univ3_pool.token1(), maintenance, univ3_pool.fee()
    )

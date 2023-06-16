import pytest

from ape import project, reverts
from ape.utils import ZERO_ADDRESS


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__deploys_pool_contract(
    project,
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        maintenance,
        rando_univ3_fee,
        sender=alice,
    )
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.factory() == factory.address
    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address
    assert pool.maintenance() == maintenance
    assert pool.fee() == 1000
    assert pool.reward() == 50000
    assert pool.secondsAgo() == 43200  # 12 hr TWAP for oracle price
    assert pool.fundingPeriod() == 604800  # 7 day funding period

    # TODO: abstract with ape-yaml.config somehow?
    univ3_factory_address = factory.uniswapV3Factory()
    univ3_factory = project.dependencies["uniswap-v3-core"]["0.8"].UniswapV3Factory.at(
        univ3_factory_address
    )
    assert pool.oracle() == univ3_factory.getPool(
        pool.token0(), pool.token1(), rando_univ3_fee
    )


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__stores_pool_address(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        maintenance,
        rando_univ3_fee,
        sender=alice,
    )
    pool_address = tx.return_value
    assert (
        factory.getPool(rando_token_a_address, rando_token_b_address, maintenance)
        == pool_address
    )
    assert (
        factory.getPool(rando_token_b_address, rando_token_a_address, maintenance)
        == pool_address
    )


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__orders_tokens(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    tx = factory.createPool(
        rando_token_b_address,
        rando_token_a_address,
        maintenance,
        rando_univ3_fee,
        sender=alice,
    )
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__emits_pool_created(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        maintenance,
        rando_univ3_fee,
        sender=alice,
    )
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    assert event.token0 == rando_token_a_address
    assert event.token1 == rando_token_b_address
    assert event.maintenance == maintenance
    assert event.pool == tx.return_value


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__deletes_params(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    _ = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        maintenance,
        rando_univ3_fee,
        sender=alice,
    )
    pool_deployer = project.MarginalV1PoolDeployer.at(factory.marginalV1Deployer())

    params = pool_deployer.params()
    assert params.factory == ZERO_ADDRESS
    assert params.token0 == ZERO_ADDRESS
    assert params.token1 == ZERO_ADDRESS
    assert params.maintenance == 0
    assert params.oracle == ZERO_ADDRESS


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_same_token(
    factory, alice, rando_token_a_address, maintenance, rando_univ3_fee
):
    with reverts(factory.InvalidTokens):
        factory.createPool(
            rando_token_a_address,
            rando_token_a_address,
            maintenance,
            rando_univ3_fee,
            sender=alice,
        )


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_token_is_zero_address(
    factory, alice, rando_token_a_address, maintenance, rando_univ3_fee
):
    with reverts(factory.InvalidTokens):
        factory.createPool(
            ZERO_ADDRESS,
            rando_token_a_address,
            maintenance,
            rando_univ3_fee,
            sender=alice,
        )

    with reverts(factory.InvalidTokens):
        factory.createPool(
            rando_token_a_address,
            ZERO_ADDRESS,
            maintenance,
            rando_univ3_fee,
            sender=alice,
        )


def test_create_pool__reverts_when_invalid_maintenance(
    factory, alice, rando_token_a_address, rando_token_b_address, rando_univ3_fee
):
    with reverts(factory.InvalidMaintenance):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            1000,
            rando_univ3_fee,
            sender=alice,
        )


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_invalid_oracle(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    with reverts(factory.InvalidOracle):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            maintenance,
            10,  # uni pool with 1 bps fee doesn't exist in mock
            sender=alice,
        )


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_observation_cardinality_less_than_min(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
    rando_univ3_pool,
):
    # update slot0 on uni pool
    slot0 = rando_univ3_pool.slot0()
    obs_cardinality_min = factory.observationCardinalityMinimum()
    slot0.observationCardinality = obs_cardinality_min - 1
    slot0.observationCardinalityNext = obs_cardinality_min - 1
    rando_univ3_pool.setSlot0(slot0, sender=alice)

    with reverts(factory.InvalidObservationCardinality):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            maintenance,
            rando_univ3_fee,
            sender=alice,
        )

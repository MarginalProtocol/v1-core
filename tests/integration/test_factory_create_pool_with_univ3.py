import pytest

from ape import project, reverts
from utils.constants import SECONDS_AGO


@pytest.mark.integration
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_factory_create_pool_with_univ3__deploys_pool_contract(
    mrglv1_factory,
    maintenance,
    alice,
    univ3_pool,
):
    token0 = univ3_pool.token0()
    token1 = univ3_pool.token1()
    univ3_fee = univ3_pool.fee()
    tx = mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)
    pool_address = tx.decode_logs(mrglv1_factory.PoolCreated)[0].pool
    pool = project.MarginalV1Pool.at(pool_address)

    assert pool.factory() == mrglv1_factory.address
    assert pool.oracle() == univ3_pool.address
    assert (
        mrglv1_factory.getPool(token0, token1, maintenance, univ3_pool.address)
        == pool.address
    )


@pytest.mark.integration
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_factory_create_pool_with_univ3__reverts_when_invalid_oracle(
    mrglv1_factory,
    maintenance,
    alice,
    univ3_pool,
):
    token0 = univ3_pool.token0()
    token1 = univ3_pool.token1()
    univ3_fee = 10

    with reverts(mrglv1_factory.InvalidOracle):
        mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)


@pytest.mark.integration
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_factory_create_pool_with_univ3__reverts_when_observation_cardinality_less_than_min(
    mrglv1_factory,
    maintenance,
    alice,
    Contract,
):
    univ3_ldoweth30bps_pool = Contract("0xa3f558aebAecAf0e11cA4b2199cC5Ed341edfd74")
    slot0 = univ3_ldoweth30bps_pool.slot0()
    obs_cardinality_min = mrglv1_factory.observationCardinalityMinimum()
    assert slot0.observationCardinality < obs_cardinality_min

    token0 = univ3_ldoweth30bps_pool.token0()
    token1 = univ3_ldoweth30bps_pool.token1()
    univ3_fee = univ3_ldoweth30bps_pool.fee()

    with reverts(
        mrglv1_factory.InvalidObservationCardinality,
        observationCardinality=slot0.observationCardinality,
    ):
        mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)


@pytest.mark.integration
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_factory_create_pool_with_univ3__reverts_when_pool_active(
    mrglv1_factory,
    maintenance,
    alice,
    univ3_pool,
):
    token0 = univ3_pool.token0()
    token1 = univ3_pool.token1()
    univ3_fee = univ3_pool.fee()
    mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)

    # should revert when attempt to deploy again with same params
    with reverts(mrglv1_factory.PoolActive):
        mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)


@pytest.mark.integration
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_factory_create_pool_with_univ3__reverts_when_not_enough_historical_observations(
    mrglv1_factory,
    maintenance,
    alice,
    Contract,
):
    univ3_usdtweth5bps_pool = Contract("0x11b815efB8f581194ae79006d24E0d814B7697F6")
    slot0 = univ3_usdtweth5bps_pool.slot0()
    obs_cardinality_min = mrglv1_factory.observationCardinalityMinimum()
    assert slot0.observationCardinality >= obs_cardinality_min

    # should revert at univ3 pool level
    with reverts("OLD"):
        univ3_usdtweth5bps_pool.observe([SECONDS_AGO, 0])

    token0 = univ3_usdtweth5bps_pool.token0()
    token1 = univ3_usdtweth5bps_pool.token1()
    univ3_fee = univ3_usdtweth5bps_pool.fee()

    with reverts("OLD"):
        mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)

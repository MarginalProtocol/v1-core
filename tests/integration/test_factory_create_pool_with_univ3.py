import pytest

from ape import project, reverts


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
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.factory() == mrglv1_factory.address
    assert pool.oracle() == univ3_pool.address
    assert mrglv1_factory.getPool(token0, token1, maintenance) == pool.address


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

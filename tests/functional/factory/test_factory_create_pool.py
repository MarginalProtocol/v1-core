import pytest

from ape import project, reverts


def univ3_oracle(univ3_factory_address, token_a, token_b, fee):
    # TODO: abstract with ape-yaml.config somehow?
    univ3_factory = project.dependencies["uniswap-v3-core"]["0.8"].UniswapV3Factory.at(
        univ3_factory_address
    )
    oracle = univ3_factory.getPool(token_a, token_b, fee)
    return oracle


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
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    pool = project.MarginalV1Pool.at(pool_address)

    assert pool.factory() == factory.address
    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address
    assert pool.maintenance() == maintenance
    assert pool.fee() == 1000
    assert pool.rewardPremium() == 2000000
    assert pool.secondsAgo() == 43200  # 12 hr TWAP for oracle price
    assert pool.fundingPeriod() == 604800  # 7 day funding period

    oracle = univ3_oracle(
        factory.uniswapV3Factory(), pool.token0(), pool.token1(), rando_univ3_fee
    )
    assert pool.oracle() == oracle


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
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool

    oracle = univ3_oracle(
        factory.uniswapV3Factory(),
        rando_token_a_address,
        rando_token_b_address,
        rando_univ3_fee,
    )
    assert (
        factory.getPool(
            rando_token_a_address, rando_token_b_address, maintenance, oracle
        )
        == pool_address
    )
    assert (
        factory.getPool(
            rando_token_b_address, rando_token_a_address, maintenance, oracle
        )
        == pool_address
    )
    assert factory.isPool(pool_address) is True


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
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    pool = project.MarginalV1Pool.at(pool_address)

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

    oracle = univ3_oracle(
        factory.uniswapV3Factory(),
        rando_token_a_address,
        rando_token_b_address,
        rando_univ3_fee,
    )

    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    assert event.token0 == rando_token_a_address
    assert event.token1 == rando_token_b_address
    assert (
        int(event.maintenance, 0) == maintenance
    )  # @dev returned as hex string in ape for some reason
    assert event.oracle.lower() == oracle.lower()
    assert (
        event.pool.lower()
        == factory.getPool(
            rando_token_a_address, rando_token_b_address, maintenance, oracle
        ).lower()
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
def test_create_pool__reverts_when_pool_active(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    maintenance,
    rando_univ3_fee,
):
    factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        maintenance,
        rando_univ3_fee,
        sender=alice,
    )

    # should fail when try again with same params
    with reverts(factory.PoolActive):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            maintenance,
            rando_univ3_fee,
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

    with reverts(
        factory.InvalidObservationCardinality,
        observationCardinality=slot0.observationCardinality,
    ):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            maintenance,
            rando_univ3_fee,
            sender=alice,
        )

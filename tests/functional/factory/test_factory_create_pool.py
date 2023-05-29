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
    assert pool.secondsAgo() == 3600
    assert pool.fundingPeriod() == 86400

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
    params = factory.params()
    assert params.token0 == ZERO_ADDRESS
    assert params.token1 == ZERO_ADDRESS
    assert params.maintenance == 0
    assert params.fee == 0
    assert params.oracle == ZERO_ADDRESS
    assert params.secondsAgo == 0
    assert params.fundingPeriod == 0


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_same_token(
    factory, alice, rando_token_a_address, maintenance, rando_univ3_fee
):
    with reverts("A == B"):
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
    with reverts("token0 == address(0)"):
        factory.createPool(
            ZERO_ADDRESS,
            rando_token_a_address,
            maintenance,
            rando_univ3_fee,
            sender=alice,
        )

    with reverts("token0 == address(0)"):
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
    with reverts("leverage not enabled"):
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
    with reverts("not Uniswap pool"):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            maintenance,
            10,  # uni pool with 1 bps fee doesn't exist in mock
            sender=alice,
        )

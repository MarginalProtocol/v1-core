import pytest
from ape import project, reverts
from ape.utils import ZERO_ADDRESS


@pytest.fixture
def factory(project, deployer):
    return project.MarginalV1Factory.deploy(sender=deployer)


def test_create_pool_deploys_pool_contract(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    tx = factory.createPool(
        rando_token_a_address, rando_token_b_address, 2500, sender=alice
    )
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.factory() == factory.address
    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address
    assert pool.maintenance() == 2500


def test_create_pool_stores_pool_address(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    tx = factory.createPool(
        rando_token_a_address, rando_token_b_address, 2500, sender=alice
    )
    pool_address = tx.return_value
    assert (
        factory.getPool(rando_token_a_address, rando_token_b_address, 2500)
        == pool_address
    )
    assert (
        factory.getPool(rando_token_b_address, rando_token_a_address, 2500)
        == pool_address
    )


def test_create_pool_orders_tokens(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    tx = factory.createPool(
        rando_token_b_address, rando_token_a_address, 2500, sender=alice
    )
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address


def test_create_pool_emits_pool_created(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    tx = factory.createPool(
        rando_token_a_address, rando_token_b_address, 2500, sender=alice
    )
    # tx.show_trace(verbose=True)
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    assert event.token0 == rando_token_a_address
    assert event.token1 == rando_token_b_address
    assert event.maintenance == 2500
    assert event.pool == tx.return_value


def test_create_pool_deletes_params(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    _ = factory.createPool(
        rando_token_a_address, rando_token_b_address, 2500, sender=alice
    )
    params = factory.params()
    assert params.token0 == ZERO_ADDRESS
    assert params.token1 == ZERO_ADDRESS
    assert params.maintenance == 0


def test_create_pool_reverts_when_same_token(factory, alice, rando_token_a_address):
    with reverts("A == B"):
        factory.createPool(
            rando_token_a_address, rando_token_a_address, 2500, sender=alice
        )


def test_create_pool_reverts_when_token_is_zero_address(
    factory, alice, rando_token_a_address
):
    with reverts("token0 == address(0)"):
        factory.createPool(ZERO_ADDRESS, rando_token_a_address, 2500, sender=alice)

    with reverts("token0 == address(0)"):
        factory.createPool(rando_token_a_address, ZERO_ADDRESS, 2500, sender=alice)


def test_create_pool_reverts_when_invalid_maintenance(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    with reverts("leverage not enabled"):
        factory.createPool(
            rando_token_a_address, rando_token_b_address, 1000, sender=alice
        )

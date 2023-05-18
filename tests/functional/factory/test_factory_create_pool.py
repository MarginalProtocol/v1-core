import pytest

from ape import project, reverts
from ape.utils import ZERO_ADDRESS


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__deploys_pool_contract(
    factory, alice, rando_token_a_address, rando_token_b_address, maintenance
):
    tx = factory.createPool(
        rando_token_a_address, rando_token_b_address, maintenance, sender=alice
    )
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.factory() == factory.address
    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address
    assert pool.maintenance() == maintenance


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__stores_pool_address(
    factory, alice, rando_token_a_address, rando_token_b_address, maintenance
):
    tx = factory.createPool(
        rando_token_a_address, rando_token_b_address, maintenance, sender=alice
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
    factory, alice, rando_token_a_address, rando_token_b_address, maintenance
):
    tx = factory.createPool(
        rando_token_b_address, rando_token_a_address, maintenance, sender=alice
    )
    pool = project.MarginalV1Pool.at(tx.return_value)

    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__emits_pool_created(
    factory, alice, rando_token_a_address, rando_token_b_address, maintenance
):
    tx = factory.createPool(
        rando_token_a_address, rando_token_b_address, maintenance, sender=alice
    )
    # tx.show_trace(verbose=True)
    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    assert event.token0 == rando_token_a_address
    assert event.token1 == rando_token_b_address
    assert event.maintenance == maintenance
    assert event.pool == tx.return_value


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__deletes_params(
    factory, alice, rando_token_a_address, rando_token_b_address, maintenance
):
    _ = factory.createPool(
        rando_token_a_address, rando_token_b_address, maintenance, sender=alice
    )
    params = factory.params()
    assert params.token0 == ZERO_ADDRESS
    assert params.token1 == ZERO_ADDRESS
    assert params.maintenance == 0
    assert params.fee == 0


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_same_token(
    factory, alice, rando_token_a_address, maintenance
):
    with reverts("A == B"):
        factory.createPool(
            rando_token_a_address, rando_token_a_address, maintenance, sender=alice
        )


@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_create_pool__reverts_when_token_is_zero_address(
    factory, alice, rando_token_a_address, maintenance
):
    with reverts("token0 == address(0)"):
        factory.createPool(
            ZERO_ADDRESS, rando_token_a_address, maintenance, sender=alice
        )

    with reverts("token0 == address(0)"):
        factory.createPool(
            rando_token_a_address, ZERO_ADDRESS, maintenance, sender=alice
        )


def test_create_pool__reverts_when_invalid_maintenance(
    factory, alice, rando_token_a_address, rando_token_b_address
):
    with reverts("leverage not enabled"):
        factory.createPool(
            rando_token_a_address, rando_token_b_address, 1000, sender=alice
        )

import pytest

from ape import reverts
from utils.constants import SECONDS_AGO, MINIMUM_LIQUIDITY


@pytest.mark.integration
@pytest.mark.parametrize("maintenance", [250000, 500000, 1000000])
def test_pool_initialize_with_univ3__reverts_when_not_enough_historical_observations(
    mrglv1_factory,
    callee,
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

    tx = mrglv1_factory.createPool(token0, token1, maintenance, univ3_fee, sender=alice)
    pool_address = tx.decode_logs(mrglv1_factory.PoolCreated)[0].pool

    with reverts("OLD"):
        callee.mint(
            pool_address,
            alice.address,
            MINIMUM_LIQUIDITY + 1,
            sender=alice,
        )

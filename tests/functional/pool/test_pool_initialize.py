from ape import reverts
from math import log, sqrt


def test_pool_initialize__updates_state(pool, alice, chain):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    price = y // x
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    tick = int(log(price) / log(1.0001))

    pool.initialize(sqrt_price_x96, sender=alice)
    state = (0, sqrt_price_x96, 0, tick, chain.blocks.head.timestamp, 0, 0, True)
    result = pool.state()
    assert result == state


def test_pool_initialize__emits_initialize(pool, alice):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    price = y // x
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96
    tick = int(log(price) / log(1.0001))

    tx = pool.initialize(sqrt_price_x96, sender=alice)
    events = tx.decode_logs(pool.Initialize)
    assert len(events) == 1
    event = events[0]

    assert event.sqrtPriceX96 == sqrt_price_x96
    assert event.tick == tick


def test_pool_initialize__reverts_when_initialized(pool, alice):
    x = int(125.04e12)  # e.g. USDC reserves
    y = int(71.70e21)  # e.g. WETH reserves
    sqrt_price = int(sqrt(y / x))
    sqrt_price_x96 = sqrt_price << 96

    pool.initialize(sqrt_price_x96, sender=alice)

    with reverts(pool.Initialized):
        pool.initialize(sqrt_price_x96, sender=alice)

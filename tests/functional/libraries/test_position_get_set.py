from eth_abi.packed import encode_packed
from eth_utils import keccak


def test_position_set(position_lib, alice):
    id = 1
    position = (1000000, 100, 200, 50, 60, True, -1000)
    position_lib.set(alice, id, position, sender=alice)

    key = keccak(encode_packed(["address", "uint112"], [alice.address, id]))
    assert position_lib.positions(key) == position


def test_position_get(position_lib, alice):
    id = 1
    position = (1000000, 100, 200, 50, 60, True, -1000)
    position_lib.set(alice, id, position, sender=alice)
    assert position_lib.get(alice, id) == position

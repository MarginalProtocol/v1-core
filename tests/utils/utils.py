from math import log, sqrt

from eth_abi.packed import encode_packed
from eth_utils import keccak

from utils.constants import MAINTENANCE_UNIT


def get_position_key(address: str, id: int) -> bytes:
    return keccak(encode_packed(["address", "uint112"], [address, id]))


def calc_tick_from_sqrt_price_x96(sqrt_price_x96: int) -> int:
    price = (sqrt_price_x96**2) / (1 << 192)
    return int(log(price) // log(1.0001))


def calc_sqrt_price_x96_next_open(
    liquidity: int,
    sqrt_price_x96: int,
    liquidity_delta: int,
    zero_for_one: bool,
    maintenance: int,
) -> int:
    prod = (liquidity_delta * (liquidity - liquidity_delta) * MAINTENANCE_UNIT) // (
        MAINTENANCE_UNIT + maintenance
    )
    under = liquidity**2 - 4 * prod
    root = int(sqrt(under))

    sqrt_price_x96_next = (
        int(sqrt_price_x96 * (liquidity + root)) // (2 * (liquidity - liquidity_delta))
        if not zero_for_one
        else int(sqrt_price_x96 * 2 * (liquidity - liquidity_delta))
        // (liquidity + root)
    )

    return sqrt_price_x96_next


def calc_insurances(
    liquidity: int,
    sqrt_price_x96: int,
    sqrt_price_x96_next: int,
    liquidity_delta: int,
    zero_for_one: bool,
) -> (int, int):
    prod = (
        ((liquidity - liquidity_delta) * sqrt_price_x96_next) // sqrt_price_x96
        if not zero_for_one
        else ((liquidity - liquidity_delta) * sqrt_price_x96) // sqrt_price_x96_next
    )
    insurance0 = ((liquidity - prod) << 96) // sqrt_price_x96
    insurance1 = ((liquidity - prod) * sqrt_price_x96) // (1 << 96)
    return (insurance0, insurance1)


def calc_debts(
    sqrt_price_x96_next: int,
    liquidity_delta: int,
    insurance0: int,
    insurance1: int,
) -> (int, int):
    debt0 = (liquidity_delta << 96) // sqrt_price_x96_next - insurance0
    debt1 = (liquidity_delta * sqrt_price_x96_next) // (1 << 96) - insurance1
    return (debt0, debt1)


def calc_amounts_from_liquidity_sqrt_price_x96(
    liquidity: int, sqrt_price_x96: int
) -> (int, int):
    amount0 = (liquidity << 96) // sqrt_price_x96
    amount1 = (liquidity * sqrt_price_x96) // (1 << 96)
    return (amount0, amount1)


# @dev sqrt in OZ solidity results in slight diff with python math.sqrt
def calc_liquidity_sqrt_price_x96_from_reserves(
    reserve0: int, reserve1: int
) -> (int, int):
    liquidity = int(sqrt(reserve0 * reserve1))
    sqrt_price_x96 = (liquidity << 96) // reserve0
    return (liquidity, sqrt_price_x96)

from math import sqrt
from utils.constants import MAINTENANCE_UNIT


def calc_sqrt_price_x96_next(
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
        if zero_for_one
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
        if zero_for_one
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

from math import log, sqrt

from eth_abi.packed import encode_packed
from eth_utils import keccak

from utils.constants import FEE_UNIT, MAINTENANCE_UNIT, FUNDING_PERIOD


def get_position_key(address: str, id: int) -> bytes:
    return keccak(encode_packed(["address", "uint96"], [address, id]))


def calc_tick_from_sqrt_price_x96(sqrt_price_x96: int) -> int:
    price = (sqrt_price_x96**2) / (1 << 192)
    return int(log(price) // log(1.0001))


def calc_sqrt_price_x96_from_tick(tick: int) -> int:
    return int(sqrt(1.0001**tick)) * (1 << 96)


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


def calc_sqrt_price_x96_next_swap_exact_input(
    liquidity: int, sqrt_price_x96: int, zero_for_one: bool, amount_specified: int
) -> int:
    assert amount_specified > 0
    if zero_for_one:
        # sqrtP' = L / (del x + x)
        (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
            liquidity, sqrt_price_x96
        )
        return (liquidity << 96) // (reserve0 + amount_specified)
    else:
        # sqrtP' = del y / L + sqrtP
        return (amount_specified << 96) // liquidity + sqrt_price_x96


def calc_sqrt_price_x96_next_swap_exact_output(
    liquidity: int, sqrt_price_x96: int, zero_for_one: bool, amount_specified: int
) -> int:
    assert amount_specified <= 0
    if zero_for_one:
        # sqrtP' = del y / L + sqrtP
        return (amount_specified << 96) // liquidity + sqrt_price_x96
    else:
        # sqrtP' = L / (del x + x)
        (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
            liquidity, sqrt_price_x96
        )
        return (liquidity << 96) // (reserve0 + amount_specified)


def calc_sqrt_price_x96_next_swap(
    liquidity: int, sqrt_price_x96: int, zero_for_one: bool, amount_specified: int
) -> int:
    exact_input = amount_specified > 0
    return (
        calc_sqrt_price_x96_next_swap_exact_input(
            liquidity, sqrt_price_x96, zero_for_one, amount_specified
        )
        if exact_input
        else calc_sqrt_price_x96_next_swap_exact_output(
            liquidity, sqrt_price_x96, zero_for_one, amount_specified
        )
    )


def calc_insurances_from_root(
    liquidity: int,
    sqrt_price_x96: int,
    liquidity_delta: int,
    maintenance: int,
) -> (int, int):
    prod = liquidity_delta * (liquidity - liquidity_delta)
    prod = (prod * 1e6) // (1e6 + maintenance)

    under = liquidity**2 - 4 * prod
    root = int(sqrt(under))

    # iy = (sqrt(P) / 2) * (L - sqrt(L**2 - (4/(1+M)) * del L * (L - del L)))
    # ix = iy / P
    insurance1 = (((liquidity - root) * sqrt_price_x96) // (1 << 96)) // 2
    insurance0 = (((liquidity - root) * (1 << 96)) // sqrt_price_x96) // 2
    return (insurance0, insurance1)


def calc_debts_from_root(
    liquidity: int,
    sqrt_price_x96: int,
    liquidity_delta: int,
    insurance0: int,
    insurance1: int,
    zero_for_one: bool,
) -> (int, int):
    (x, y) = calc_amounts_from_liquidity_sqrt_price_x96(liquidity, sqrt_price_x96)
    (x_delta, y_delta) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta, sqrt_price_x96
    )

    if not zero_for_one:
        # dx = del L * ((L - del L) / (L * sqrt(P) - iy)) - ix
        # dy = L * ((del L * sqrt(P) - iy) / (L - del L))
        debt0 = (liquidity_delta * (liquidity - liquidity_delta)) // (
            y - insurance1
        ) - insurance0
        debt1 = (liquidity * (y_delta - insurance1)) // (liquidity - liquidity_delta)
    else:
        # dy = del L * ((L - del L) / (L / sqrt(P) - ix)) - iy
        # dx = L * ((del L / sqrt(P) - ix) / (L - del L))
        debt1 = (liquidity_delta * (liquidity - liquidity_delta)) // (
            x - insurance0
        ) - insurance1
        debt0 = (liquidity * (x_delta - insurance0)) // (liquidity - liquidity_delta)

    return (debt0, debt1)


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


def calc_swap_amounts(
    liquidity: int, sqrt_price_x96: int, sqrt_price_x96_next: int
) -> (int, int):
    amount0 = (liquidity << 96) // sqrt_price_x96_next - (
        liquidity << 96
    ) // sqrt_price_x96
    amount1 = (liquidity * (sqrt_price_x96_next - sqrt_price_x96)) // (1 << 96)
    return (amount0, amount1)


def calc_swap_fees(amount_in: int, fee: int) -> int:
    return (amount_in * fee) // FEE_UNIT


def calc_debts_after_funding(
    debt0: int,
    debt1: int,
    zero_for_one: bool,
    tick_cumulative_start: int,
    oracle_tick_cumulative_start: int,
    tick_cumulative_last: int,
    oracle_tick_cumulative_last: int,
) -> (int, int):
    if zero_for_one:
        tick_cumulative_delta = (
            oracle_tick_cumulative_last - oracle_tick_cumulative_start
        ) - (tick_cumulative_last - tick_cumulative_start)

        debt0 = int(debt0 * (1.0001 ** (tick_cumulative_delta / FUNDING_PERIOD)))
        return (debt0, debt1)
    else:
        tick_cumulative_delta = (tick_cumulative_last - tick_cumulative_start) - (
            oracle_tick_cumulative_last - oracle_tick_cumulative_start
        )

        debt1 = int(debt1 * (1.0001 ** (tick_cumulative_delta / FUNDING_PERIOD)))
        return (debt0, debt1)

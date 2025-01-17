import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
    calc_tick_from_sqrt_price_x96,
)


def test_pool_swap__updates_state_with_exact_input_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = amount_specified - amount0
    amount0 += fees0

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1,
    )
    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


def test_pool_swap__updates_state_with_exact_input_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = amount_specified - amount1
    amount1 += fees1

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1,
    )
    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


def test_pool_swap__updates_state_with_exact_output_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = swap_math_lib.swapFees(amount0, fee, True)
    amount0 += fees0

    # set amount out to amount specified as exact output
    amount1 = amount_specified

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1,
    )

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


def test_pool_swap__updates_state_with_exact_output_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = swap_math_lib.swapFees(amount1, fee, True)
    amount1 += fees1

    # set amount out to amount specified as exact output
    amount0 = amount_specified

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1,
    )

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    assert pool_initialized_with_liquidity.state() == state


def test_pool_swap__transfers_funds_with_exact_input_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = amount_specified - amount0
    amount0 += fees0

    balance0_sender = token0.balanceOf(sender.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert token1.balanceOf(alice.address) == balance1_alice - amount1


def test_pool_swap__transfers_funds_with_exact_input_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = amount_specified - amount1
    amount1 += fees1

    balance1_sender = token1.balanceOf(sender.address)
    balance0_alice = token0.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert token0.balanceOf(alice.address) == balance0_alice - amount0


def test_pool_swap__transfers_funds_with_exact_output_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = swap_math_lib.swapFees(amount0, fee, True)
    amount0 += fees0

    # set amount out to amount specified as exact output
    amount1 = amount_specified

    balance0_sender = token0.balanceOf(sender.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert token1.balanceOf(alice.address) == balance1_alice - amount1


def test_pool_swap__transfers_funds_with_exact_output_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = swap_math_lib.swapFees(amount1, fee, True)
    amount1 += fees1

    # set amount out to amount specified as exact output
    amount0 = amount_specified

    balance1_sender = token1.balanceOf(sender.address)
    balance0_alice = token0.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert token0.balanceOf(alice.address) == balance0_alice - amount0


@pytest.mark.skip
def test_pool_swap__adds_protocol_fees_with_exact_input_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    admin,
    token0,
    token1,
    chain,
):
    pool_initialized_with_liquidity.setFeeProtocol(10, sender=admin)

    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    protocol_fees = pool_initialized_with_liquidity.protocolFees()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees with protocol fee
    fees0 = amount_specified - amount0
    delta = fees0 // state.feeProtocol

    amount0 += fees0
    protocol_fees.token0 += delta

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0 - delta,
        amount1,
    )
    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    balance0_sender = token0.balanceOf(sender.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state
    assert pool_initialized_with_liquidity.protocolFees() == protocol_fees

    # check funds, return values, event remains as expected
    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert token1.balanceOf(alice.address) == balance1_alice - amount1

    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


@pytest.mark.skip
def test_pool_swap__adds_protocol_fees_with_exact_input_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    position_lib,
    sender,
    alice,
    admin,
    token0,
    token1,
    chain,
):
    pool_initialized_with_liquidity.setFeeProtocol(10, sender=admin)

    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()
    protocol_fees = pool_initialized_with_liquidity.protocolFees()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees with protocol fee
    fees1 = amount_specified - amount1
    delta = fees1 // state.feeProtocol

    amount1 += fees1
    protocol_fees.token1 += delta

    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = liquidity_math_lib.liquiditySqrtPriceX96Next(
        state.liquidity,
        state.sqrtPriceX96,
        amount0,
        amount1 - delta,
    )
    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    balance1_sender = token1.balanceOf(sender.address)
    balance0_alice = token0.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state
    assert pool_initialized_with_liquidity.protocolFees() == protocol_fees

    # check funds, return values, event remains as expected
    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert token0.balanceOf(alice.address) == balance0_alice - amount0

    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


def test_pool_swap__calls_swap_callback_with_exact_input_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = amount_specified - amount0
    amount0 += fees0

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


def test_pool_swap__calls_swap_callback_with_exact_input_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = amount_specified - amount1
    amount1 += fees1

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


def test_pool_swap__calls_swap_callback_with_exact_output_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = swap_math_lib.swapFees(amount0, fee, True)
    amount0 += fees0

    # set amount out to amount specified as exact output
    amount1 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


def test_pool_swap__calls_swap_callback_with_exact_output_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = swap_math_lib.swapFees(amount1, fee, True)
    amount1 += fees1

    # set amount out to amount specified as exact output
    amount0 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


def test_pool_swap__emits_swap_with_exact_input_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = amount_specified - amount0
    amount0 += fees0

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


def test_pool_swap__emits_swap_with_exact_input_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = amount_specified - swap_math_lib.swapFees(
        amount_specified, fee, False
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = amount_specified - amount1
    amount1 += fees1

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


def test_pool_swap__emits_swap_with_exact_output_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees0 = swap_math_lib.swapFees(amount0, fee, True)
    amount0 += fees0

    # set amount out to amount specified as exact output
    amount1 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


def test_pool_swap__emits_swap_with_exact_output_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees ignoring protocol fee (== 0)
    fees1 = swap_math_lib.swapFees(amount1, fee, True)
    amount1 += fees1

    # set amount out to amount specified as exact output
    amount0 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


def test_pool_swap__reverts_when_amount_specified_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    zero_for_one = True
    amount_specified = 0
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    with reverts(pool_initialized_with_liquidity.InvalidAmountSpecified):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_sqrt_price_limit_x96_greater_than_sqrt_price_x96_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    zero_for_one = True
    amount_specified = 1000000

    state = pool_initialized_with_liquidity.state()
    sqrt_price_limit_x96 = state.sqrtPriceX96 + 1

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_sqrt_price_limit_x96_less_than_min_sqrt_ratio_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    zero_for_one = True
    amount_specified = 1000000
    sqrt_price_limit_x96 = MIN_SQRT_RATIO

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_sqrt_price_limit_x96_less_than_sqrt_price_x96_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    zero_for_one = False
    amount_specified = 1000000

    state = pool_initialized_with_liquidity.state()
    sqrt_price_limit_x96 = state.sqrtPriceX96 - 1

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_sqrt_price_limit_x96_greater_than_max_sqrt_ratio_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    zero_for_one = False
    amount_specified = 1000000
    sqrt_price_limit_x96 = MAX_SQRT_RATIO

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_sqrt_price_x96_next_less_than_sqrt_price_limit_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next + 1

    with reverts(pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_sqrt_price_x96_next_greater_than_sqrt_price_limit_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next - 1

    with reverts(pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_amount0_transferred_less_than_min_with_zero_for_one(
    pool_initialized_with_liquidity,
    callee_below_min0,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    with reverts(pool_initialized_with_liquidity.Amount0LessThanMin):
        callee_below_min0.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_amount1_transferred_less_than_min_with_one_for_zero(
    pool_initialized_with_liquidity,
    callee_below_min1,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()

    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
        callee_below_min1.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=500))
@given(
    amount_specified_pc=st.integers(
        min_value=-(1000000000 - 1), max_value=1000000000000000
    ),
    zero_for_one=st.booleans(),
)
def test_pool_swap__with_fuzz(
    pool_initialized_with_liquidity,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    amount_specified_pc,
    zero_for_one,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**128 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**128 - 1 - balance1_sender, sender=sender)

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)  # 2**128-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**128-1
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    amount_specified = 0
    if amount_specified_pc == 0:
        return
    elif amount_specified_pc > 0:
        amount_specified = (
            (balance0_pool * amount_specified_pc) // 1000000000
            if zero_for_one
            else (balance1_pool * amount_specified_pc) // 1000000000
        )
    else:
        amount_specified = (
            (balance1_pool * amount_specified_pc) // 1000000000
            if zero_for_one
            else (balance0_pool * amount_specified_pc) // 1000000000
        )

    # set up fuzz test of swap
    state = pool_initialized_with_liquidity.state()
    fee = pool_initialized_with_liquidity.fee()

    exact_input = amount_specified > 0
    sqrt_price_limit_x96 = (
        MAX_SQRT_RATIO - 1 if not zero_for_one else MIN_SQRT_RATIO + 1
    )

    # cache for later sanity checks
    _liquidity = state.liquidity
    _sqrt_price_x96 = state.sqrtPriceX96

    # oracle updates
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    amount_specified_less_fee = (
        amount_specified - swap_math_lib.swapFees(amount_specified, fee, False)
        if exact_input
        else amount_specified
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified_less_fee,
    )
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # include swap fees on input amount ignoring protocol fee (== 0)
    fees = (
        swap_math_lib.swapFees(amount0, fee, True)
        if zero_for_one
        else swap_math_lib.swapFees(amount1, fee, True)
    )
    if exact_input:
        fees = (
            amount_specified - amount0 if zero_for_one else amount_specified - amount1
        )

    fees0 = fees if zero_for_one else 0
    fees1 = 0 if zero_for_one else fees
    amount0 += fees0
    amount1 += fees1

    # set amount out to amount specified as exact output
    if not exact_input:
        amount0 = amount0 if zero_for_one else amount_specified
        amount1 = amount_specified if zero_for_one else amount1

    params = (
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
    )
    tx = callee.swap(*params, sender=sender)
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    # check pool state transition
    # TODO: also test with protocol fee
    (reserve0, reserve1) = calc_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96
    )
    (
        liquidity_after,
        sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(
        reserve0 + amount0, reserve1 + amount1
    )
    state.liquidity = liquidity_after
    state.sqrtPriceX96 = sqrt_price_x96_after
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_after)

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    result_state = pool_initialized_with_liquidity.state()
    assert pytest.approx(result_state.liquidity, rel=1e-14) == state.liquidity
    assert pytest.approx(result_state.sqrtPriceX96, rel=1e-14) == state.sqrtPriceX96
    assert result_state.tick == state.tick
    assert result_state.blockTimestamp == state.blockTimestamp
    assert result_state.tickCumulative == state.tickCumulative
    assert result_state.totalPositions == state.totalPositions

    # sanity check pool state
    # excluding fees should have after swap
    #  L = L
    #  sqrt(P') = sqrt(P) * (1 + dy / y) = sqrt(P) / (1 + dx / x); dx, dy can be > 0 or < 0
    calc_liquidity_next = _liquidity

    # del x, del y without fees
    _del_x = amount0 if amount0 < 0 else amount0 - fees0
    _del_y = amount1 if amount1 < 0 else amount1 - fees1

    _del_sqrt_price_y = 1 + _del_y / reserve1
    _del_sqrt_price_x = 1 / (1 + _del_x / reserve0)

    # L invariant on swap requires
    #  1 + dy / y = 1 / (1 + dx / x)
    assert pytest.approx(_del_sqrt_price_y, rel=1e-6) == _del_sqrt_price_x
    calc_sqrt_price_x96_next = int(_sqrt_price_x96 * _del_sqrt_price_y)

    # add in the fees
    (_reserve0_next, _reserve1_next) = calc_amounts_from_liquidity_sqrt_price_x96(
        calc_liquidity_next, calc_sqrt_price_x96_next
    )
    (
        _liquidity_after,
        _sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(
        _reserve0_next + fees0, _reserve1_next + fees1
    )
    assert pytest.approx(result_state.liquidity, rel=1e-6) == _liquidity_after
    assert pytest.approx(result_state.sqrtPriceX96, rel=1e-6) == _sqrt_price_x96_after

    state = result_state  # for event checks below

    # check balances
    amount0_sender = -amount0 if zero_for_one else 0
    amount1_sender = 0 if zero_for_one else -amount1

    amount0_alice = 0 if zero_for_one else -amount0
    amount1_alice = -amount1 if zero_for_one else 0

    balance0_pool += amount0
    balance1_pool += amount1
    balance0_sender += amount0_sender
    balance1_sender += amount1_sender
    balance0_alice += amount0_alice
    balance1_alice += amount1_alice

    result_balance0_sender = token0.balanceOf(sender.address)
    result_balance1_sender = token1.balanceOf(sender.address)
    result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    result_balance0_alice = token0.balanceOf(alice.address)
    result_balance1_alice = token1.balanceOf(alice.address)

    assert result_balance0_sender == balance0_sender
    assert result_balance1_sender == balance1_sender
    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool
    assert result_balance0_alice == balance0_alice
    assert result_balance1_alice == balance1_alice

    # TODO: check protocol fees (add fuzz param)

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)

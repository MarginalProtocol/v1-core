import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import (
    calc_amounts_from_liquidity_sqrt_price_x96,
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
        amount_specified, fee
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
        amount_specified, fee
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
    fees0 = swap_math_lib.swapFees(amount0, fee)
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
    fees1 = swap_math_lib.swapFees(amount1, fee)
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
        amount_specified, fee
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
        amount_specified, fee
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
    fees0 = swap_math_lib.swapFees(amount0, fee)
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
    fees1 = swap_math_lib.swapFees(amount1, fee)
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
        amount_specified, fee
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

    assert tx.return_value[0] == amount0
    assert tx.return_value[1] == amount1

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
        amount_specified, fee
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

    assert tx.return_value[0] == amount0
    assert tx.return_value[1] == amount1

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
        amount_specified, fee
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
        amount_specified, fee
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
    fees0 = swap_math_lib.swapFees(amount0, fee)
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
    fees1 = swap_math_lib.swapFees(amount1, fee)
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
        amount_specified, fee
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

    assert tx.return_value[0] == amount0
    assert tx.return_value[1] == amount1

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
        amount_specified, fee
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

    assert tx.return_value[0] == amount0
    assert tx.return_value[1] == amount1

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
    fees0 = swap_math_lib.swapFees(amount0, fee)
    amount0 += fees0

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert tx.return_value[0] == amount0
    assert tx.return_value[1] == amount1

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
    fees1 = swap_math_lib.swapFees(amount1, fee)
    amount1 += fees1

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert tx.return_value[0] == amount0
    assert tx.return_value[1] == amount1

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

    with reverts(
        pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit,
        sqrtPriceX96Next=sqrt_price_x96_next,
    ):
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

    with reverts(
        pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit,
        sqrtPriceX96Next=sqrt_price_x96_next,
    ):
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


# TODO:
@pytest.mark.fuzzing
def test_pool_swap__with_fuzz():
    pass

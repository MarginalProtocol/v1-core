from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import get_position_key, calc_tick_from_sqrt_price_x96


def test_pool_open__updates_state_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96Next(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )
    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next

    state.totalPositions += 1
    assert pool_initialized_with_liquidity.state() == state


def test_pool_open__updates_state_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96Next(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )
    state.liquidity -= liquidity_delta
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.tickCumulative = tick_cumulative
    state.blockTimestamp = block_timestamp_next

    state.totalPositions += 1
    assert pool_initialized_with_liquidity.state() == state


def test_pool_open__updates_reserves_locked_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96Next(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)

    # fees added to debt of margin token
    position.debt1 += fees

    # get amounts locked to back position
    (amount0_locked, amount1_locked) = position_lib.amountsLocked(position)

    reserve0_locked += amount0_locked
    reserve1_locked += amount1_locked

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )

    print("(reserve0_locked, reserve1_locked)", (reserve0_locked, reserve1_locked))

    assert pool_initialized_with_liquidity.reservesLocked() == (
        reserve0_locked,
        reserve1_locked,
    )


def test_pool_open__updates_reserves_locked_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    callee,
    sender,
    alice,
    token0,
    token1,
):
    state = pool_initialized_with_liquidity.state()
    (
        reserve0_locked,
        reserve1_locked,
    ) = pool_initialized_with_liquidity.reservesLocked()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96Next(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        0,  # @dev irrelevant for this test
        0,  # @dev irrelevant for this test
    )
    fees = position_lib.fees(position.size, fee)

    # fees added to debt of margin token
    position.debt0 += fees

    # get amounts locked to back position
    (amount0_locked, amount1_locked) = position_lib.amountsLocked(position)

    reserve0_locked += amount0_locked
    reserve1_locked += amount1_locked

    callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.reservesLocked() == (
        reserve0_locked,
        reserve1_locked,
    )


def test_pool_open__sets_position_with_zero_for_one(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96Next(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    fees = position_lib.fees(position.size, fee)
    margin_min = position_lib.marginMinimum(position.size, maintenance)

    # fees added to debt of margin token
    position.debt1 += fees
    position.margin = margin_min  # @dev given callee setup

    id = state.totalPositions
    key = get_position_key(alice.address, id)
    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )

    result = pool_initialized_with_liquidity.positions(key)
    assert tx.return_value == id
    assert result == position


def test_pool_open__sets_position_with_one_for_zero(
    pool_initialized_with_liquidity,
    position_lib,
    sqrt_price_math_lib,
    rando_univ3_observations,
    callee,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    state = pool_initialized_with_liquidity.state()
    maintenance = pool_initialized_with_liquidity.maintenance()
    fee = pool_initialized_with_liquidity.fee()

    liquidity = state.liquidity
    liquidity_delta = liquidity * 500 // 10000  # 5% of pool reserves leveraged
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    tick_cumulative = state.tickCumulative + state.tick * (
        chain.pending_timestamp - state.blockTimestamp
    )
    obs = rando_univ3_observations[-1]  # @dev last obs
    oracle_tick_cumulative = obs[1]  # tick cumulative

    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96Next(
        state.liquidity, state.sqrtPriceX96, liquidity_delta, zero_for_one, maintenance
    )
    position = position_lib.assemble(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
        liquidity_delta,
        zero_for_one,
        tick_cumulative,
        oracle_tick_cumulative,
    )
    fees = position_lib.fees(position.size, fee)
    margin_min = position_lib.marginMinimum(position.size, maintenance)

    # fees added to debt of margin token
    position.debt0 += fees
    position.margin = margin_min  # @dev given callee setup

    id = state.totalPositions
    key = get_position_key(alice.address, id)
    tx = callee.open(
        pool_initialized_with_liquidity.address,
        alice.address,
        liquidity_delta,
        zero_for_one,
        sqrt_price_limit_x96,
        sender=sender,
    )

    result = pool_initialized_with_liquidity.positions(key)
    assert tx.return_value == id
    assert result == position


def test_pool_open__transfers_funds_with_zero_for_one():
    pass


def test_pool_open__transfers_funds_with_one_for_zero():
    pass


def test_pool_open__emits_open_with_zero_for_one(pool, alice, bob):
    pass


def test_pool_open__emits_open_with_one_for_zero(pool, alice, bob):
    pass

// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title The interface for a Marginal v1 pool
/// @notice A Marginal v1 pool facilitates leverage trading, swapping, and automated market making between any two assets that strictly conform
/// to the ERC20 specification
/// @dev Inherits from IERC20 as liquidity providers are minted fungible pool tokens
interface IMarginalV1Pool is IERC20 {
    /// @notice The Marginal v1 factory that created the pool
    /// @return The address of the Marginal v1 factory
    function factory() external view returns (address);

    /// @notice The Uniswap v3 oracle referenced by the pool for funding and position safety
    /// @return The address of the Uniswap v3 oracle referenced by the pool
    function oracle() external view returns (address);

    /// @notice The first of the two tokens of the pool, sorted by address
    /// @return The address of the token0 contract
    function token0() external view returns (address);

    /// @notice The second of the two tokens of the pool, sorted by address
    /// @return The address of the token1 contract
    function token1() external view returns (address);

    /// @notice The minimum maintenance requirement for leverage positions on the pool
    /// @return The minimum maintenance requirement
    function maintenance() external view returns (uint24);

    /// @notice The pool's fee in hundredths of a bip, i.e. 1e-6
    /// @return The fee
    function fee() external view returns (uint24);

    /// @notice The premium multiplier on liquidation rewards in hundredths of a bip, i.e. 1e-6
    /// @dev Liquidation rewards set aside in native (gas) token.
    /// Premium acts as an incentive above the expected gas cost to call IMarginalV1Pool#liquidate.
    /// @return The premium multiplier
    function rewardPremium() external view returns (uint24);

    /// @notice The maximum rate of change in tick cumulative between the Marginal v1 pool and the Uniswap v3 oracle
    /// @dev Puts a ceiling on funding paid per second
    /// @return The maximum tick cumulative rate per second
    function tickCumulativeRateMax() external view returns (uint24);

    /// @notice The amount of time in seconds to average the Uniswap v3 oracle TWAP over to assess position safety
    /// @return The averaging time for the Uniswap v3 oracle TWAP in seconds
    function secondsAgo() external view returns (uint32);

    /// @notice The period in seconds to benchmark funding payments with respect to
    /// @dev Acts as an averaging period on tick cumulative changes between the Marginal v1 pool and the Uniswap v3 oracle
    /// @return The funding period in seconds
    function fundingPeriod() external view returns (uint32);

    /// @notice The pool state represented in (L, sqrt(P)) space
    /// @return sqrtPriceX96 The current price of the pool as a sqrt(token1/token0) Q64.96 value
    /// totalPositions The total number of leverage positions that have ever been taken out on the pool
    /// liquidity The currently available liquidity offered by the pool for swaps and leverage positions
    /// tick The current tick of the pool, i.e. according to the last tick transition that was run.
    /// blockTimestamp The last `block.timestamp` at which state was synced
    /// tickCumulative The tick cumulative running sum of the pool, used in funding calculations
    /// feeProtocol The protocol fee for both tokens of the pool
    /// initialized Whether the pool has been initialized
    function state()
        external
        view
        returns (
            uint160 sqrtPriceX96,
            uint96 totalPositions,
            uint128 liquidity,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulative,
            uint8 feeProtocol,
            bool initialized
        );

    /// @notice The liquidity used to capitalize outstanding leverage positions
    /// @return The liquidity locked for outstanding leverage positions
    function liquidityLocked() external view returns (uint128);

    /// @notice The amounts of token0 and token1 that are owed to the protocol
    /// @dev Protocol fees will never exceed uint128 max in either token
    /// @return protocolFees0 The amount of token0 owed to the protocol
    /// @return protocolFees1 The amount of token1 owed to the protocol
    function protocolFees()
        external
        view
        returns (uint128 protocolFees0, uint128 protocolFees1);

    /// @notice Returns information about a leverage position by the position's key
    /// @dev Either debt0 (zeroForOne = true) or debt1 (zeroForOne = false) will be updated each funding sync
    /// @param key The position's key is a hash of the packed encoding of the owner and the position ID
    /// @return size The position size in the token the owner is long
    /// debt0 The position debt in token0 owed to the pool at settlement. If long token1 (zeroForOne = true), this is the debt to be repaid at settlement by owner. Otherwise, simply used for internal accounting
    /// debt1 The position debt in token1 owed to the pool at settlement. If long token0 (zeroForOne = false), this is the debt to be repaid at settlement by owner. Otherwise, simply used for internal accounting
    /// insurance0 The insurance in token0 set aside to backstop the position in case of late liquidations
    /// insurance1 The insurance in token1 set aside to backstop the position in case of late liquidations
    /// zeroForOne Whether the position is long token1 and short token0 (true) or long token0 and short token1 (false)
    /// liquidated Whether the position has been liquidated
    /// tick The pool tick prior to opening the position
    /// blockTimestamp The `block.timestamp` at which the position was last synced for funding
    /// tickCumulativeDelta The difference in the Uniswap v3 oracle tick cumulative and the Marginal v1 pool tick cumulative at the last funding sync
    /// margin The position margin in the token the owner is long
    /// liquidityLocked The liquidity locked by the pool to collateralize the position
    /// rewards The liquidation rewards in the native (gas) token received by liquidator if position becomes unsafe
    function positions(
        bytes32 key
    )
        external
        view
        returns (
            uint128 size,
            uint128 debt0,
            uint128 debt1,
            uint128 insurance0,
            uint128 insurance1,
            bool zeroForOne,
            bool liquidated,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulativeDelta,
            uint128 margin,
            uint128 liquidityLocked,
            uint256 rewards
        );

    /// @notice Opens a leverage position on the pool
    /// @dev The caller of this method receives a callback in the form of IMarginalV1OpenCallback#marginalV1OpenCallback.
    /// The caller must forward liquidation rewards in the native (gas) token to be escrowed by the pool contract
    /// Rewards determined by current `block.basefee` * estimated gas cost to call IMarginalV1Pool#liquidate * rewardPremium
    /// @param recipient The address of the owner of the opened position
    /// @param zeroForOne Whether long token1 and short token0 (true), or long token0 and short token1 (false)
    /// @param liquidityDelta The amount of liquidity for the pool to lock to capitalize the position
    /// @param sqrtPriceLimitX96 The Q64.96 sqrt price limit. If zero for one, the price cannot be less than this
    /// value after opening the position otherwise the call reverts. If one for zero, the price cannot be greater than this value after opening
    /// @param margin The amount of margin used to back the position in the token the position is long
    /// @param data Any data to be passed through to the callback
    /// @return id The ID of the opened position
    /// @return size The size of the opened position in the token the position is long. Excludes margin amount provided by caller
    /// @return debt The debt of the opened position in the token the position is short
    /// @return amount0 The amount of token0 caller must send to pool to open the position
    /// @return amount1 The amount of token1 caller must send to pool to open the position
    function open(
        address recipient,
        bool zeroForOne,
        uint128 liquidityDelta,
        uint160 sqrtPriceLimitX96,
        uint128 margin,
        bytes calldata data
    )
        external
        payable
        returns (
            uint256 id,
            uint256 size,
            uint256 debt,
            uint256 amount0,
            uint256 amount1
        );

    /// @notice Adjusts the margin used to back a position on the pool
    /// @dev The caller of this method receives a callback in the form of IMarginalV1AdjustCallback#marginalV1AdjustCallback
    /// Old position margin is flashed out to recipient prior to the callback
    /// @param recipient The address to receive the old position margin
    /// @param id The ID of the position to adjust
    /// @param marginDelta The delta of the margin backing the position on the pool. Adding margin to the position when positive, removing margin when negative
    /// @param data Any data to be passed through to the callback
    /// @return margin0 The amount of token0 to be used as the new margin backing the position
    /// @return margin1 The amount of token1 to be used as the new margin backing the position
    function adjust(
        address recipient,
        uint96 id,
        int128 marginDelta,
        bytes calldata data
    ) external returns (uint256 margin0, uint256 margin1);

    /// @notice Settles a position on the pool
    /// @dev The caller of this method receives a callback in the form of IMarginalV1SettleCallback#marginalV1SettleCallback.
    /// If a contract, `recipient` must implement a `receive()` function to receive the escrowed liquidation rewards in the native (gas) token from the pool.
    /// Position size, margin, and liquidation rewards are flashed out before the callback to allow the caller to swap to repay the debt to the pool
    /// @param recipient The address to receive the size, margin, and liquidation rewards of the settled position
    /// @param id The ID of the position to settle
    /// @param data Any data to be passed through to the callback
    /// @return amount0 The delta of the balance of token0 of the pool. Position debt into the pool (> 0) if long token1 (zeroForOne = true), or position size and margin out of the pool (< 0) if long token0 (zeroForOne = false)
    /// @return amount1 The delta of the balance of token1 of the pool. Position size and margin out of the pool (< 0) if long token1 (zeroForOne = true), or position debt into the pool (> 0) if long token0 (zeroForOne = false)
    /// @return rewards The amount of escrowed native (gas) token sent to `recipient`
    function settle(
        address recipient,
        uint96 id,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1, uint256 rewards);

    /// @notice Liquidates a position on the pool
    /// @dev Reverts if position is safe from liquidation. Position is considered safe if
    /// (`position.margin` + `position.size`) / oracleTwap >= (1 + `maintenance`) * `position.debt0` when position.zeroForOne = true
    /// (`position.margin` + `position.size`) * oracleTwap >= (1 + `maintenance`) * `position.debt1` when position.zeroForOne = false
    /// Safety checks are performed after syncing the position debts for funding payments
    /// If a contract, `recipient` must implement a `receive()` function to receive the escrowed liquidation rewards in the native (gas) token from the pool.
    /// @param recipient The address to receive liquidation rewards escrowed with the position
    /// @param owner The address of the owner of the position to liquidate
    /// @param id The ID of the position to liquidate
    /// @return rewards The amount of escrowed native (gas) token sent to `recipient`
    function liquidate(
        address recipient,
        address owner,
        uint96 id
    ) external returns (uint256 rewards);

    /// @notice Swap token0 for token1, or token1 for token0
    /// @dev The caller of this method receives a callback in the form of IMarginalV1SwapCallback#marginalV1SwapCallback
    /// @param recipient The address to receive the output of the swap
    /// @param zeroForOne The direction of the swap, true for token0 to token1, false for token1 to token0
    /// @param amountSpecified The amount of the swap, which implicitly configures the swap as exact input (positive), or exact output (negative)
    /// @param sqrtPriceLimitX96 The Q64.96 sqrt price limit. If zero for one, the price cannot be less than this
    /// value after the swap otherwise the call reverts. If one for zero, the price cannot be greater than this value after the swap
    /// @param data Any data to be passed through to the callback
    /// @return amount0 The delta of the balance of token0 of the pool, exact when negative, minimum when positive
    /// @return amount1 The delta of the balance of token1 of the pool, exact when negative, minimum when positive
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);

    /// @notice Adds liquidity to the pool
    /// @dev The caller of this method receives a callback in the form of IMarginalV1MintCallback#marginalV1MintCallback.
    /// The pool is initialized through the first call to mint
    /// @param recipient The address to mint LP tokens to after adding liquidity to the pool
    /// @param liquidityDelta The liquidity added to the pool
    /// @param data Any data to be passed through to the callback
    /// @return shares The amount of LP token shares minted to recipient
    /// @return amount0 The amount of token0 added to the pool reserves
    /// @return amount1 The amount of token1 added to the pool reserves
    function mint(
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) external returns (uint256 shares, uint256 amount0, uint256 amount1);

    /// @notice Removes liquidity from the pool
    /// @dev Reverts if not enough liquidity available to exit due to outstanding leverage positions
    /// @param recipient The address to send token amounts to after removing liquidity from the pool
    /// @param shares The amount of LP token shares to burn
    /// @return liquidityDelta The liquidity removed from the pool
    /// @return amount0 The amount of token0 removed from pool reserves
    /// @return amount1 The amount of token1 removed from pool reserves
    function burn(
        address recipient,
        uint256 shares
    )
        external
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1);
}

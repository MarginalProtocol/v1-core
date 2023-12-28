// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 settle callback
/// @notice Callbacks called by Marginal v1 pools when settling the debt owed by a position to the pool
/// @dev Any contract that calls IMarginalV1Pool#settle must implement this interface
interface IMarginalV1SettleCallback {
    /// @notice Called to `msg.sender` after settling a position via IMarginalV1Pool#settle
    /// @dev In the implementation you must pay the pool tokens owed to settle the debt owed by a position to the pool.
    /// Position size and margin are flashed out to `recipient` in the IMarginalV1Pool#settle call prior to enable debt repayment via swaps.
    /// The caller of this method must be checked to be a MarginalV1Pool deployed by the canonical MarginalV1Factory.
    /// Amount that must be payed to pool is > 0 as IMarginalV1Pool#open would have reverted otherwise.
    /// @param amount0Delta The amount of token0 that was sent (negative) or must be received (positive) by the pool by
    /// the end of position settlement. If positive, the callback must send that amount of token0 to the pool.
    /// @param amount1Delta The amount of token1 that was sent (negative) or must be received (positive) by the pool by
    /// the end of position settlement. If positive, the callback must send that amount of token1 to the pool.
    /// @param data Any data passed through by the caller via the IMarginalV1Pool#settle call
    function marginalV1SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external;
}

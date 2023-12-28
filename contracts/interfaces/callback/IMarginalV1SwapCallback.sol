// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 swap callback
/// @notice Callbacks called by Marginal v1 pools when executing a swap
/// @dev Any contract that calls IMarginalV1Pool#swap must implement this interface
interface IMarginalV1SwapCallback {
    /// @notice Called to `msg.sender` after executing a swap via IMarginalV1Pool#swap
    /// @dev In the implementation you must pay the pool tokens owed for the swap.
    /// The caller of this method must be checked to be a MarginalV1Pool deployed by the canonical MarginalV1Factory.
    /// Amount that must be payed to pool is > 0 as IMarginalV1Pool#swap reverts otherwise.
    /// @param amount0Delta The amount of token0 that was sent (negative) or must be received (positive) by the pool by
    /// the end of the swap. If positive, the callback must send that amount of token0 to the pool.
    /// @param amount1Delta The amount of token1 that was sent (negative) or must be received (positive) by the pool by
    /// the end of the swap. If positive, the callback must send that amount of token1 to the pool.
    /// @param data Any data passed through by the caller via the IMarginalV1Pool#swap call
    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external;
}

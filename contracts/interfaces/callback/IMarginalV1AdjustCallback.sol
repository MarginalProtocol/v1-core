// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 adjust callback
/// @notice Callbacks called by Marginal v1 pools when adjusting the margin backing a position
/// @dev Any contract that calls IMarginalV1Pool#adjust must implement this interface
interface IMarginalV1AdjustCallback {
    /// @notice Called to `msg.sender` after adjusting the margin backing a position via IMarginalV1Pool#adjust
    /// @dev In the implementation you must pay the pool tokens owed to adjust the margin backing a position. The tokens owed
    /// is the new position margin, as the original margin is flashed out to `recipient` in the IMarginalV1Pool#adjust call.
    /// The caller of this method must be checked to be a MarginalV1Pool deployed by the canonical MarginalV1Factory.
    /// @param amount0Owed The amount of token0 that must be payed to pool to successfully adjust the margin backing a position
    /// @param amount1Owed The amount of token1 that must be payed to pool to successfully adjust the margin backing a position
    /// @param data Any data passed through by the caller via the IMarginalV1Pool#adjust call
    function marginalV1AdjustCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external;
}

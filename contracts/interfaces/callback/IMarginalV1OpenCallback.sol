// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 open callback
/// @notice Callbacks called by Marginal v1 pools when opening a position
/// @dev Any contract that calls IMarginalV1Pool#open must implement this interface
interface IMarginalV1OpenCallback {
    /// @notice Called to `msg.sender` after opening a position via IMarginalV1Pool#open
    /// @dev In the implementation you must pay the pool tokens owed to open a position.
    /// The pool tokens owed are the margin and fees required to open the position.
    /// The caller of this method must be checked to be a MarginalV1Pool deployed by the canonical MarginalV1Factory.
    /// @param amount0Owed The amount of token0 that must be payed to pool to successfully open a position
    /// @param amount1Owed The amount of token1 that must be payed to pool to successfully open a position
    /// @param data Any data passed through by the caller via the IMarginalV1Pool#open call
    function marginalV1OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external;
}

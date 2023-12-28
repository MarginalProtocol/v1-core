// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 mint callback
/// @notice Callbacks called by Marginal v1 pools when adding liquidity
/// @dev Any contract that calls IMarginalV1Pool#mint must implement this interface
interface IMarginalV1MintCallback {
    /// @notice Called to `msg.sender` after adding liquidity via IMarginalV1Pool#mint
    /// @dev In the implementation you must pay the pool tokens owed to add liquidity to the pool and mint LP tokens.
    /// The caller of this method must be checked to be a MarginalV1Pool deployed by the canonical MarginalV1Factory.
    /// @param amount0Owed The amount of token0 that must be payed to pool to successfully mint LP tokens
    /// @param amount1Owed The amount of token1 that must be payed to pool to successfully mint LP tokens
    /// @param data Any data passed through by the caller via the IMarginalV1Pool#mint call
    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external;
}

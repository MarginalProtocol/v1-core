// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 pool deployer
/// @notice The Marginal v1 pool deployer deploys new pools
interface IMarginalV1PoolDeployer {
    /// @notice Deploys a new Marginal v1 pool for the given unique pool key
    /// @dev `msg.sender` treated as factory address for the pool
    /// @param token0 The address of token0 for the pool
    /// @param token1 The address of token1 for the pool
    /// @param maintenance The minimum maintenance requirement for the pool
    /// @param oracle The address of the Uniswap v3 oracle used by the pool
    /// @return pool The address of the deployed Marginal v1 pool
    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) external returns (address pool);
}

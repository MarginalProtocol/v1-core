// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 factory
/// @notice The Marginal v1 factory creates pools and enables leverage tiers
interface IMarginalV1Factory {
    /// @notice Returns the Marginal v1 pool deployer to use when creating pools
    /// @return The address of the Marginal v1 pool deployer
    function marginalV1Deployer() external view returns (address);

    /// @notice Returns the Uniswap v3 factory to reference for pool oracles
    /// @return The address of the Uniswap v3 factory
    function uniswapV3Factory() external view returns (address);

    /// @notice Returns the minimum observation cardinality the Uniswap v3 oracle must have
    /// @dev Used as a check that averaging over `secondsAgo` in the Marginal v1 pool is likely to succeed
    /// @return The minimum observation cardinality the Uniswap v3 oracle must have
    function observationCardinalityMinimum() external view returns (uint16);

    /// @notice Returns the current owner of the Marginal v1 factory contract
    /// @dev Changed via permissioned `setOwner` function on the factory
    /// @return The address of the current owner of the Marginal v1 factory
    function owner() external view returns (address);

    /// @notice Returns the pool address for the given unique Marginal v1 pool key
    /// @dev tokenA and tokenB may be passed in either token0/token1 or token1/token0 order
    /// @param tokenA The address of either token0/token1
    /// @param tokenB The address of the other token token1/token0
    /// @param maintenance The minimum maintenance requirement for the pool
    /// @param oracle The address of the Uniswap v3 oracle used by the pool
    /// @return The address of the Marginal v1 pool
    function getPool(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle
    ) external view returns (address);

    /// @notice Returns whether given address is a Marginal v1 pool deployed by the factory
    /// @return Whether address is a pool
    function isPool(address pool) external view returns (bool);

    /// @notice Returns the maximum leverage associated with the pool maintenance if pool exists
    /// @param maintenance The minimum maintenance margin requirement for the pool
    /// @return The maximum leverage for the pool maintenance if pool exists
    function getLeverage(uint24 maintenance) external view returns (uint256);

    /// @notice Creates a new Marginal v1 pool for the given unique pool key
    /// @dev tokenA and tokenB may be passed in either token0/token1 or token1/token0 order
    /// @param tokenA The address of either token0/token1
    /// @param tokenB The address of the other token token1/token0
    /// @param maintenance The minimum maintenance requirement for the pool
    /// @param uniswapV3Fee The fee tier of the Uniswap v3 oracle used by the Marginal v1 pool
    /// @return pool The address of the created Marginal v1 pool
    function createPool(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        uint24 uniswapV3Fee
    ) external returns (address pool);

    /// @notice Sets the owner of the Marginal v1 factory contract
    /// @dev Can only be called by the current factory owner
    /// @param _owner The new owner of the factory
    function setOwner(address _owner) external;

    /// @notice Enables a new leverage tier for Marginal v1 pool deployments
    /// @dev Can only be called by the current factory owner
    /// @dev Set leverage tier obeys: l = 1 + 1/M; M = maintenance
    /// @param maintenance The minimum maintenance requirement associated with the leverage tier
    function enableLeverage(uint24 maintenance) external;
}

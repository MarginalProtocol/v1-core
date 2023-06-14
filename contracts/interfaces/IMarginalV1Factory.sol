// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity >=0.5.0;

interface IMarginalV1Factory {
    function marginalV1Deployer() external view returns (address);

    function uniswapV3Factory() external view returns (address);

    function observationCardinalityMinimum() external view returns (uint16);

    function owner() external view returns (address);

    function getPool(
        address tokenA,
        address tokenB,
        uint24 maintenance
    ) external view returns (address);

    function getLeverage(uint24 maintenance) external view returns (uint256);

    function createPool(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        uint24 uniswapV3Fee
    ) external returns (address pool);
}

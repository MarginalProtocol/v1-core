// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1Factory {
    function uniswapV3Factory() external view returns (address);

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

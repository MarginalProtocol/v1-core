// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1Factory {
    function getPool(
        address tokenA,
        address tokenB,
        uint256 maintenance
    ) external view returns (address);

    function getLeverage(uint256 maintenance) external view returns (uint256);

    function params()
        external
        view
        returns (address token0, address token1, uint256 maintenance);
}

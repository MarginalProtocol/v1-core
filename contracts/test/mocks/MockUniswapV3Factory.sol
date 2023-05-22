// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

contract MockUniswapV3Factory {
    mapping(address => mapping(address => mapping(uint24 => address)))
        public getPool;

    function setPool(
        address tokenA,
        address tokenB,
        uint24 fee,
        address pool
    ) external {
        getPool[tokenA][tokenB][fee] = pool;
        getPool[tokenB][tokenA][fee] = pool;
    }
}

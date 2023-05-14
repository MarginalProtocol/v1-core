// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {MarginalV1Pool} from "./MarginalV1Pool.sol";

contract MarginalV1Factory {
    mapping(address => mapping(address => mapping(uint256 => address)))
        public getPool;
    mapping(uint256 => uint256) public getLeverage;

    event PoolCreated(
        address token0,
        address token1,
        uint256 maintenance,
        address pool
    );
    event LeverageEnabled(uint256 maintenance, uint256 leverage);

    constructor() {
        getLeverage[2500] = 50000; // precision of 1e4
        emit LeverageEnabled(2500, 50000);
        getLeverage[5000] = 30000;
        emit LeverageEnabled(5000, 30000);
        getLeverage[10000] = 20000;
        emit LeverageEnabled(10000, 20000);
    }

    function createPool(
        address tokenA,
        address tokenB,
        uint256 maintenance
    ) external returns (address poolAddress) {
        require(tokenA != tokenB, "A == B");
        (address token0, address token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        require(token0 != address(0), "token0 == address(0)");
        require(getLeverage[maintenance] > 0, "leverage not enabled");

        MarginalV1Pool pool = new MarginalV1Pool{
            salt: keccak256(abi.encode(token0, token1, maintenance))
        }();
        pool.initialize(token0, token1, maintenance);

        // populate in reverse for key (token0, token1, maintenance)
        poolAddress = address(pool);
        getPool[token0][token1][maintenance] = poolAddress;
        getPool[token1][token0][maintenance] = poolAddress;

        emit PoolCreated(token0, token1, maintenance, poolAddress);
    }
}

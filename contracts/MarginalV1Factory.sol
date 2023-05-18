// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {MarginalV1Pool} from "./MarginalV1Pool.sol";

contract MarginalV1Factory {
    mapping(address => mapping(address => mapping(uint24 => address)))
        public getPool;
    mapping(uint24 => uint256) public getLeverage;

    struct Params {
        address token0;
        address token1;
        uint24 maintenance; // precision of 1e6
        uint24 fee; // precision of 1e6
    }
    Params public params;

    event PoolCreated(
        address token0,
        address token1,
        uint24 maintenance,
        address pool
    );
    event LeverageEnabled(uint24 maintenance, uint256 leverage);

    constructor() {
        getLeverage[250000] = 5000000;
        emit LeverageEnabled(250000, 5000000);
        getLeverage[500000] = 3000000;
        emit LeverageEnabled(500000, 3000000);
        getLeverage[1000000] = 2000000;
        emit LeverageEnabled(1000000, 2000000);
    }

    // TODO: fee input param to choose which uni pool to use for twap oracle
    function createPool(
        address tokenA,
        address tokenB,
        uint24 maintenance
    ) external returns (address pool) {
        require(tokenA != tokenB, "A == B");
        (address token0, address token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        require(token0 != address(0), "token0 == address(0)");
        require(getLeverage[maintenance] > 0, "leverage not enabled");

        params = Params({
            token0: token0,
            token1: token1,
            maintenance: maintenance, // different max leverages across pools
            fee: 1000 // 10 bps across all pools
        });
        pool = address(
            new MarginalV1Pool{
                salt: keccak256(abi.encode(token0, token1, maintenance))
            }()
        );
        delete params;

        // populate in reverse for key (token0, token1, maintenance)
        getPool[token0][token1][maintenance] = pool;
        getPool[token1][token0][maintenance] = pool;

        emit PoolCreated(token0, token1, maintenance, pool);
    }
}

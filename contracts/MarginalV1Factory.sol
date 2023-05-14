// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {MarginalV1Pool} from "./MarginalV1Pool.sol";

contract MarginalV1Factory {
    mapping(address => mapping(address => mapping(uint256 => address))) getPool;

    event PoolCreated(
        address token0,
        address token1,
        uint256 maintenance,
        address pool
    );

    constructor() {}

    function createPool(
        address tokenA,
        address tokenB,
        uint256 maintenance // TODO: smaller type
    ) external returns (address pool) {
        require(tokenA != tokenB, "A == B");
        (address token0, address token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        require(token0 != address(0));

        pool = address(
            new MarginalV1Pool{
                salt: keccak256(abi.encode(token0, token1, maintenance))
            }()
        );

        // populate in reverse for key (token0, token1, maintenance)
        getPool[token0][token1][maintenance] = pool;
        getPool[token1][token0][maintenance] = pool;

        emit PoolCreated(token0, token1, maintenance, pool);
    }
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";

import {IMarginalV1Factory} from "./interfaces/IMarginalV1Factory.sol";
import {MarginalV1Pool} from "./MarginalV1Pool.sol";

contract MarginalV1Factory is IMarginalV1Factory {
    address public immutable uniswapV3Factory;

    mapping(address => mapping(address => mapping(uint24 => address)))
        public getPool;
    mapping(uint24 => uint256) public getLeverage;

    struct Params {
        address token0;
        address token1;
        uint24 maintenance; // precision of 1e6
        uint24 fee; // precision of 1e6
        uint24 reward; // precision of 1e6
        address oracle;
        uint32 secondsAgo;
        uint32 fundingPeriod;
    }
    Params public params;

    event PoolCreated(
        address token0,
        address token1,
        uint24 maintenance,
        address pool
    );
    event LeverageEnabled(uint24 maintenance, uint256 leverage);

    constructor(address _uniswapV3Factory) {
        uniswapV3Factory = _uniswapV3Factory;

        getLeverage[250000] = 5000000;
        emit LeverageEnabled(250000, 5000000);
        getLeverage[500000] = 3000000;
        emit LeverageEnabled(500000, 3000000);
        getLeverage[1000000] = 2000000;
        emit LeverageEnabled(1000000, 2000000);
    }

    function createPool(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        uint24 uniswapV3Fee
    ) external returns (address pool) {
        require(tokenA != tokenB, "A == B");
        (address token0, address token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        require(token0 != address(0), "token0 == address(0)");
        require(getLeverage[maintenance] > 0, "leverage not enabled");

        address oracle = IUniswapV3Factory(uniswapV3Factory).getPool(
            token0,
            token1,
            uniswapV3Fee
        );
        require(oracle != address(0), "not Uniswap pool");

        params = Params({
            token0: token0,
            token1: token1,
            maintenance: maintenance, // different max leverages across pools
            fee: 1000, // 10 bps across all pools
            reward: 100000, // 10% of margin remaining on liquidation
            oracle: oracle,
            secondsAgo: 3600, // 1 hr TWAP for oracle price
            fundingPeriod: 86400 // 1 day
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

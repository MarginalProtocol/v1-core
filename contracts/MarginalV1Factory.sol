// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {IMarginalV1Factory} from "./interfaces/IMarginalV1Factory.sol";
import {IMarginalV1PoolDeployer} from "./interfaces/IMarginalV1PoolDeployer.sol";

contract MarginalV1Factory is IMarginalV1Factory {
    address public immutable marginalV1Deployer;
    address public immutable uniswapV3Factory;
    uint16 public immutable observationCardinalityMinimum;

    address public owner;

    mapping(address => mapping(address => mapping(uint24 => address)))
        public getPool;
    mapping(uint24 => uint256) public getLeverage;

    event PoolCreated(
        address token0,
        address token1,
        uint24 maintenance,
        address pool
    );
    event LeverageEnabled(uint24 maintenance, uint256 leverage);
    event OwnerChanged(address indexed oldOwner, address indexed newOwner);

    constructor(
        address _marginalV1Deployer,
        address _uniswapV3Factory,
        uint16 _observationCardinalityMinimum
    ) {
        owner = msg.sender;
        emit OwnerChanged(address(0), msg.sender);

        marginalV1Deployer = _marginalV1Deployer;
        uniswapV3Factory = _uniswapV3Factory;
        observationCardinalityMinimum = _observationCardinalityMinimum;

        getLeverage[250000] = 4333333; // includes liq reward req
        emit LeverageEnabled(250000, 4333333);
        getLeverage[500000] = 2818181;
        emit LeverageEnabled(500000, 2818181);
        getLeverage[1000000] = 1952380;
        emit LeverageEnabled(1000000, 1952380);
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

        (, , , uint16 observationCardinality, , , ) = IUniswapV3Pool(oracle)
            .slot0();
        require(
            observationCardinality >= observationCardinalityMinimum,
            "observationCardinality < observationCardinalityMinimum"
        );

        pool = IMarginalV1PoolDeployer(marginalV1Deployer).deploy(
            token0,
            token1,
            maintenance,
            oracle
        );

        // populate in reverse for key (token0, token1, maintenance)
        getPool[token0][token1][maintenance] = pool;
        getPool[token1][token0][maintenance] = pool;

        emit PoolCreated(token0, token1, maintenance, pool);
    }

    function setOwner(address _owner) external {
        require(msg.sender == owner, "not owner");
        emit OwnerChanged(owner, _owner);
        owner = _owner;
    }

    // TODO: test
    function enableLeverage(uint24 maintenance) external {
        require(msg.sender == owner, "not owner");
        require(
            maintenance >= 100000 && maintenance < 1000000,
            "maintenance exceeds min/max"
        );
        require(getLeverage[maintenance] == 0, "leverage enabled");

        // l = 1 + 1 / (M + reward)
        uint256 leverage = 1e6 + 1e12 / (uint256(maintenance) + 5e4);
        getLeverage[maintenance] = leverage;

        emit LeverageEnabled(maintenance, leverage);
    }
}

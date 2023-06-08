// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {IMarginalV1PoolDeployer} from "./interfaces/IMarginalV1PoolDeployer.sol";
import {MarginalV1Pool} from "./MarginalV1Pool.sol";

contract MarginalV1PoolDeployer is IMarginalV1PoolDeployer {
    struct Params {
        address factory;
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

    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 fee,
        uint24 reward,
        address oracle,
        uint32 secondsAgo,
        uint32 fundingPeriod
    ) external returns (address pool) {
        params = Params({
            factory: msg.sender,
            token0: token0,
            token1: token1,
            maintenance: maintenance,
            fee: fee,
            reward: reward,
            oracle: oracle,
            secondsAgo: secondsAgo,
            fundingPeriod: fundingPeriod
        });
        pool = address(
            new MarginalV1Pool{
                salt: keccak256(
                    abi.encode(msg.sender, token0, token1, maintenance)
                )
            }()
        );
        delete params;
    }
}

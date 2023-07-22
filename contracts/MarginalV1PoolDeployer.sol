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
        address oracle;
    }
    Params public params;

    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) external returns (address pool) {
        params = Params({
            factory: msg.sender,
            token0: token0,
            token1: token1,
            maintenance: maintenance,
            oracle: oracle
        });
        pool = address(
            new MarginalV1Pool{
                salt: keccak256(
                    abi.encode(msg.sender, token0, token1, maintenance, oracle)
                )
            }()
        );
        delete params;
    }
}

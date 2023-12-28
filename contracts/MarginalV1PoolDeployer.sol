// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IMarginalV1PoolDeployer} from "./interfaces/IMarginalV1PoolDeployer.sol";
import {MarginalV1Pool} from "./MarginalV1Pool.sol";

contract MarginalV1PoolDeployer is IMarginalV1PoolDeployer {
    /// @inheritdoc IMarginalV1PoolDeployer
    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) external returns (address pool) {
        pool = address(
            new MarginalV1Pool{
                salt: keccak256(
                    abi.encode(msg.sender, token0, token1, maintenance, oracle)
                )
            }(msg.sender, token0, token1, maintenance, oracle)
        );
    }
}

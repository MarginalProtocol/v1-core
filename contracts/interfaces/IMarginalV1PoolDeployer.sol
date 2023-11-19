// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

interface IMarginalV1PoolDeployer {
    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) external returns (address pool);
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity >=0.5.0;

interface IMarginalV1PoolDeployer {
    function params()
        external
        view
        returns (
            address factory,
            address token0,
            address token1,
            uint24 maintenance,
            address oracle
        );

    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) external returns (address pool);
}

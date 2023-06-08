// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1PoolDeployer {
    function params()
        external
        view
        returns (
            address factory,
            address token0,
            address token1,
            uint24 maintenance,
            uint24 fee,
            uint24 reward,
            address oracle,
            uint32 secondsAgo,
            uint32 fundingPeriod
        );

    function deploy(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 fee,
        uint24 reward,
        address oracle,
        uint32 secondsAgo,
        uint32 fundingPeriod
    ) external returns (address pool);
}

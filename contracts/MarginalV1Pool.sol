// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

contract MarginalV1Pool {
    address public immutable factory;

    address public token0;
    address public token1;
    uint256 public maintenance;

    constructor() {
        factory = msg.sender;
    }

    function initialize(
        address _token0,
        address _token1,
        uint256 _maintenance
    ) external {
        require(msg.sender == factory, "not factory");
        token0 = _token0;
        token1 = _token1;
        maintenance = _maintenance;
    }
}

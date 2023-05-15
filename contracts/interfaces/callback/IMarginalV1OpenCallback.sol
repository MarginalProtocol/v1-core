// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1OpenCallback {
    function marginalV1OpenCallback(
        uint256 margin0Minimum,
        uint256 margin1Minimum
    ) external;
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1AdjustCallback {
    function marginalV1AdjustCallback(
        uint256 margin0Out,
        uint256 margin1Out,
        uint256 margin0AdjustMinimum,
        uint256 margin1AdjustMinimum,
        bytes calldata data
    ) external;
}

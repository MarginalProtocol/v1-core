// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1AdjustCallback {
    function marginalV1AdjustCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external;
}

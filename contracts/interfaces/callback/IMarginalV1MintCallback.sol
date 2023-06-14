// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity >=0.5.0;

interface IMarginalV1MintCallback {
    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external;
}

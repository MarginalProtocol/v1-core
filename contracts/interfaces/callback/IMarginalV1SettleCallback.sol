// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

interface IMarginalV1SettleCallback {
    function marginalV1SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external;
}

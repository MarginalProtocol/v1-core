// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

interface IMarginalV1SwapCallback {
    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external;
}

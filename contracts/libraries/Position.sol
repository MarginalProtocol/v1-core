// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

library Position {
    struct Info {
        uint256 liquidity;
        uint256 sqrtPrice;
        uint256 fundingIndex;
        uint256 liquidityDelta;
        bool zeroForOne;
        uint256 margin;
    }

    // TODO: implement
    function sqrtPriceNext(
        Info memory position,
        uint256 maintenance
    ) internal view returns (uint256) {
        return 0;
    }

    // TODO: implement
    function marginMinimum(
        Info memory position,
        uint256 maintenance
    ) internal view returns (uint256) {
        return 0;
    }
}

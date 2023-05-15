// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

library Position {
    struct Info {
        uint256 sqrtPriceBefore;
        uint256 sqrtPriceAfter;
        uint256 fundingIndexBefore;
        uint256 liquidityDelta;
        bool zeroForOne;
        uint256 margin;
    }

    // TODO: implement
    function marginMinimum(
        Info memory position,
        uint256 maintenance
    ) internal view returns (uint256) {
        return 0;
    }
}

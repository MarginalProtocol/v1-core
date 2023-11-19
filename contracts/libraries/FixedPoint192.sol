// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.4.0;

library FixedPoint192 {
    uint8 internal constant RESOLUTION = 192;
    uint256 internal constant Q192 =
        0x1000000000000000000000000000000000000000000000000;
}

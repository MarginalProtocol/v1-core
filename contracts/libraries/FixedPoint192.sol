// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

library FixedPoint192 {
    uint8 internal constant RESOLUTION = 192;
    uint256 internal constant Q192 =
        0x1000000000000000000000000000000000000000000000000;
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

// TODO: test
library FixedPoint64 {
    uint8 internal constant RESOLUTION = 64;
    uint256 internal constant Q64 = 0x10000000000000000;
}

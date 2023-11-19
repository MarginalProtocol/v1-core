// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.4.0;

library FixedPoint64 {
    uint8 internal constant RESOLUTION = 64;
    uint256 internal constant Q64 = 0x10000000000000000;
}

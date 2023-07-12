// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity >=0.4.0;

library FixedPoint128 {
    uint8 internal constant RESOLUTION = 128;
    uint256 internal constant Q128 = 0x100000000000000000000000000000000;
}

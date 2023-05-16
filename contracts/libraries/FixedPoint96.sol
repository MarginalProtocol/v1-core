// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

library FixedPoint96 {
    uint8 internal constant RESOLUTION = 96;
    uint256 internal constant Q96 = 0x1000000000000000000000000;
}

// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.4.0;

/// @title FixedPoint64
/// @notice A library for handling binary fixed point numbers, see https://en.wikipedia.org/wiki/Q_(number_format)
library FixedPoint64 {
    uint8 internal constant RESOLUTION = 64;
    uint256 internal constant Q64 = 0x10000000000000000;
}

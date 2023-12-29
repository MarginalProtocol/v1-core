// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.4.0;

/// @title FixedPoint128
/// @notice A library for handling binary fixed point numbers, see https://en.wikipedia.org/wiki/Q_(number_format)
library FixedPoint128 {
    uint8 internal constant RESOLUTION = 128;
    uint256 internal constant Q128 = 0x100000000000000000000000000000000;
}

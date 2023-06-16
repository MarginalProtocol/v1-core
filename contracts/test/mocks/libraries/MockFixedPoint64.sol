// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {FixedPoint64} from "../../../libraries/FixedPoint64.sol";

contract MockFixedPoint64 {
    function Q64() external view returns (uint256) {
        return FixedPoint64.Q64;
    }

    function RESOLUTION() external view returns (uint8) {
        return FixedPoint64.RESOLUTION;
    }
}

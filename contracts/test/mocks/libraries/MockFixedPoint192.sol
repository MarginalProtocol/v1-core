// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {FixedPoint192} from "../../../libraries/FixedPoint192.sol";

contract MockFixedPoint192 {
    function Q192() external view returns (uint256) {
        return FixedPoint192.Q192;
    }

    function RESOLUTION() external view returns (uint8) {
        return FixedPoint192.RESOLUTION;
    }
}

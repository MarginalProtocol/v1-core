// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {FixedPoint96} from "../../../libraries/FixedPoint96.sol";

contract MockFixedPoint96 {
    function Q96() external view returns (uint256) {
        return FixedPoint96.Q96;
    }

    function RESOLUTION() external view returns (uint8) {
        return FixedPoint96.RESOLUTION;
    }
}

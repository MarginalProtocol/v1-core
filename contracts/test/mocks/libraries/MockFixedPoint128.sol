// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {FixedPoint128} from "../../../libraries/FixedPoint128.sol";

contract MockFixedPoint128 {
    function Q128() external view returns (uint256) {
        return FixedPoint128.Q128;
    }

    function RESOLUTION() external view returns (uint8) {
        return FixedPoint128.RESOLUTION;
    }
}

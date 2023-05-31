// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {OracleLibrary} from "../../../libraries/OracleLibrary.sol";

contract MockOracleLibrary {
    function oracleSqrtPriceX96(
        int56 tickCumulativeStart,
        int56 tickCumulativeEnd,
        uint32 timeDelta
    ) external pure returns (uint160) {
        return
            OracleLibrary.oracleSqrtPriceX96(
                tickCumulativeStart,
                tickCumulativeEnd,
                timeDelta
            );
    }
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

library OracleLibrary {
    /// @dev Rounds toward zero for both positive and negative tick delta
    // TODO: retest
    function oracleSqrtPriceX96(
        int56 tickCumulativeDelta,
        uint32 timeDelta
    ) internal pure returns (uint160) {
        // @uniswap/v3-periphery/contracts/libraries/OracleLibrary.sol#L35
        // TODO: need round to negative infinity? was causing rounding issues
        // TODO: issues casting?
        int24 arithmeticMeanTick = int24(
            tickCumulativeDelta / int56(uint56(timeDelta))
        );
        return TickMath.getSqrtRatioAtTick(arithmeticMeanTick);
    }

    // TODO: test
    function oracleTickCumulativeDelta(
        int56 tickCumulativeStart,
        int56 tickCumulativeEnd
    ) internal pure returns (int56) {
        // TODO: unchecked ok? should be
        unchecked {
            return tickCumulativeEnd - tickCumulativeStart;
        }
    }
}

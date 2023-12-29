// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

/// @title Oracle library
/// @notice Enables calculation of the geometric time weighted average price
library OracleLibrary {
    /// @notice Returns the geometric time weighted average sqrtP
    /// @dev Rounds toward zero for both positive and negative tick delta
    /// @param tickCumulativeDelta The delta in tick cumulative over the averaging interval
    /// @param timeDelta The time to average over
    /// @return The geometric time weighted average price
    function oracleSqrtPriceX96(
        int56 tickCumulativeDelta,
        uint32 timeDelta
    ) internal pure returns (uint160) {
        // @uniswap/v3-periphery/contracts/libraries/OracleLibrary.sol#L35
        int24 arithmeticMeanTick = int24(
            tickCumulativeDelta / int56(uint56(timeDelta))
        );
        return TickMath.getSqrtRatioAtTick(arithmeticMeanTick);
    }

    /// @notice Returns the tick cumulative delta over an interval
    /// @dev Allows for tick cumulative overflow
    /// @param tickCumulativeStart The tick cumulative value at the start of the interval
    /// @param tickCumulativeEnd The tick cumulative value at the end of the interval
    /// @return The delta in tick cumulative over the averaging interval
    function oracleTickCumulativeDelta(
        int56 tickCumulativeStart,
        int56 tickCumulativeEnd
    ) internal pure returns (int56) {
        unchecked {
            return tickCumulativeEnd - tickCumulativeStart;
        }
    }
}

// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {FixedPoint64} from "./FixedPoint64.sol";
import {FixedPoint96} from "./FixedPoint96.sol";
import {FixedPoint128} from "./FixedPoint128.sol";
import {FixedPoint192} from "./FixedPoint192.sol";

import {OracleLibrary} from "./OracleLibrary.sol";

/// @title Position library
/// @notice Facilitates calculations, updates, and retrieval of leverage position info
/// @dev Positions are represented in (x, y) space
library Position {
    using SafeCast for uint256;

    // info stored for each trader's leverage position
    struct Info {
        // size of position in token1 if zeroForOne = true or token0 if zeroForOne = false
        uint128 size;
        // debt owed by trader at settlement if zeroForOne = true, otherwise used for internal accounting only
        uint128 debt0;
        // debt owed by trader at settlement if zeroForOne = false, otherwise used for internal accounting only
        uint128 debt1;
        // insurance balances set aside by LPs to prevent liquidity shortfall in case of late liquidation
        uint128 insurance0;
        uint128 insurance1;
        // whether the position is long token1 and short token0 (true), or long token0 and short token1 (false)
        bool zeroForOne;
        // whether the position has been liquidated
        bool liquidated;
        // tick before position was opened, used in maintenance margin requirements
        int24 tick;
        // timestamp when position was last synced for funding payments
        uint32 blockTimestamp;
        // delta between oracle and pool tick cumulatives at last funding sync (bar{a}_t - a_t)
        int56 tickCumulativeDelta;
        // margin backing position in token1 if zeroForOne = true or token0 if zeroForOne = false
        uint128 margin;
        // liquidity locked by LPs to collateralize the position. liability owed to pool
        uint128 liquidityLocked;
        // liquidation rewards escrowed with position in the native (gas) token to incentivize liquidations
        uint256 rewards;
    }

    /// @notice Gets a position from positions mapping
    /// @param positions The pool mapping that stores the leverage positions
    /// @param owner The owner of the position
    /// @param id The ID of the position
    /// @return The position info associated with the (owner, ID) key
    function get(
        mapping(bytes32 => Info) storage positions,
        address owner,
        uint96 id
    ) internal view returns (Info memory) {
        return positions[keccak256(abi.encodePacked(owner, id))];
    }

    /// @notice Stores the given position in positions mapping
    /// @dev Used to create a new position or to update existing positions
    /// @param positions The pool mapping that stores the leverage positions
    /// @param owner The owner of the position
    /// @param id The ID of the position
    /// @param position The position information to store
    function set(
        mapping(bytes32 => Info) storage positions,
        address owner,
        uint96 id,
        Info memory position
    ) internal {
        positions[keccak256(abi.encodePacked(owner, id))] = position;
    }

    /// @notice Realizes funding payments via updates to position debt amounts
    /// @param position The position to sync
    /// @param blockTimestampLast The latest `block.timestamp` to sync to
    /// @param tickCumulativeLast The `tickCumulative` from the pool at `blockTimestampLast`
    /// @param oracleTickCumulativeLast The `tickCumulative` from the oracle at `blockTimestampLast`
    /// @param tickCumulativeRateMax The maximum rate of change in tick cumulative between the oracle and pool `tickCumulative` values
    /// @param fundingPeriod The pool funding period to benchmark funding payments to
    /// @return The synced position
    function sync(
        Info memory position,
        uint32 blockTimestampLast,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast,
        uint24 tickCumulativeRateMax,
        uint32 fundingPeriod
    ) internal pure returns (Info memory) {
        // early exit if nothing to update
        if (blockTimestampLast == position.blockTimestamp) return position;

        // oracle tick - marginal tick (bar{a}_t - a_t)
        int56 tickCumulativeDeltaLast = OracleLibrary.oracleTickCumulativeDelta(
            tickCumulativeLast,
            oracleTickCumulativeLast
        );
        (uint128 debt0, uint128 debt1) = debtsAfterFunding(
            position,
            blockTimestampLast,
            tickCumulativeDeltaLast,
            tickCumulativeRateMax,
            fundingPeriod
        );

        position.debt0 = debt0;
        position.debt1 = debt1;
        position.blockTimestamp = blockTimestampLast;
        position.tickCumulativeDelta = tickCumulativeDeltaLast;
        return position;
    }

    /// @notice Liquidates an existing position
    /// @param position The position to liquidate
    /// @return positionAfter The liquidated position info
    function liquidate(
        Info memory position
    ) internal pure returns (Info memory positionAfter) {
        positionAfter.zeroForOne = position.zeroForOne;
        positionAfter.liquidated = true;
        positionAfter.tick = position.tick;
        positionAfter.blockTimestamp = position.blockTimestamp;
        positionAfter.tickCumulativeDelta = position.tickCumulativeDelta;
    }

    /// @notice Settles existing position
    /// @param position The position to settle
    /// @return positionAfter The settled position info
    function settle(
        Info memory position
    ) internal pure returns (Info memory positionAfter) {
        positionAfter.zeroForOne = position.zeroForOne;
        positionAfter.liquidated = position.liquidated;
        positionAfter.tick = position.tick;
        positionAfter.blockTimestamp = position.blockTimestamp;
        positionAfter.tickCumulativeDelta = position.tickCumulativeDelta;
    }

    /// @notice Assembles a new position from pool state
    /// @dev zeroForOne = true means short position (long token1, short token0)
    /// @param liquidity The pool liquidity before opening the position
    /// @param sqrtPriceX96 The pool sqrt price before opening the position
    /// @param sqrtPriceX96Next The pool sqrt price after opening the position
    /// @param liquidityDelta The delta in pool liquidity used to collateralize the position
    /// @param zeroForOne Whether the position is long token1 and short token0 (true), or long token0 and short token1 (false)
    /// @param tick The pool tick before opening the position
    /// @param blockTimestampStart The timestamp at which the pool state was last synced before opening the position
    /// @param tickCumulativeStart The tick cumulative value from the pool at `blockTimestampStart`
    /// @param oracleTickCumulativeStart The tick cumulative value from the oracle at `blockTimestampStart`
    /// @return position The assembled position info
    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne,
        int24 tick,
        uint32 blockTimestampStart,
        int56 tickCumulativeStart,
        int56 oracleTickCumulativeStart
    ) internal pure returns (Info memory position) {
        position.zeroForOne = zeroForOne;
        position.tick = tick;
        position.blockTimestamp = blockTimestampStart;
        position.tickCumulativeDelta =
            oracleTickCumulativeStart -
            tickCumulativeStart;
        position.liquidityLocked = liquidityDelta;

        position.size = size(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            zeroForOne
        );
        (position.insurance0, position.insurance1) = insurances(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne
        );
        (position.debt0, position.debt1) = debts(
            sqrtPriceX96Next,
            liquidityDelta,
            position.insurance0,
            position.insurance1
        );
    }

    /// @notice Size of position in (x, y) amounts
    /// @dev Size amount in token1 if zeroForOne = true, or in token0 if zeroForOne = false
    /// @param liquidity The pool liquidity before opening the position
    /// @param sqrtPriceX96 The pool sqrt price before opening the position
    /// @param sqrtPriceX96Next The pool sqrt price after opening the position
    /// @param zeroForOne Whether the position is long token1 and short token0 (true), or long token0 and short token1 (false)
    /// @return The position size
    function size(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        bool zeroForOne
    ) internal pure returns (uint128) {
        if (!zeroForOne) {
            // L / sqrt(P) - L / sqrt(P')
            return
                ((uint256(liquidity) << FixedPoint96.RESOLUTION) /
                    sqrtPriceX96 -
                    (uint256(liquidity) << FixedPoint96.RESOLUTION) /
                    sqrtPriceX96Next).toUint128();
        } else {
            // L * sqrt(P) - L * sqrt(P')
            return
                (
                    Math.mulDiv(
                        liquidity,
                        sqrtPriceX96 - sqrtPriceX96Next,
                        FixedPoint96.Q96
                    )
                ).toUint128();
        }
    }

    /// @notice Insurance balances to back position in (x, y) amounts
    /// @param liquidity The pool liquidity before opening the position
    /// @param sqrtPriceX96 The pool sqrt price before opening the position
    /// @param sqrtPriceX96Next The pool sqrt price after opening the position
    /// @param liquidityDelta The delta in pool liquidity used to collateralize the position
    /// @param zeroForOne Whether the position is long token1 and short token0 (true), or long token0 and short token1 (false)
    /// @return insurance0 The insurance reserves in token0 needed to prevent liquidity shortfall for late liquidations
    /// @return insurance1 The insurance reserves in token1 needed to prevent liquidity shortfall for late liquidations
    function insurances(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne
    ) internal pure returns (uint128 insurance0, uint128 insurance1) {
        uint256 prod = !zeroForOne
            ? Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96Next,
                sqrtPriceX96
            ) // iy / y = 1 - sqrt(P'/P) * (1 - del L / L)
            : Math.mulDiv(
                liquidity - liquidityDelta,
                sqrtPriceX96,
                sqrtPriceX96Next
            ); // iy / y = 1 - sqrt(P/P') * (1 - del L / L)

        insurance0 = (((uint256(liquidity) - prod) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96).toUint128();
        insurance1 = (
            Math.mulDiv(
                uint256(liquidity) - prod,
                sqrtPriceX96,
                FixedPoint96.Q96
            )
        ).toUint128();
    }

    /// @notice Debts owed by position in (x, y) amounts
    /// @dev Uses invariant (insurance0 + debt0) * (insurance1 + debt1) = liquidityDelta * sqrtPriceNext
    /// @param sqrtPriceX96Next The pool sqrt price after opening the position
    /// @param liquidityDelta The delta in pool liquidity used to collateralize the position
    /// @param insurance0 The position insurance reserves in token0
    /// @param insurance1 The position insurance reserves in token1
    /// @return debt0 The debt in token0 the position owes to the pool
    /// @return debt1 The debt in token1 the position owes to the pool
    function debts(
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        uint128 insurance0,
        uint128 insurance1
    ) internal pure returns (uint128 debt0, uint128 debt1) {
        // ix + dx = del L / sqrt(P'); iy + dy = del L * sqrt(P')
        debt0 = ((uint256(liquidityDelta) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96Next -
            uint256(insurance0)).toUint128();
        debt1 = (Math.mulDiv(
            liquidityDelta,
            sqrtPriceX96Next,
            FixedPoint96.Q96
        ) - uint256(insurance1)).toUint128();
    }

    /// @notice Fees owed when opening the position in (x, y) amounts
    /// @dev Fees taken proportional to size
    /// @param size The position size
    /// @param fee The fee rate charged on position size
    /// @return The amount of fees charged to open the position
    function fees(uint128 size, uint24 fee) internal pure returns (uint256) {
        return (uint256(size) * fee) / 1e6;
    }

    /// @notice Liquidation rewards required to set aside for liquidator in native (gas) token amount
    /// @dev Returned on settle to position owner or used as incentive for liquidator to liquidate position when unsafe
    /// @param blockBaseFee Current block base fee
    /// @param blockBaseFeeMin Minimum block base fee to use in calculating cost to execute call to liquidate
    /// @param gas Estimated gas required to execute call to liquidate
    /// @param premium Liquidation premium to incentivize potential liquidators with
    /// @return The liquidation rewards to set aside for liquidator if position unsafe
    function liquidationRewards(
        uint256 blockBaseFee,
        uint256 blockBaseFeeMin,
        uint256 gas,
        uint24 premium
    ) internal pure returns (uint256) {
        uint256 baseFee = (
            blockBaseFee > blockBaseFeeMin ? blockBaseFee : blockBaseFeeMin
        );
        // need base fee of ~4e62 for possible overflow with gas limit of 30e6
        return (baseFee * gas * uint256(premium)) / 1e6;
    }

    /// @notice Absolute minimum margin amount required to be held in position
    /// @dev Uses `position.tick` prior to position open (alongside insurance balances) to ensure repayment to pool of at least liquidityDelta liability if ignore funding
    /// @param position The position to check minimum margin amounts for
    /// @param maintenance The minimum maintenance margin requirement for the pool
    /// @return The minimum amount of margin the position must hold
    function marginMinimum(
        Info memory position,
        uint24 maintenance
    ) internal pure returns (uint128) {
        uint160 sqrtPriceX96 = TickMath.getSqrtRatioAtTick(position.tick); // price before open
        if (!position.zeroForOne) {
            // cx >= (1+M) * dy / P - sx
            uint256 debt1Adjusted = (uint256(position.debt1) *
                (1e6 + uint256(maintenance))) / 1e6;

            uint256 prod = sqrtPriceX96 <= type(uint128).max
                ? Math.mulDiv(
                    debt1Adjusted,
                    FixedPoint192.Q192,
                    uint256(sqrtPriceX96) * uint256(sqrtPriceX96)
                )
                : Math.mulDiv(
                    debt1Adjusted,
                    FixedPoint128.Q128,
                    Math.mulDiv(sqrtPriceX96, sqrtPriceX96, FixedPoint64.Q64)
                );
            return
                prod > uint256(position.size)
                    ? (prod - uint256(position.size)).toUint128()
                    : 0; // check necessary due to funding
        } else {
            // cy >= (1+M) * dx * P - sy
            uint256 debt0Adjusted = (uint256(position.debt0) *
                (1e6 + uint256(maintenance))) / 1e6;

            uint256 prod = sqrtPriceX96 <= type(uint128).max
                ? Math.mulDiv(
                    debt0Adjusted,
                    uint256(sqrtPriceX96) * uint256(sqrtPriceX96),
                    FixedPoint192.Q192
                )
                : Math.mulDiv(
                    debt0Adjusted,
                    Math.mulDiv(sqrtPriceX96, sqrtPriceX96, FixedPoint64.Q64),
                    FixedPoint128.Q128
                );
            return
                prod > uint256(position.size)
                    ? (prod - uint256(position.size)).toUint128()
                    : 0; // check necessary due to funding
        }
    }

    /// @notice Amounts (x, y) of pool reserves locked in position
    /// @dev Includes margin in the event position were to be liquidated
    /// @param position The position
    /// @return amount0 The amount of token0 set aside for the position
    /// @return amount1 The amount of token1 set aside for the position
    function amountsLocked(
        Info memory position
    ) internal pure returns (uint256 amount0, uint256 amount1) {
        if (!position.zeroForOne) {
            amount0 =
                uint256(position.size) +
                uint256(position.margin) +
                uint256(position.debt0) +
                uint256(position.insurance0);
            amount1 = position.insurance1;
        } else {
            amount0 = position.insurance0;
            amount1 =
                uint256(position.size) +
                uint256(position.margin) +
                uint256(position.debt1) +
                uint256(position.insurance1);
        }
    }

    /// @notice Debt adjusted for funding
    /// @dev Ref @with-backed/papr/src/UniswapOracleFundingRateController.sol#L156
    /// Follows debt0Next = debt0 * (oracleTwap / poolTwap) ** (dt / fundingPeriod) if zeroForOne = true
    //  or debt1Next = debt1 * (poolTwap / oracleTwap) ** (dt / fundingPeriod) if zeroForOne = false
    /// @param position The position to update debts for funding
    /// @param blockTimestampLast The block timestamp at the last pool state sync
    /// @param tickCumulativeDeltaLast The delta in oracle tick cumulative minus pool tick cumulative values at `blockTimestampLast`
    /// @param tickCumulativeRateMax The maximum rate of change in tick cumulative between the oracle and pool `tickCumulative` values
    /// @param fundingPeriod The pool funding period to benchmark funding payments to
    /// @return debt0 The position debt in token0 after funding
    /// @return debt1 The position debt in token1 after funding
    function debtsAfterFunding(
        Info memory position,
        uint32 blockTimestampLast,
        int56 tickCumulativeDeltaLast,
        uint24 tickCumulativeRateMax,
        uint32 fundingPeriod
    ) internal pure returns (uint128 debt0, uint128 debt1) {
        int56 deltaMax;
        unchecked {
            deltaMax =
                int56(uint56(tickCumulativeRateMax)) *
                int56(uint56(blockTimestampLast - position.blockTimestamp));
        }
        if (!position.zeroForOne) {
            // debt1Now = debt1Start * (P / bar{P}) ** (now - start) / fundingPeriod
            // delta = (a_t - bar{a}_t) - (a_0 - bar{a}_0), clamped by funding rate bounds
            int56 delta = OracleLibrary.oracleTickCumulativeDelta(
                tickCumulativeDeltaLast,
                position.tickCumulativeDelta
            );
            if (delta > deltaMax) delta = deltaMax;
            else if (delta < -deltaMax) delta = -deltaMax;

            // @dev ok as position is unsafe well before arithmeticMeanTick reaches min/max tick given fundingPeriod, tickCumulativeRateMax values
            uint160 numeratorX96 = OracleLibrary.oracleSqrtPriceX96(
                delta,
                fundingPeriod / 2 // div by 2 given sqrt price result
            );
            debt0 = position.debt0;
            debt1 = Math
                .mulDiv(position.debt1, numeratorX96, FixedPoint96.Q96)
                .toUint128();
        } else {
            // debt0Now = debt0Start * (bar{P} / P) ** (now - start) / fundingPeriod
            // delta = (bar{a}_t - a_t) - (bar{a}_0 - a_0), clamped by funding rate bounds
            int56 delta = OracleLibrary.oracleTickCumulativeDelta(
                position.tickCumulativeDelta,
                tickCumulativeDeltaLast
            );
            if (delta > deltaMax) delta = deltaMax;
            else if (delta < -deltaMax) delta = -deltaMax;

            // @dev ok as position is unsafe well before arithmeticMeanTick reaches min/max tick given fundingPeriod, tickCumulativeRateMax values
            uint160 numeratorX96 = OracleLibrary.oracleSqrtPriceX96(
                delta,
                fundingPeriod / 2 // div by 2 given sqrt price result
            );
            debt0 = Math
                .mulDiv(position.debt0, numeratorX96, FixedPoint96.Q96)
                .toUint128();
            debt1 = position.debt1;
        }
    }

    /// @notice Whether the position is safe from liquidation
    /// @dev If not safe, position can be liquidated
    /// Considered safe if (`position.margin` + `position.size`) / oracleTwap >= (1 + `maintenance`) * `position.debt0` when position.zeroForOne = true
    /// or (`position.margin` + `position.size`) * oracleTwap >= (1 + `maintenance`) * `position.debt1` when position.zeroForOne = false
    /// @param position The position to check safety of
    /// @param sqrtPriceX96 The oracle time weighted average sqrt price
    /// @param maintenance The minimum maintenance margin requirement for the pool
    /// @return true if safe and false if not safe
    function safe(
        Info memory position,
        uint160 sqrtPriceX96,
        uint24 maintenance
    ) internal pure returns (bool) {
        if (!position.zeroForOne) {
            uint256 debt1Adjusted = (uint256(position.debt1) *
                (1e6 + uint256(maintenance))) / 1e6;
            uint256 liquidityCollateral = Math.mulDiv(
                uint256(position.margin) + uint256(position.size),
                sqrtPriceX96,
                FixedPoint96.Q96
            );
            uint256 liquidityDebt = (debt1Adjusted << FixedPoint96.RESOLUTION) /
                sqrtPriceX96;
            return liquidityCollateral >= liquidityDebt;
        } else {
            uint256 debt0Adjusted = (uint256(position.debt0) *
                (1e6 + uint256(maintenance))) / 1e6;
            uint256 liquidityCollateral = ((uint256(position.margin) +
                uint256(position.size)) << FixedPoint96.RESOLUTION) /
                sqrtPriceX96;
            uint256 liquidityDebt = Math.mulDiv(
                debt0Adjusted,
                sqrtPriceX96,
                FixedPoint96.Q96
            );
            return liquidityCollateral >= liquidityDebt;
        }
    }
}

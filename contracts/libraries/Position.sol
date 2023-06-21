// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {FixedPoint64} from "./FixedPoint64.sol";
import {FixedPoint96} from "./FixedPoint96.sol";
import {FixedPoint128} from "./FixedPoint128.sol";
import {FixedPoint192} from "./FixedPoint192.sol";

import {OracleLibrary} from "./OracleLibrary.sol";

/// @dev Positions represented in (x, y) space
// TODO: fuzz for edge cases and rounding
library Position {
    using SafeCast for uint256;

    struct Info {
        uint128 size;
        uint128 debt0;
        uint128 debt1;
        uint128 insurance0;
        uint128 insurance1;
        bool zeroForOne;
        bool liquidated;
        int56 tick;
        int56 tickCumulativeDelta; // bar{a}_t - a_t
        uint128 margin;
        uint128 liquidityLocked;
    }

    /// @notice Gets a position from positions mapping
    function get(
        mapping(bytes32 => Info) storage positions,
        address owner,
        uint96 id
    ) internal view returns (Info memory) {
        return positions[keccak256(abi.encodePacked(owner, id))];
    }

    /// @notice Stores the given position in positions mapping
    function set(
        mapping(bytes32 => Info) storage positions,
        address owner,
        uint96 id,
        Info memory position
    ) internal {
        positions[keccak256(abi.encodePacked(owner, id))] = position;
    }

    /// @notice Realizes funding payments via updates to position debt amounts
    function sync(
        Info memory position,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast,
        uint32 fundingPeriod
    ) internal pure returns (Info memory) {
        // early exit if nothing to update
        int56 tickCumulativeDeltaLast = oracleTickCumulativeLast -
            tickCumulativeLast;
        if (tickCumulativeDeltaLast == position.tickCumulativeDelta)
            return position;

        (uint128 debt0, uint128 debt1) = debtsAfterFunding(
            position,
            tickCumulativeLast,
            oracleTickCumulativeLast,
            fundingPeriod
        );
        position.debt0 = debt0;
        position.debt1 = debt1;
        position.tickCumulativeDelta = tickCumulativeDeltaLast;
        return position;
    }

    /// @notice Liquidates an existing position
    function liquidate(
        Info memory position
    ) internal pure returns (Info memory positionAfter) {
        positionAfter.zeroForOne = position.zeroForOne;
        positionAfter.liquidated = true;
        positionAfter.tick = position.tick;
        positionAfter.tickCumulativeDelta = position.tickCumulativeDelta;
    }

    /// @notice Settles existing position
    function settle(
        Info memory position
    ) internal pure returns (Info memory positionAfter) {
        positionAfter.zeroForOne = position.zeroForOne;
        positionAfter.liquidated = position.liquidated;
        positionAfter.tick = position.tick;
        positionAfter.tickCumulativeDelta = position.tickCumulativeDelta;
    }

    /// @notice Assembles a new position from pool state
    /// @dev zeroForOne == true means short position
    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne,
        int24 tick,
        int56 tickCumulativeStart,
        int56 oracleTickCumulativeStart
    ) internal pure returns (Info memory position) {
        position.zeroForOne = zeroForOne;
        position.tick = int56(tick);
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
    function debts(
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        uint128 insurance0,
        uint128 insurance1
    ) internal pure returns (uint128 debt0, uint128 debt1) {
        // ix + dx = del L / sqrt(P'); iy + dy = del L * sqrt(P')
        debt0 = ((uint256(liquidityDelta) << FixedPoint96.RESOLUTION) /
            sqrtPriceX96Next -
            insurance0).toUint128();
        debt1 = (Math.mulDiv(
            liquidityDelta,
            sqrtPriceX96Next,
            FixedPoint96.Q96
        ) - insurance1).toUint128();
    }

    /// @notice Fees owed by position in (x, y) amounts
    /// @dev Fees taken proportional to size
    function fees(uint128 size, uint24 fee) internal pure returns (uint256) {
        return (uint256(size) * fee) / 1e6;
    }

    /// @notice Liquidation rewards to liquidator in (x, y) amounts
    /// @dev Rewards given proportional to size
    function liquidationRewards(
        uint128 size,
        uint24 reward
    ) internal pure returns (uint256) {
        return (uint256(size) * reward) / 1e6;
    }

    /// @notice Absolute minimum margin requirement
    function marginMinimum(
        Info memory position,
        uint24 maintenance
    ) internal pure returns (uint128) {
        uint160 sqrtPriceX96 = TickMath.getSqrtRatioAtTick(
            int24(position.tick)
        ); // price before open
        if (!position.zeroForOne) {
            // cx >= (1+M) * dy / P - sx
            uint256 debt1Adjusted = (uint256(position.debt1) *
                (1e6 + maintenance)) / 1e6;

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
                (1e6 + maintenance)) / 1e6;

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

    /// @notice Amounts (x, y) of pool liquidity locked for position
    /// @dev Includes margin in the event position were to be liquidated
    function amountsLocked(
        Info memory position
    ) internal pure returns (uint128 amount0, uint128 amount1) {
        if (!position.zeroForOne) {
            amount0 =
                position.size +
                position.margin +
                position.debt0 +
                position.insurance0;
            amount1 = position.insurance1;
        } else {
            amount0 = position.insurance0;
            amount1 =
                position.size +
                position.margin +
                position.debt1 +
                position.insurance1;
        }
    }

    /// @notice Debt adjusted for funding
    /// @dev Ref @with-backed/papr/src/UniswapOracleFundingRateController.sol#L156
    function debtsAfterFunding(
        Info memory position,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast,
        uint32 fundingPeriod
    ) internal pure returns (uint128 debt0, uint128 debt1) {
        int56 tickCumulativeDeltaLast = oracleTickCumulativeLast -
            tickCumulativeLast;
        if (!position.zeroForOne) {
            // debt1Now = debt1Start * (P / bar{P}) ** (now - start) / fundingPeriod
            uint160 numeratorX96 = OracleLibrary.oracleSqrtPriceX96(
                -position.tickCumulativeDelta, // a_0 - bar{a}_0
                -tickCumulativeDeltaLast, // a_t - bar{a}_t
                fundingPeriod / 2 // TODO: check ok, particularly with tick range limits
            ); // (a_t - bar{a}_t) - (a_0 - bar{a}_0)
            debt0 = position.debt0;
            debt1 = Math
                .mulDiv(position.debt1, numeratorX96, FixedPoint96.Q96)
                .toUint128();
        } else {
            // debt0Now = debt0Start * (bar{P} / P) ** (now - start) / fundingPeriod
            uint160 numeratorX96 = OracleLibrary.oracleSqrtPriceX96(
                position.tickCumulativeDelta, // bar{a}_0 - a_0
                tickCumulativeDeltaLast, // bar{a}_t - a_t
                fundingPeriod / 2 // TODO: check ok, particularly with tick range limits
            ); // (bar{a}_t - a_t) - (bar{a}_0 - a_0)
            debt0 = Math
                .mulDiv(position.debt0, numeratorX96, FixedPoint96.Q96)
                .toUint128();
            debt1 = position.debt1;
        }
    }

    /// @notice If not safe, position can be liquidated
    function safe(
        Info memory position,
        uint160 sqrtPriceX96,
        uint24 maintenance
    ) internal pure returns (bool) {
        if (!position.zeroForOne) {
            uint256 debt1Adjusted = (uint256(position.debt1) *
                (1e6 + maintenance)) / 1e6;
            uint256 liquidityCollateral = Math.mulDiv(
                position.margin + position.size,
                sqrtPriceX96,
                FixedPoint96.Q96
            );
            uint256 liquidityDebt = (debt1Adjusted << FixedPoint96.RESOLUTION) /
                sqrtPriceX96;
            return liquidityCollateral >= liquidityDebt;
        } else {
            uint256 debt0Adjusted = (uint256(position.debt0) *
                (1e6 + maintenance)) / 1e6;
            uint256 liquidityCollateral = (uint256(
                position.margin + position.size
            ) << FixedPoint96.RESOLUTION) / sqrtPriceX96;
            uint256 liquidityDebt = Math.mulDiv(
                debt0Adjusted,
                sqrtPriceX96,
                FixedPoint96.Q96
            );
            return liquidityCollateral >= liquidityDebt;
        }
    }
}

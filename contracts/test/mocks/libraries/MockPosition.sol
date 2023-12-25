// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {Position} from "../../../libraries/Position.sol";

contract MockPosition {
    using Position for mapping(bytes32 => Position.Info);
    using Position for Position.Info;

    mapping(bytes32 => Position.Info) public positions;

    function get(
        address owner,
        uint96 id
    ) external view returns (Position.Info memory) {
        return positions.get(owner, id);
    }

    function set(
        address owner,
        uint96 id,
        Position.Info memory position
    ) external {
        positions.set(owner, id, position);
    }

    function sync(
        Position.Info memory position,
        uint32 blockTimestampLast,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast,
        uint24 tickCumulativeRateMax,
        uint32 fundingPeriod
    ) external pure returns (Position.Info memory) {
        return
            Position.sync(
                position,
                blockTimestampLast,
                tickCumulativeLast,
                oracleTickCumulativeLast,
                tickCumulativeRateMax,
                fundingPeriod
            );
    }

    function liquidate(
        Position.Info memory position
    ) external pure returns (Position.Info memory) {
        return Position.liquidate(position);
    }

    function settle(
        Position.Info memory position
    ) external pure returns (Position.Info memory) {
        return Position.settle(position);
    }

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
    ) external view returns (Position.Info memory) {
        return
            Position.assemble(
                liquidity,
                sqrtPriceX96,
                sqrtPriceX96Next,
                liquidityDelta,
                zeroForOne,
                tick,
                blockTimestampStart,
                tickCumulativeStart,
                oracleTickCumulativeStart
            );
    }

    function size(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        bool zeroForOne
    ) external view returns (uint128) {
        return
            Position.size(
                liquidity,
                sqrtPriceX96,
                sqrtPriceX96Next,
                zeroForOne
            );
    }

    function insurances(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne
    ) external view returns (uint128, uint128) {
        return
            Position.insurances(
                liquidity,
                sqrtPriceX96,
                sqrtPriceX96Next,
                liquidityDelta,
                zeroForOne
            );
    }

    function debts(
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        uint128 insurance0,
        uint128 insurance1
    ) external view returns (uint128, uint128) {
        return
            Position.debts(
                sqrtPriceX96Next,
                liquidityDelta,
                insurance0,
                insurance1
            );
    }

    function fees(uint128 size, uint24 fee) external view returns (uint256) {
        return Position.fees(size, fee);
    }

    function liquidationRewards(
        uint256 blockBaseFee,
        uint256 blockBaseFeeMin,
        uint256 gas,
        uint24 premium
    ) external pure returns (uint256) {
        return
            Position.liquidationRewards(
                blockBaseFee,
                blockBaseFeeMin,
                gas,
                premium
            );
    }

    function marginMinimum(
        Position.Info memory position,
        uint24 maintenance
    ) external view returns (uint256) {
        return Position.marginMinimum(position, maintenance);
    }

    function amountsLocked(
        Position.Info memory position
    ) external view returns (uint256 amount0, uint256 amount1) {
        return position.amountsLocked();
    }

    function debtsAfterFunding(
        Position.Info memory position,
        uint32 blockTimestampLast,
        int56 tickCumulativeDeltaLast,
        uint24 tickCumulativeRateMax,
        uint32 fundingPeriod
    ) external pure returns (uint128 debt0, uint128 debt1) {
        return
            position.debtsAfterFunding(
                blockTimestampLast,
                tickCumulativeDeltaLast,
                tickCumulativeRateMax,
                fundingPeriod
            );
    }

    function safe(
        Position.Info memory position,
        uint160 sqrtPriceX96,
        uint24 maintenance
    ) external pure returns (bool) {
        return position.safe(sqrtPriceX96, maintenance);
    }
}

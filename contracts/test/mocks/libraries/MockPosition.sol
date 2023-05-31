// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Position} from "../../../libraries/Position.sol";

contract MockPosition {
    using Position for mapping(bytes32 => Position.Info);
    using Position for Position.Info;

    mapping(bytes32 => Position.Info) public positions;

    function get(
        address owner,
        uint112 id
    ) external view returns (Position.Info memory) {
        return positions.get(owner, id);
    }

    function set(
        address owner,
        uint112 id,
        Position.Info memory position
    ) external {
        positions.set(owner, id, position);
    }

    function liquidate(
        Position.Info memory position
    ) external pure returns (Position.Info memory) {
        return Position.liquidate(position);
    }

    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne,
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

    function marginMinimum(
        uint128 size,
        uint24 maintenance,
        uint24 reward
    ) external view returns (uint256) {
        return Position.marginMinimum(size, maintenance, reward);
    }

    function liquidationRewards(
        uint128 size,
        uint24 reward
    ) external pure returns (uint256) {
        return Position.liquidationRewards(size, reward);
    }

    function amountsLocked(
        Position.Info memory position
    ) external view returns (uint128 amount0, uint128 amount1) {
        return position.amountsLocked();
    }

    function debtsAfterFunding(
        Position.Info memory position,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast,
        uint32 fundingPeriod
    ) external pure returns (uint128 debt0, uint128 debt1) {
        return
            position.debtsAfterFunding(
                tickCumulativeLast,
                oracleTickCumulativeLast,
                fundingPeriod
            );
    }

    function safe(
        Position.Info memory position,
        uint160 sqrtPriceX96,
        uint24 maintenance,
        int56 tickCumulativeLast,
        int56 oracleTickCumulativeLast,
        uint32 fundingPeriod
    ) external pure returns (bool) {
        return
            position.safe(
                sqrtPriceX96,
                maintenance,
                tickCumulativeLast,
                oracleTickCumulativeLast,
                fundingPeriod
            );
    }
}

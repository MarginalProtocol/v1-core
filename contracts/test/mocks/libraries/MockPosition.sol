// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Position} from "../../../libraries/Position.sol";

contract MockPosition {
    using Position for mapping(uint256 => Position.Info);

    mapping(uint256 => Position.Info) public positions;

    function set(uint256 id, Position.Info memory position) external {
        positions.set(id, position);
    }

    function assemble(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint24 fee
    ) external view returns (Position.Info memory) {
        return
            Position.assemble(
                liquidity,
                sqrtPriceX96,
                sqrtPriceX96Next,
                liquidityDelta,
                zeroForOne,
                fee
            );
    }

    function sizes(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceX96Next,
        bool zeroForOne
    ) external view returns (uint128, uint128) {
        return
            Position.sizes(
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

    function fees(
        uint128 size0,
        uint128 size1,
        uint24 fee
    ) external view returns (uint128, uint128) {
        return Position.fees(size0, size1, fee);
    }

    function marginMinimumWithFees(
        uint128 size,
        uint24 maintenance,
        uint24 fee
    ) external view returns (uint256) {
        return Position.marginMinimumWithFees(size, maintenance, fee);
    }
}

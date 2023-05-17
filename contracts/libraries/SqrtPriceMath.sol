// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {MaintenanceMath} from "./MaintenanceMath.sol";

library SqrtPriceMath {
    using SafeCast for uint256;

    /// @notice Calculates sqrtP after assembling a position
    /// @dev Choice of insurance function made in this function
    function sqrtPriceX96Next(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint16 maintenance
    ) internal view returns (uint160) {
        uint256 prod = liquidityDelta * (liquidity - liquidityDelta);
        prod = Math.mulDiv(
            prod,
            MaintenanceMath.unit,
            (MaintenanceMath.unit + maintenance)
        );

        uint256 under = liquidity ** 2 - 4 * prod;
        uint256 root = Math.sqrt(under);

        uint256 nextX96 = zeroForOne
            ? Math.mulDiv(
                sqrtPriceX96,
                liquidity + root,
                2 * (liquidity - liquidityDelta)
            )
            : Math.mulDiv(
                sqrtPriceX96,
                2 * (liquidity - liquidityDelta),
                liquidity + root
            );
        return nextX96.toUint160();
    }
}

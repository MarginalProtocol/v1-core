// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {MaintenanceMath} from "./MaintenanceMath.sol";

library SqrtPriceMath {
    function sqrtPriceNext(
        uint256 liquidity,
        uint256 sqrtPrice,
        uint256 liquidityDelta,
        bool zeroForOne,
        uint256 maintenance
    ) internal view returns (uint256) {
        uint256 prod = 4 * liquidityDelta * (liquidity - liquidityDelta);
        prod = Math.mulDiv(
            prod,
            MaintenanceMath.unit,
            MaintenanceMath.unit + maintenance
        );

        uint256 under = liquidity ** 2 - prod; // TODO: overflow worries for k = L**2?
        uint256 root = Math.sqrt(under);

        uint256 numerator = liquidity + root;
        uint256 denominator = 2 * (liquidity - liquidityDelta);

        // TODO: careful with sqrtPrice if go uint160 sqrtPriceX96
        return Math.mulDiv(sqrtPrice, numerator, denominator);
    }
}

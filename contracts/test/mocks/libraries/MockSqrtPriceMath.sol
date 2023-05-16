// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {SqrtPriceMath} from "../../../libraries/SqrtPriceMath.sol";

contract MockSqrtPriceMath {
    function sqrtPriceX96Next(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint256 maintenance // TODO: smaller type
    ) external view returns (uint160) {
        return
            SqrtPriceMath.sqrtPriceX96Next(
                liquidity,
                sqrtPriceX96,
                liquidityDelta,
                zeroForOne,
                maintenance
            );
    }
}

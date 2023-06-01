// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

library TransferHelper {
    using SafeERC20 for IERC20;

    function safeTransfer(address token, address to, uint256 value) internal {
        // in case of dust errors due to (L, sqrtP) <=> (x, y) transforms
        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 amount = value <= balance ? value : balance;
        IERC20(token).safeTransfer(to, amount);
    }
}

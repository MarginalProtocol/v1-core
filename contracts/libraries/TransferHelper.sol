// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

library TransferHelper {
    using SafeERC20 for IERC20;

    /// @notice Transfers an ERC20 token amount from this address
    /// @dev If value > balance, transfers balance of this address
    /// @param token The address of the ERC20 to transfer
    /// @param to The address of the recipient
    /// @param value The desired amount of tokens to transfer
    function safeTransfer(address token, address to, uint256 value) internal {
        // in case of dust errors due to (L, sqrtP) <=> (x, y) transforms
        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 amount = value <= balance ? value : balance;
        IERC20(token).safeTransfer(to, amount);
    }

    /// @notice Transfers an amount of native (gas) token from this address
    /// @dev Ref @uniswap/v3-periphery/contracts/libraries/TransferHelper.sol#L56
    /// @param to The address of the recipient
    /// @param value The amount of ETH to transfer
    function safeTransferETH(address to, uint256 value) internal {
        (bool success, ) = to.call{value: value}(new bytes(0));
        require(success, "STE");
    }
}

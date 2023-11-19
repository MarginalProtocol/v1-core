// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {TransferHelper} from "../../../libraries/TransferHelper.sol";

contract MockTransferHelper {
    function safeTransfer(address token, address to, uint256 value) external {
        TransferHelper.safeTransfer(token, to, value);
    }
}

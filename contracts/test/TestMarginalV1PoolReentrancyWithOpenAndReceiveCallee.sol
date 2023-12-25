// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {SqrtPriceMath} from "../libraries/SqrtPriceMath.sol";

import {IMarginalV1AdjustCallback} from "../interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1MintCallback} from "../interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1OpenCallback} from "../interfaces/callback/IMarginalV1OpenCallback.sol";
import {IMarginalV1SettleCallback} from "../interfaces/callback/IMarginalV1SettleCallback.sol";
import {IMarginalV1SwapCallback} from "../interfaces/callback/IMarginalV1SwapCallback.sol";

import {IMarginalV1Pool} from "../interfaces/IMarginalV1Pool.sol";

/// @dev bytes data param for each call should contain a call to pool function to attempt re-entrance
contract TestMarginalV1PoolReentrancyWithOpenAndReceiveCallee is
    IMarginalV1OpenCallback,
    IMarginalV1SettleCallback
{
    using SafeERC20 for IERC20;

    address private _pool;
    bytes private _data;

    event OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        address sender
    );

    function reenter() private {
        (bool success, bytes memory reason) = _pool.call(_data);
        delete _pool;
        delete _data;

        if (!success) {
            // given custom errors
            // @dev Ref https://ethereum.stackexchange.com/questions/125238/catching-custom-error/125296
            bytes4 desired = bytes4(keccak256(bytes("Locked()")));
            bytes4 received = bytes4(reason);
            if (desired == received) {
                // will ultimately revert with STE
                revert("Locked() returned");
            }
        }
    }

    function open(
        address pool,
        address recipient,
        bool zeroForOne,
        uint128 liquidityDelta,
        uint160 sqrtPriceLimitX96,
        uint128 margin
    )
        external
        payable
        returns (
            uint256 id,
            uint256 size,
            uint256 debt,
            uint256 amount0,
            uint256 amount1
        )
    {
        _pool = pool;
        return
            IMarginalV1Pool(pool).open{value: msg.value}(
                recipient,
                zeroForOne,
                liquidityDelta,
                sqrtPriceLimitX96,
                margin,
                abi.encode(msg.sender)
            );
    }

    function marginalV1OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit OpenCallback(amount0Owed, amount1Owed, sender);

        if (amount0Owed > 0)
            IERC20(IMarginalV1Pool(msg.sender).token0()).safeTransferFrom(
                sender,
                msg.sender,
                amount0Owed
            );
        if (amount1Owed > 0)
            IERC20(IMarginalV1Pool(msg.sender).token1()).safeTransferFrom(
                sender,
                msg.sender,
                amount1Owed
            );
    }

    function settle(
        address pool,
        address recipient,
        uint96 id,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1, uint256 rewards) {
        _pool = pool;
        _data = data;
        return IMarginalV1Pool(pool).settle(recipient, id, data);
    }

    function marginalV1SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        revert("Failed to lock on receive()");
    }

    function liquidate(
        address pool,
        address recipient,
        address owner,
        uint96 id,
        bytes calldata data
    ) external returns (uint256 rewards) {
        _pool = pool;
        _data = data;
        return IMarginalV1Pool(pool).liquidate(recipient, owner, id);
    }

    receive() external payable {
        reenter();
    }
}

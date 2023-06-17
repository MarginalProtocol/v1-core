// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IMarginalV1AdjustCallback} from "../interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1MintCallback} from "../interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1OpenCallback} from "../interfaces/callback/IMarginalV1OpenCallback.sol";
import {IMarginalV1SettleCallback} from "../interfaces/callback/IMarginalV1SettleCallback.sol";
import {IMarginalV1SwapCallback} from "../interfaces/callback/IMarginalV1SwapCallback.sol";

import {IMarginalV1Pool} from "../interfaces/IMarginalV1Pool.sol";

contract TestMarginalV1PoolCallee is
    IMarginalV1AdjustCallback,
    IMarginalV1MintCallback,
    IMarginalV1OpenCallback
{
    using SafeERC20 for IERC20;

    event AdjustCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        address sender
    );
    event MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        address sender
    );
    event OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        address sender
    );
    event SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        address sender
    );
    event SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        address sender
    );

    function mint(
        address pool,
        address recipient,
        uint128 liquidityDelta
    ) external returns (uint256 amount0, uint256 amount1) {
        return
            IMarginalV1Pool(pool).mint(
                recipient,
                liquidityDelta,
                abi.encode(msg.sender)
            );
    }

    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit MintCallback(amount0Owed, amount1Owed, sender);

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

    function open(
        address pool,
        address recipient,
        bool zeroForOne,
        uint128 liquidityDelta,
        uint160 sqrtPriceLimitX96,
        uint128 margin
    ) external returns (uint256 id, uint256 size) {
        return
            IMarginalV1Pool(pool).open(
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

    function adjust(
        address pool,
        address recipient,
        uint96 id,
        int128 marginDelta
    ) external returns (uint256 margin0, uint256 margin1) {
        return
            IMarginalV1Pool(pool).adjust(
                recipient,
                id,
                marginDelta,
                abi.encode(msg.sender)
            );
    }

    function marginalV1AdjustCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit AdjustCallback(amount0Owed, amount1Owed, sender);

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
        uint96 id
    ) external returns (int256 amount0, int256 amount1) {
        return
            IMarginalV1Pool(pool).settle(recipient, id, abi.encode(msg.sender));
    }

    function marginalV1SettleCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit SettleCallback(amount0Delta, amount1Delta, sender);

        if (amount0Delta > 0) {
            IERC20(IMarginalV1Pool(msg.sender).token0()).safeTransferFrom(
                sender,
                msg.sender,
                uint256(amount0Delta)
            );
        } else if (amount1Delta > 0) {
            IERC20(IMarginalV1Pool(msg.sender).token1()).safeTransferFrom(
                sender,
                msg.sender,
                uint256(amount1Delta)
            );
        } else {
            assert(amount0Delta == 0 && amount1Delta == 0);
        }
    }

    function swap(
        address pool,
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96
    ) external returns (int256 amount0, int256 amount1) {
        return
            IMarginalV1Pool(pool).swap(
                recipient,
                zeroForOne,
                amountSpecified,
                sqrtPriceLimitX96,
                abi.encode(msg.sender)
            );
    }

    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit SwapCallback(amount0Delta, amount1Delta, sender);

        if (amount0Delta > 0) {
            IERC20(IMarginalV1Pool(msg.sender).token0()).safeTransferFrom(
                sender,
                msg.sender,
                uint256(amount0Delta)
            );
        } else if (amount1Delta > 0) {
            IERC20(IMarginalV1Pool(msg.sender).token1()).safeTransferFrom(
                sender,
                msg.sender,
                uint256(amount1Delta)
            );
        } else {
            assert(amount0Delta == 0 && amount1Delta == 0);
        }
    }
}

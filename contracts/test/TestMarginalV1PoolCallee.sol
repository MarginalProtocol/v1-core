// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IMarginalV1AdjustCallback} from "../interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1MintCallback} from "../interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1OpenCallback} from "../interfaces/callback/IMarginalV1OpenCallback.sol";

import {IMarginalV1Pool} from "../interfaces/IMarginalV1Pool.sol";

contract TestMarginalV1PoolCallee is
    IMarginalV1AdjustCallback,
    IMarginalV1MintCallback,
    IMarginalV1OpenCallback
{
    using SafeERC20 for IERC20;

    event AdjustCallback(
        uint256 margin0In,
        uint256 margin1In,
        uint256 margin0Out,
        uint256 margin1Out,
        address sender
    );
    event MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        address sender
    );
    event OpenCallback(
        uint256 margin0MinimumWithFees,
        uint256 margin1MinimumWithFees,
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
        uint160 sqrtPriceLimitX96
    ) external returns (uint256 id) {
        return
            IMarginalV1Pool(pool).open(
                recipient,
                zeroForOne,
                liquidityDelta,
                sqrtPriceLimitX96,
                abi.encode(msg.sender)
            );
    }

    function marginalV1OpenCallback(
        uint256 margin0MinimumWithFees,
        uint256 margin1MinimumWithFees,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit OpenCallback(
            margin0MinimumWithFees,
            margin1MinimumWithFees,
            sender
        );

        if (margin0MinimumWithFees > 0)
            IERC20(IMarginalV1Pool(msg.sender).token0()).safeTransferFrom(
                sender,
                msg.sender,
                margin0MinimumWithFees
            );
        if (margin1MinimumWithFees > 0)
            IERC20(IMarginalV1Pool(msg.sender).token1()).safeTransferFrom(
                sender,
                msg.sender,
                margin1MinimumWithFees
            );
    }

    function marginalV1AdjustCallback(
        uint256 margin0In,
        uint256 margin1In,
        uint256 margin0Out,
        uint256 margin1Out,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));
        address token0 = IMarginalV1Pool(msg.sender).token0();
        address token1 = IMarginalV1Pool(msg.sender).token1();

        emit AdjustCallback(
            margin0In,
            margin1In,
            margin0Out,
            margin1Out,
            sender
        );

        if (margin0Out > 0) IERC20(token0).safeTransfer(sender, margin0Out);
        if (margin1Out > 0) IERC20(token1).safeTransfer(sender, margin1Out);

        if (margin0In > 0)
            IERC20(token0).safeTransferFrom(sender, msg.sender, margin0In);
        if (margin1In > 0)
            IERC20(token1).safeTransferFrom(sender, msg.sender, margin1In);
    }
}

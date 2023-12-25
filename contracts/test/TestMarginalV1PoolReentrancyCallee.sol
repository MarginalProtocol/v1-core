// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {SqrtPriceMath} from "../libraries/SqrtPriceMath.sol";

import {IMarginalV1AdjustCallback} from "../interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1MintCallback} from "../interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1OpenCallback} from "../interfaces/callback/IMarginalV1OpenCallback.sol";
import {IMarginalV1SettleCallback} from "../interfaces/callback/IMarginalV1SettleCallback.sol";
import {IMarginalV1SwapCallback} from "../interfaces/callback/IMarginalV1SwapCallback.sol";

import {IMarginalV1Pool} from "../interfaces/IMarginalV1Pool.sol";

/// @dev bytes data param for each call should contain a call to pool function to attempt re-entrance
contract TestMarginalV1PoolReentrancyCallee is
    IMarginalV1MintCallback,
    IMarginalV1OpenCallback,
    IMarginalV1SwapCallback
{
    address private _pool;

    function reenter(bytes calldata data) private {
        (bool success, bytes memory reason) = _pool.call(data);
        delete _pool;

        if (success) {
            revert("Failed to lock");
        } else {
            // given custom errors
            // @dev Ref https://ethereum.stackexchange.com/questions/125238/catching-custom-error/125296
            bytes4 desired = bytes4(keccak256(bytes("Locked()")));
            bytes4 received = bytes4(reason);
            if (desired != received) {
                revert("Locked() not returned");
            } else {
                revert("Locked() returned");
            }
        }
    }

    function mint(
        address pool,
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) external returns (uint256 shares, uint256 amount0, uint256 amount1) {
        _pool = pool;
        return IMarginalV1Pool(pool).mint(recipient, liquidityDelta, data);
    }

    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        reenter(data);
    }

    function open(
        address pool,
        address recipient,
        bool zeroForOne,
        uint128 liquidityDelta,
        uint160 sqrtPriceLimitX96,
        uint128 margin,
        bytes calldata data
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
                data
            );
    }

    function marginalV1OpenCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        reenter(data);
    }

    function swap(
        address pool,
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1) {
        _pool = pool;
        return
            IMarginalV1Pool(pool).swap(
                recipient,
                zeroForOne,
                amountSpecified,
                sqrtPriceLimitX96,
                data
            );
    }

    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        reenter(data);
    }
}

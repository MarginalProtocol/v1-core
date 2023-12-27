// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IMarginalV1Pool is IERC20 {
    function factory() external view returns (address);

    function oracle() external view returns (address);

    function token0() external view returns (address);

    function token1() external view returns (address);

    function maintenance() external view returns (uint24);

    function fee() external view returns (uint24);

    function rewardPremium() external view returns (uint24);

    function tickCumulativeRateMax() external view returns (uint24);

    function secondsAgo() external view returns (uint32);

    function fundingPeriod() external view returns (uint32);

    function state()
        external
        view
        returns (
            uint160 sqrtPriceX96,
            uint96 totalPositions,
            uint128 liquidity,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulative,
            uint8 feeProtocol,
            bool initialized
        );

    function liquidityLocked() external view returns (uint128);

    function protocolFees()
        external
        view
        returns (uint128 protocolFees0, uint128 protocolFees1);

    function positions(
        bytes32 key
    )
        external
        view
        returns (
            uint128 size,
            uint128 debt0,
            uint128 debt1,
            uint128 insurance0,
            uint128 insurance1,
            bool zeroForOne,
            bool liquidated,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulativeDelta,
            uint128 margin,
            uint128 liquidityLocked,
            uint256 rewards
        );

    function open(
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
        );

    function adjust(
        address recipient,
        uint96 id,
        int128 marginDelta,
        bytes calldata data
    ) external returns (uint256 margin0, uint256 margin1);

    function settle(
        address recipient,
        uint96 id,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1, uint256 rewards);

    function liquidate(
        address recipient,
        address owner,
        uint96 id
    ) external returns (uint256 rewards);

    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);

    function mint(
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) external returns (uint256 shares, uint256 amount0, uint256 amount1);

    function burn(
        address recipient,
        uint256 shares
    )
        external
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1);

    function setFeeProtocol(uint8 feeProtocol) external;

    function collectProtocol(
        address recipient
    ) external returns (uint128 amount0, uint128 amount1);
}

// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

interface IMarginalV1Pool {
    function factory() external view returns (address);

    function oracle() external view returns (address);

    function token0() external view returns (address);

    function token1() external view returns (address);

    function fee() external view returns (uint24);

    function maintenance() external view returns (uint24);

    function state()
        external
        view
        returns (
            uint128 liquidity,
            uint160 sqrtPriceX96,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulative,
            uint104 totalPositions,
            uint8 feeProtocol
        );

    function reservesLocked()
        external
        view
        returns (uint128 reserves0Locked, uint128 reserves1Locked);

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
            int56 tickCumulativeStart,
            int56 oracleTickCumulativeStart,
            uint128 margin,
            uint128 rewards
        );

    function initialize(uint160 _sqrtPriceX96) external;

    function open(
        address recipient,
        bool zeroForOne,
        uint128 liquidityDelta,
        uint160 sqrtPriceLimitX96,
        uint128 margin,
        bytes calldata data
    ) external returns (uint256 id);

    function adjust(
        address recipient,
        uint112 id,
        int256 marginDelta,
        bytes calldata data
    ) external returns (uint256 margin0, uint256 margin1);

    function settle(
        address recipient,
        uint112 id,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);

    function liquidate(
        address recipient,
        address owner,
        uint112 id
    ) external returns (uint256 reward0, uint256 reward1);

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
    ) external returns (uint256 amount0, uint256 amount1);

    function burn(
        address recipient,
        uint256 shares
    ) external returns (uint256 amount0, uint256 amount1);
}

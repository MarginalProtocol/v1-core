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
            uint112 totalPositions
        );

    function reservesLocked()
        external
        view
        returns (uint128 reserves0Locked, uint128 reserves1Locked);

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
            uint256 margin
        );

    function initialize(uint160 _sqrtPriceX96) external;

    function open(
        address recipient,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (uint256 id);

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

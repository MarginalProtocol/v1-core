// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

contract MockUniswapV3Pool {
    address public immutable token0;
    address public immutable token1;
    uint24 public immutable fee;

    struct Observation {
        uint32 blockTimestamp;
        int56 tickCumulative;
        uint160 secondsPerLiquidityCumulativeX128;
        bool initialized;
    }
    Observation[65535] public observations;
    uint256 private observationIndex;

    struct Slot0 {
        // the current price
        uint160 sqrtPriceX96;
        // the current tick
        int24 tick;
        // the most-recently updated index of the observations array
        uint16 observationIndex;
        // the current maximum number of observations that are being stored
        uint16 observationCardinality;
        // the next maximum number of observations to store, triggered in observations.write
        uint16 observationCardinalityNext;
        // the current protocol fee as a percentage of the swap fee taken on withdrawal
        // represented as an integer denominator (1/x)%
        uint8 feeProtocol;
        // whether the pool is locked
        bool unlocked;
    }
    Slot0 public slot0;

    constructor(address tokenA, address tokenB, uint24 _fee) {
        (address _token0, address _token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        token0 = _token0;
        token1 = _token1;
        fee = _fee;
    }

    function setSlot0(Slot0 memory _slot0) external {
        slot0 = _slot0;
    }

    function pushObservation(
        uint32 blockTimestamp,
        int56 tickCumulative,
        uint160 secondsPerLiquidityCumulativeX128,
        bool initialized
    ) external {
        observations[observationIndex % 65535] = (
            Observation({
                blockTimestamp: blockTimestamp,
                tickCumulative: tickCumulative,
                secondsPerLiquidityCumulativeX128: secondsPerLiquidityCumulativeX128,
                initialized: initialized
            })
        );
        observationIndex++;
    }

    /// @dev unlike Uniswap V3, naively returns back observations so order matters
    /// @dev assumes contracts query with e.g. secondsAgos[0] = secondsAgo; secondsAgos[1] = 0;
    // TODO: fix to be more realistic
    function observe(
        uint32[] calldata secondsAgos
    )
        external
        view
        returns (
            int56[] memory tickCumulatives,
            uint160[] memory secondsPerLiquidityCumulativeX128s
        )
    {
        uint256 _observationIndex = observationIndex;
        require(
            secondsAgos.length <= _observationIndex,
            "not enough observations"
        );
        tickCumulatives = new int56[](secondsAgos.length);
        secondsPerLiquidityCumulativeX128s = new uint160[](secondsAgos.length);
        for (uint256 i = 0; i < secondsAgos.length; i++) {
            uint256 j = _observationIndex - secondsAgos.length + i;
            Observation memory observation = observations[j];
            tickCumulatives[i] = observation.tickCumulative;
            secondsPerLiquidityCumulativeX128s[i] = observation
                .secondsPerLiquidityCumulativeX128;
        }
    }
}

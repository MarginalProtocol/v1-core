// SPDX-License-Identifier: AGPL-3.0-or-later
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

    constructor(address tokenA, address tokenB, uint24 _fee) {
        (address _token0, address _token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);
        token0 = _token0;
        token1 = _token1;
        fee = _fee;
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
        tickCumulatives = new int56[](secondsAgos.length);
        secondsPerLiquidityCumulativeX128s = new uint160[](secondsAgos.length);
        for (uint256 i = 0; i < secondsAgos.length; i++) {
            Observation memory observation = observations[i];
            tickCumulatives[i] = observation.tickCumulative;
            secondsPerLiquidityCumulativeX128s[i] = observation
                .secondsPerLiquidityCumulativeX128;
        }
    }
}

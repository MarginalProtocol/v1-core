// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";

import {LiquidityMath} from "./libraries/LiquidityMath.sol";
import {OracleLibrary} from "./libraries/OracleLibrary.sol";
import {Position} from "./libraries/Position.sol";
import {SqrtPriceMath} from "./libraries/SqrtPriceMath.sol";
import {TransferHelper} from "./libraries/TransferHelper.sol";

import {IMarginalV1AdjustCallback} from "./interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1MintCallback} from "./interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1OpenCallback} from "./interfaces/callback/IMarginalV1OpenCallback.sol";

import {IMarginalV1Factory} from "./interfaces/IMarginalV1Factory.sol";
import {IMarginalV1Pool} from "./interfaces/IMarginalV1Pool.sol";

contract MarginalV1Pool is IMarginalV1Pool, ERC20 {
    using Position for mapping(bytes32 => Position.Info);
    using Position for Position.Info;
    using SafeCast for uint256;

    address public immutable factory;
    address public immutable oracle;

    address public immutable token0;
    address public immutable token1;

    uint24 public immutable fee;
    uint24 public immutable maintenance;
    uint24 public immutable reward;

    uint32 public immutable secondsAgo;
    uint32 public immutable fundingPeriod;

    // @dev Pool state represented in (L, sqrtP) space
    struct State {
        uint128 liquidity;
        uint160 sqrtPriceX96;
        int24 tick;
        uint32 blockTimestamp;
        int56 tickCumulative;
        uint112 totalPositions; // > ~ 1e25 years at max per block to fill on mainnet
    }
    State public state;

    struct ReservesLocked {
        uint128 token0;
        uint128 token1;
    }
    ReservesLocked public reservesLocked;

    mapping(bytes32 => Position.Info) public positions;

    uint256 private unlocked = 1; // uses OZ convention of 1 for false and 2 for true
    modifier lock() {
        require(unlocked == 2, "locked");
        unlocked = 1;
        _;
        unlocked = 2;
    }

    event Initialize(uint160 sqrtPriceX96, int24 tick);
    event Open(
        address sender,
        address indexed owner,
        uint256 indexed id,
        uint128 liquidityAfter,
        uint160 sqrtPriceX96After,
        uint128 liquidityDelta
    );
    event Adjust(
        address indexed owner,
        uint256 indexed id,
        address recipient,
        uint256 marginAfter
    );
    event Liquidate(
        address indexed owner,
        uint256 indexed id,
        address recipient,
        uint128 liquidityAfter,
        uint160 sqrtPriceX96After,
        uint256 rewards0,
        uint256 rewards1
    );
    event Mint(
        address sender,
        address indexed owner,
        uint128 liquidityDelta,
        uint256 amount0,
        uint256 amount1
    );
    event Burn(
        address indexed owner,
        address recipient,
        uint128 liquidityDelta,
        uint256 amount0,
        uint256 amount1
    );

    constructor() ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        (
            token0,
            token1,
            maintenance,
            fee,
            reward,
            oracle,
            secondsAgo,
            fundingPeriod
        ) = IMarginalV1Factory(msg.sender).params();
        factory = msg.sender;
    }

    function initialize(uint160 _sqrtPriceX96) external {
        require(state.sqrtPriceX96 == 0, "initialized");
        int24 tick = TickMath.getTickAtSqrtRatio(_sqrtPriceX96);
        state = State({
            liquidity: 0,
            sqrtPriceX96: _sqrtPriceX96,
            tick: tick,
            blockTimestamp: _blockTimestamp(),
            tickCumulative: 0,
            totalPositions: 0
        });
        unlocked = 2;
        emit Initialize(_sqrtPriceX96, tick);
    }

    function _blockTimestamp() internal view virtual returns (uint32) {
        return uint32(block.timestamp);
    }

    function balance0() private view returns (uint256) {
        return IERC20(token0).balanceOf(address(this));
    }

    function balance1() private view returns (uint256) {
        return IERC20(token1).balanceOf(address(this));
    }

    function oracleTickCumulatives(
        uint32[] memory secondsAgos
    ) private view returns (int56[] memory) {
        (int56[] memory tickCumulatives, ) = IUniswapV3Pool(oracle).observe(
            secondsAgos
        );
        return tickCumulatives;
    }

    function open(
        address recipient,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external lock returns (uint256 id) {
        State memory _state = state;
        require(
            liquidityDelta < _state.liquidity,
            "liquidityDelta >= liquidity"
        ); // TODO: min liquidity, min liquidity delta (size)
        require(
            zeroForOne
                ? sqrtPriceLimitX96 < _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO
                : sqrtPriceLimitX96 > _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO,
            "sqrtPriceLimitX96 exceeds min/max"
        );

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96Next(
            _state.liquidity,
            _state.sqrtPriceX96,
            liquidityDelta,
            zeroForOne,
            maintenance
        );
        require(
            zeroForOne
                ? sqrtPriceX96Next >= sqrtPriceLimitX96
                : sqrtPriceX96Next <= sqrtPriceLimitX96,
            "sqrtPriceX96Next exceeds sqrtPriceLimitX96"
        );

        // oracle write then assemble position
        _state.tickCumulative +=
            int56(_state.tick) *
            int56(uint56(_blockTimestamp() - _state.blockTimestamp)); // TODO: think thru overflow
        _state.blockTimestamp = _blockTimestamp();
        _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        Position.Info memory position = Position.assemble(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne,
            _state.tickCumulative,
            oracleTickCumulative
        );
        _state.liquidity -= liquidityDelta;
        _state.sqrtPriceX96 = sqrtPriceX96Next;

        // callback for margin amount
        if (!zeroForOne) {
            // long token0 (out) relative to token1 (in); margin in token0
            uint256 balance0Before = balance0();
            uint256 margin0Minimum = Position.marginMinimum(
                position.size,
                maintenance
            ); // saves gas by not referencing oracle price but unsafe for trader to use wrt liquidations
            uint256 fees0 = Position.fees(position.size, fee);
            uint256 rewards0 = Position.liquidationRewards(
                position.size,
                reward
            );
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                margin0Minimum + fees0 + rewards0,
                0,
                data
            );

            uint256 amount0 = balance0() - balance0Before;
            require(
                amount0 >= margin0Minimum + fees0 + rewards0,
                "amount0 < min"
            );
            uint256 margin = amount0 - fees0 - rewards0;

            position.margin = margin.toUint128(); // safecast to avoid issues on liquidation
            position.rewards = uint128(rewards0);
            position.debt0 += uint128(fees0); // fees added to available liquidity on settle

            ReservesLocked memory _reservesLocked = reservesLocked;
            (uint128 amount0Locked, uint128 amount1Locked) = position
                .amountsLocked();
            _reservesLocked.token0 += amount0Locked;
            _reservesLocked.token1 += amount1Locked;
            reservesLocked = _reservesLocked;
        } else {
            // long token1 (out) relative to token0 (in); margin in token1
            uint256 balance1Before = balance1();
            uint256 margin1Minimum = Position.marginMinimum(
                position.size,
                maintenance
            ); // saves gas by not referencing oracle price but unsafe for trader to use wrt liquidations
            uint256 fees1 = Position.fees(position.size, fee);
            uint256 rewards1 = Position.liquidationRewards(
                position.size,
                reward
            );
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                0,
                margin1Minimum + fees1 + rewards1,
                data
            );

            uint256 amount1 = balance1() - balance1Before;
            require(
                amount1 >= margin1Minimum + fees1 + rewards1,
                "amount1 < min"
            );
            uint256 margin = amount1 - fees1 - rewards1;

            position.margin = margin.toUint128(); // safecast to avoid issues on liquidation
            position.rewards = uint128(rewards1);
            position.debt1 += uint128(fees1); // fees added to available liquidity on settle

            ReservesLocked memory _reservesLocked = reservesLocked;
            (uint128 amount0Locked, uint128 amount1Locked) = position
                .amountsLocked();
            _reservesLocked.token0 += amount0Locked;
            _reservesLocked.token1 += amount1Locked;
            reservesLocked = _reservesLocked;
        }

        id = _state.totalPositions;
        positions.set(recipient, _state.totalPositions, position);
        _state.totalPositions++;

        // update pool state to latest
        state = _state;

        emit Open(
            msg.sender,
            recipient,
            id,
            _state.liquidity,
            _state.sqrtPriceX96,
            liquidityDelta
        );
    }

    function adjust(
        address recipient,
        uint112 id,
        uint128 marginIn,
        uint128 marginOut,
        bytes calldata data
    ) external lock {
        Position.Info memory position = positions.get(msg.sender, id);
        require(position.size > 0, "not position");
        require(marginOut <= position.margin, "marginOut > position margin");
        uint256 marginMinimum = Position.marginMinimum(
            position.size,
            maintenance
        );

        // flash margin out then callback for margin in
        if (!position.zeroForOne) {
            TransferHelper.safeTransfer(token0, recipient, marginOut);
            position.margin -= marginOut;

            uint256 balance0Before = balance0();
            uint256 margin0AdjustMinimum = uint256(position.margin) <
                marginMinimum
                ? marginMinimum - uint256(position.margin)
                : 0;
            IMarginalV1AdjustCallback(recipient).marginalV1AdjustCallback(
                marginIn,
                0,
                marginOut,
                0,
                data
            );

            uint256 amount0 = balance0() - balance0Before;
            require(amount0 >= margin0AdjustMinimum, "amount0 < min");
            position.margin += amount0.toUint128(); // safecast to avoid issues on liquidation
        } else {
            TransferHelper.safeTransfer(token1, recipient, marginOut);
            position.margin -= marginOut;

            uint256 balance1Before = balance1();
            uint256 margin1AdjustMinimum = uint256(position.margin) <
                marginMinimum
                ? marginMinimum - uint256(position.margin)
                : 0;
            IMarginalV1AdjustCallback(recipient).marginalV1AdjustCallback(
                0,
                marginIn,
                0,
                marginOut,
                data
            );
            uint256 amount1 = balance1() - balance1Before;
            require(amount1 >= margin1AdjustMinimum, "amount1 < min");
            position.margin += amount1.toUint128(); // safecast to avoid issues on liquidation
        }

        positions.set(msg.sender, id, position);

        emit Adjust(msg.sender, uint256(id), recipient, position.margin);
    }

    // TODO:
    function settle(
        address recipient,
        uint112 id,
        uint128 liquidityDelta,
        bytes calldata data
    ) external lock {}

    function liquidate(
        address recipient,
        address owner,
        uint112 id
    ) external lock returns (uint256 rewards0, uint256 rewards1) {
        State memory _state = state;
        Position.Info memory position = positions.get(owner, id);
        require(position.size > 0, "not position");

        // oracle write then liquidate position
        _state.tickCumulative +=
            int56(_state.tick) *
            int56(uint56(_blockTimestamp() - _state.blockTimestamp)); // TODO: think thru overflow
        _state.blockTimestamp = _blockTimestamp();

        // oracle price averaged over seconds ago for liquidation calc
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;
        secondsAgos[1] = 0;

        int56[] memory oracleTickCumulativesLast = oracleTickCumulatives(
            secondsAgos
        );
        uint160 oracleSqrtPriceX96 = OracleLibrary.oracleSqrtPriceX96(
            oracleTickCumulativesLast[0],
            oracleTickCumulativesLast[1],
            secondsAgo
        );
        require(
            !position.safe(
                oracleSqrtPriceX96,
                maintenance,
                _state.tickCumulative,
                oracleTickCumulativesLast[1], // zero seconds ago
                fundingPeriod
            ),
            "position safe"
        );

        (uint128 amount0, uint128 amount1) = position.amountsLocked();
        ReservesLocked memory _reservesLocked = reservesLocked;
        _reservesLocked.token0 -= amount0;
        _reservesLocked.token1 -= amount1;
        reservesLocked = _reservesLocked;

        if (!position.zeroForOne) {
            rewards0 = uint256(position.rewards);
            amount0 += position.margin;

            (uint128 reserve0, uint128 reserve1) = LiquidityMath.toAmounts(
                _state.liquidity,
                _state.sqrtPriceX96
            );
            (uint128 liquidityNext, uint160 sqrtPriceX96Next) = LiquidityMath
                .toLiquiditySqrtPriceX96(
                    reserve0 + amount0,
                    reserve1 + amount1
                );
            _state.liquidity = liquidityNext;
            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);
        } else {
            rewards1 = uint256(position.rewards);
            amount1 += position.margin;

            (uint128 reserve0, uint128 reserve1) = LiquidityMath.toAmounts(
                _state.liquidity,
                _state.sqrtPriceX96
            );
            (uint128 liquidityNext, uint160 sqrtPriceX96Next) = LiquidityMath
                .toLiquiditySqrtPriceX96(
                    reserve0 + amount0,
                    reserve1 + amount1
                );
            _state.liquidity = liquidityNext;
            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);
        }

        if (rewards0 > 0)
            TransferHelper.safeTransfer(token0, recipient, rewards0);
        if (rewards1 > 0)
            TransferHelper.safeTransfer(token1, recipient, rewards1);

        positions.set(owner, id, position.liquidate());

        // update pool state to latest
        state = _state;

        emit Liquidate(
            owner,
            uint256(id),
            recipient,
            _state.liquidity,
            _state.sqrtPriceX96,
            rewards0,
            rewards1
        );
    }

    // TODO:
    function swap(
        address recipient,
        uint128 amountOut,
        bool zeroForOne,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external lock returns (uint128 amountIn) {}

    function mint(
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) external lock returns (uint256 amount0, uint256 amount1) {
        State memory _state = state;
        uint256 _totalSupply = totalSupply();
        require(liquidityDelta > 0, "liquidityDelta == 0");

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96
        );

        // total liquidity is available liquidity if all locked reserves were returned to pool
        uint256 shares;
        {
            (uint128 reserve0, uint128 reserve1) = LiquidityMath.toAmounts(
                _state.liquidity,
                _state.sqrtPriceX96
            );
            ReservesLocked memory _reservesLocked = reservesLocked;
            (uint128 totalLiquidityAfter, ) = LiquidityMath
                .toLiquiditySqrtPriceX96(
                    reserve0 + _reservesLocked.token0 + uint128(amount0),
                    reserve1 + _reservesLocked.token1 + uint128(amount1)
                );
            shares = _totalSupply == 0
                ? totalLiquidityAfter
                : Math.mulDiv(
                    _totalSupply,
                    liquidityDelta,
                    totalLiquidityAfter - liquidityDelta
                );
        }

        _state.liquidity += liquidityDelta;

        // callback for amounts owed
        uint256 balance0Before = balance0();
        uint256 balance1Before = balance1();
        IMarginalV1MintCallback(msg.sender).marginalV1MintCallback(
            amount0,
            amount1,
            data
        );
        require(balance0Before + amount0 <= balance0(), "balance0 < min");
        require(balance1Before + amount1 <= balance1(), "balance1 < min");

        // update pool state to latest
        state = _state;

        _mint(recipient, shares);

        emit Mint(msg.sender, recipient, liquidityDelta, amount0, amount1);
    }

    /// @dev Reverts if not enough liquidity available to exit due to outstanding positions
    function burn(
        address recipient,
        uint256 shares
    ) external lock returns (uint256 amount0, uint256 amount1) {
        State memory _state = state;
        uint256 _totalSupply = totalSupply();
        require(shares > 0, "shares == 0");
        require(shares <= _totalSupply, "shares > totalSupply");

        // total liquidity is available liquidity if all locked reserves were returned to pool
        uint128 liquidityDelta;
        {
            (uint128 reserve0, uint128 reserve1) = LiquidityMath.toAmounts(
                _state.liquidity,
                _state.sqrtPriceX96
            );
            ReservesLocked memory _reservesLocked = reservesLocked;
            (uint128 _totalLiquidity, ) = LiquidityMath.toLiquiditySqrtPriceX96(
                reserve0 + _reservesLocked.token0,
                reserve1 + _reservesLocked.token1
            );
            liquidityDelta = uint128(
                Math.mulDiv(_totalLiquidity, shares, _totalSupply)
            );
        }
        require(
            liquidityDelta < _state.liquidity,
            "liquidityDelta >= liquidity"
        );

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96
        );
        _state.liquidity -= liquidityDelta;

        if (amount0 > 0)
            TransferHelper.safeTransfer(token0, recipient, amount0);
        if (amount1 > 0)
            TransferHelper.safeTransfer(token1, recipient, amount1);

        // update pool state to latest
        state = _state;

        _burn(msg.sender, shares);

        emit Burn(msg.sender, recipient, liquidityDelta, amount0, amount1);
    }
}

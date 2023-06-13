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
import {SwapMath} from "./libraries/SwapMath.sol";
import {TransferHelper} from "./libraries/TransferHelper.sol";

import {IMarginalV1AdjustCallback} from "./interfaces/callback/IMarginalV1AdjustCallback.sol";
import {IMarginalV1MintCallback} from "./interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1OpenCallback} from "./interfaces/callback/IMarginalV1OpenCallback.sol";
import {IMarginalV1SettleCallback} from "./interfaces/callback/IMarginalV1SettleCallback.sol";
import {IMarginalV1SwapCallback} from "./interfaces/callback/IMarginalV1SwapCallback.sol";

import {IMarginalV1Factory} from "./interfaces/IMarginalV1Factory.sol";
import {IMarginalV1PoolDeployer} from "./interfaces/IMarginalV1PoolDeployer.sol";
import {IMarginalV1Pool} from "./interfaces/IMarginalV1Pool.sol";

contract MarginalV1Pool is IMarginalV1Pool, ERC20 {
    using Position for mapping(bytes32 => Position.Info);
    using Position for Position.Info;
    using SafeCast for uint256;

    address public immutable factory;
    address public immutable oracle;

    address public immutable token0;
    address public immutable token1;
    uint24 public immutable maintenance;

    uint24 public constant fee = 1000; // 10 bps across all pools
    uint24 public constant reward = 50000; // 5% of size added to min margin reqs

    uint32 public constant secondsAgo = 43200; // 12 hr TWAP for oracle price
    uint32 public constant fundingPeriod = 604800; // 7 day funding period

    // @dev Pool state represented in (L, sqrtP) space
    struct State {
        uint128 liquidity;
        uint160 sqrtPriceX96;
        int24 tick;
        uint32 blockTimestamp;
        int56 tickCumulative;
        uint104 totalPositions; // > ~ 5e22 years at max per block to fill on mainnet
        uint8 feeProtocol;
    }
    State public state;

    struct ReservesLocked {
        uint128 token0;
        uint128 token1;
    }
    ReservesLocked public reservesLocked;

    struct ProtocolFees {
        uint128 token0;
        uint128 token1;
    }
    ProtocolFees public protocolFees;

    mapping(bytes32 => Position.Info) public positions;

    uint256 private unlocked = 1; // uses OZ convention of 1 for false and 2 for true
    modifier lock() {
        require(unlocked == 2, "locked");
        unlocked = 1;
        _;
        unlocked = 2;
    }

    modifier onlyFactoryOwner() {
        require(
            msg.sender == IMarginalV1Factory(factory).owner(),
            "not factory owner"
        );
        _;
    }

    event Initialize(uint160 sqrtPriceX96, int24 tick);
    event Open(
        address sender,
        address indexed owner,
        uint256 indexed id,
        uint128 liquidityAfter,
        uint160 sqrtPriceX96After,
        uint128 margin
    );
    event Adjust(
        address indexed owner,
        uint256 indexed id,
        address recipient,
        uint256 marginAfter
    );
    event Settle(
        address indexed owner,
        uint256 indexed id,
        address recipient,
        uint128 liquidityAfter,
        uint160 sqrtPriceX96After,
        int256 amount0,
        int256 amount1
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
    event Swap(
        address indexed sender,
        address indexed recipient,
        int256 amount0,
        int256 amount1,
        uint160 sqrtPriceX96,
        uint128 liquidity,
        int24 tick
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
    event SetFeeProtocol(uint8 oldFeeProtocol, uint8 newFeeProtocol);
    event CollectProtocol(
        address sender,
        address indexed recipient,
        uint128 amount0,
        uint128 amount1
    );

    constructor() ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        (
            factory,
            token0,
            token1,
            maintenance,
            oracle
        ) = IMarginalV1PoolDeployer(msg.sender).params();
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
            totalPositions: 0,
            feeProtocol: 0
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
        // TODO: oracle buffers?
        (int56[] memory tickCumulatives, ) = IUniswapV3Pool(oracle).observe(
            secondsAgos
        );
        return tickCumulatives;
    }

    function stateSynced() private view returns (State memory) {
        State memory _state = state;
        // oracle update
        _state.tickCumulative +=
            int56(_state.tick) *
            int56(uint56(_blockTimestamp() - _state.blockTimestamp)); // TODO: think thru overflow
        _state.blockTimestamp = _blockTimestamp();
        return _state;
    }

    function open(
        address recipient,
        bool zeroForOne,
        uint128 liquidityDelta,
        uint160 sqrtPriceLimitX96,
        uint128 margin,
        bytes calldata data
    ) external lock returns (uint256 id) {
        State memory _state = stateSynced();
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

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextOpen(
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
        uint128 marginMinimum = position.marginMinimum(maintenance);
        require(margin >= marginMinimum, "margin < min");

        _state.liquidity -= liquidityDelta;
        _state.sqrtPriceX96 = sqrtPriceX96Next;

        (uint128 amount0Locked, uint128 amount1Locked) = position
            .amountsLocked();
        reservesLocked.token0 += amount0Locked;
        reservesLocked.token1 += amount1Locked;

        // callback for margin amount
        if (!zeroForOne) {
            // long token0 (out) relative to token1 (in); margin in token0
            uint256 fees0 = Position.fees(position.size, fee);
            uint256 rewards0 = Position.liquidationRewards(
                position.size,
                reward
            );
            uint256 amount0 = uint256(margin) + fees0 + rewards0;

            uint256 balance0Before = balance0();
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                amount0,
                0,
                data
            );
            require(balance0Before + amount0 <= balance0(), "amount0 < min");

            position.margin = margin;
            position.rewards = uint128(rewards0);

            // account for protocol fees if fee on
            if (_state.feeProtocol > 0) {
                uint256 delta = fees0 / _state.feeProtocol;
                fees0 -= delta;
                protocolFees.token0 += uint128(delta);
            }

            // fees added to available liquidity
            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    int256(fees0),
                    0
                );
            _state.liquidity = liquidityAfter;
            _state.sqrtPriceX96 = sqrtPriceX96After;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
        } else {
            // long token1 (out) relative to token0 (in); margin in token1
            uint256 fees1 = Position.fees(position.size, fee);
            uint256 rewards1 = Position.liquidationRewards(
                position.size,
                reward
            );
            uint256 amount1 = uint256(margin) + fees1 + rewards1;

            uint256 balance1Before = balance1();
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                0,
                amount1,
                data
            );
            require(balance1Before + amount1 <= balance1(), "amount1 < min");

            position.margin = margin;
            position.rewards = uint128(rewards1);

            // account for protocol fees if fee on
            if (_state.feeProtocol > 0) {
                uint256 delta = fees1 / _state.feeProtocol;
                fees1 -= delta;
                protocolFees.token1 += uint128(delta);
            }

            // fees added to available liquidity
            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    0,
                    int256(fees1)
                );
            _state.liquidity = liquidityAfter;
            _state.sqrtPriceX96 = sqrtPriceX96After;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
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
            margin
        );
    }

    function adjust(
        address recipient,
        uint112 id,
        int256 marginDelta,
        bytes calldata data
    ) external lock returns (uint256 margin0, uint256 margin1) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(msg.sender, id);
        require(position.size > 0, "not position");

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        // update debts for funding
        position = position.sync(
            _state.tickCumulative,
            oracleTickCumulative,
            fundingPeriod
        );
        uint128 marginMinimum = position.marginMinimum(maintenance);
        require(
            marginDelta > 0 ||
                uint256(position.margin) >=
                uint256(-marginDelta) + uint256(marginMinimum),
            "margin < min"
        );

        // flash margin out then callback for margin in
        if (!position.zeroForOne) {
            margin0 = uint256(int256(uint256(position.margin)) + marginDelta);
            TransferHelper.safeTransfer(token0, recipient, position.margin);

            uint256 balance0Before = balance0();
            IMarginalV1AdjustCallback(msg.sender).marginalV1AdjustCallback(
                margin0,
                0,
                data
            );
            require(balance0Before + margin0 <= balance0(), "amount0 < min");
            position.margin = margin0.toUint128(); // safecast to avoid issues on liquidation
        } else {
            margin1 = uint256(int256(uint256(position.margin)) + marginDelta);
            TransferHelper.safeTransfer(token1, recipient, position.margin);

            uint256 balance1Before = balance1();
            IMarginalV1AdjustCallback(msg.sender).marginalV1AdjustCallback(
                0,
                margin1,
                data
            );
            require(balance1Before + margin1 <= balance1(), "amount1 < min");
            position.margin = margin1.toUint128(); // safecast to avoid issues on liquidation
        }

        positions.set(msg.sender, id, position);

        // update pool state to latest
        state = _state;

        emit Adjust(msg.sender, uint256(id), recipient, position.margin);
    }

    function settle(
        address recipient,
        uint112 id,
        bytes calldata data
    ) external lock returns (int256 amount0, int256 amount1) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(msg.sender, id);
        require(position.size > 0, "not position");

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        // update debts for funding
        position = position.sync(
            _state.tickCumulative,
            oracleTickCumulative,
            fundingPeriod
        );

        (uint128 amount0Unlocked, uint128 amount1Unlocked) = position
            .amountsLocked();
        reservesLocked.token0 -= amount0Unlocked;
        reservesLocked.token1 -= amount1Unlocked;

        // flash size + margin + rewards out then callback for debt owed in
        if (!position.zeroForOne) {
            amount0 = -int256(
                uint256(position.size) +
                    uint256(position.margin) +
                    uint256(position.rewards)
            ); // size + margin + rewards out
            amount1 = int256(uint256(position.debt1)); // debt in

            if (amount0 < 0)
                TransferHelper.safeTransfer(
                    token0,
                    recipient,
                    uint256(-amount0)
                );

            (uint128 liquidityNext, uint160 sqrtPriceX96Next) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    int256(uint256(amount0Unlocked - position.size)), // insurance0 + debt0
                    int256(uint256(amount1Unlocked)) + amount1 // insurance1 + debt1
                );
            _state.liquidity = liquidityNext;
            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);

            uint256 balance1Before = balance1();
            IMarginalV1SettleCallback(msg.sender).marginalV1SettleCallback(
                amount0,
                amount1,
                data
            );
            require(
                balance1Before + uint256(amount1) <= balance1(),
                "amount1 < min"
            );
        } else {
            amount0 = int256(uint256(position.debt0)); // debt in
            amount1 = -int256(
                uint256(position.size) +
                    uint256(position.margin) +
                    uint256(position.rewards)
            ); // size + margin + rewards out

            if (amount1 < 0)
                TransferHelper.safeTransfer(
                    token1,
                    recipient,
                    uint256(-amount1)
                );

            (uint128 liquidityNext, uint160 sqrtPriceX96Next) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    int256(uint256(amount0Unlocked)) + amount0, // insurance0 + debt0
                    int256(uint256(amount1Unlocked - position.size)) // insurance1 + debt1
                );
            _state.liquidity = liquidityNext;
            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);

            uint256 balance0Before = balance0();
            IMarginalV1SettleCallback(msg.sender).marginalV1SettleCallback(
                amount0,
                amount1,
                data
            );
            require(
                balance0Before + uint256(amount0) <= balance0(),
                "amount0 < min"
            );
        }

        positions.set(msg.sender, id, position.settle());

        // update pool state to latest
        state = _state;

        emit Settle(
            msg.sender,
            uint256(id),
            recipient,
            _state.liquidity,
            _state.sqrtPriceX96,
            amount0,
            amount1
        );
    }

    function liquidate(
        address recipient,
        address owner,
        uint112 id
    ) external lock returns (uint256 rewards0, uint256 rewards1) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(owner, id);
        require(position.size > 0, "not position");

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

        // update debts for funding
        position = position.sync(
            _state.tickCumulative,
            oracleTickCumulativesLast[1], // zero seconds ago
            fundingPeriod
        );

        require(
            !position.safe(oracleSqrtPriceX96, maintenance),
            "position safe"
        );

        (uint128 amount0, uint128 amount1) = position.amountsLocked();
        reservesLocked.token0 -= amount0;
        reservesLocked.token1 -= amount1;

        if (!position.zeroForOne) {
            rewards0 = uint256(position.rewards);
            amount0 += position.margin;

            (uint128 liquidityNext, uint160 sqrtPriceX96Next) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    int256(uint256(amount0)),
                    int256(uint256(amount1))
                );
            _state.liquidity = liquidityNext;
            _state.sqrtPriceX96 = sqrtPriceX96Next;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);
        } else {
            rewards1 = uint256(position.rewards);
            amount1 += position.margin;

            (uint128 liquidityNext, uint160 sqrtPriceX96Next) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    int256(uint256(amount0)),
                    int256(uint256(amount1))
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

    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external lock returns (int256 amount0, int256 amount1) {
        State memory _state = stateSynced();
        require(amountSpecified != 0, "amountSpecified == 0");
        require(
            zeroForOne
                ? sqrtPriceLimitX96 < _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO
                : sqrtPriceLimitX96 > _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO,
            "sqrtPriceLimitX96 exceeds min/max"
        );

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            _state.liquidity,
            _state.sqrtPriceX96,
            zeroForOne,
            amountSpecified
        );
        require(
            zeroForOne
                ? sqrtPriceX96Next >= sqrtPriceLimitX96
                : sqrtPriceX96Next <= sqrtPriceLimitX96,
            "sqrtPriceX96Next exceeds sqrtPriceLimitX96"
        );

        // amounts without fees
        (amount0, amount1) = SwapMath.swapAmounts(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next
        );

        // optimistic amount out with callback for amount in
        if (!zeroForOne) {
            if (amount0 < 0)
                TransferHelper.safeTransfer(
                    token0,
                    recipient,
                    uint256(-amount0)
                );

            uint256 fees1 = SwapMath.swapFees(uint256(amount1), fee);
            amount1 += int256(fees1);

            uint256 balance1Before = balance1();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            require(
                balance1Before + uint256(amount1) <= balance1(),
                "amount1 < min"
            );

            // account for protocol fees if fee on
            if (_state.feeProtocol > 0) {
                uint256 delta = fees1 / _state.feeProtocol;
                amount1 -= int256(delta);
                protocolFees.token1 += uint128(delta);
            }

            // update state liquidity, sqrt price accounting for fee growth
            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    amount0,
                    amount1
                );
            _state.liquidity = liquidityAfter;
            _state.sqrtPriceX96 = sqrtPriceX96After;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
        } else {
            if (amount1 < 0)
                TransferHelper.safeTransfer(
                    token1,
                    recipient,
                    uint256(-amount1)
                );

            uint256 fees0 = SwapMath.swapFees(uint256(amount0), fee);
            amount0 += int256(fees0);

            uint256 balance0Before = balance0();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            require(
                balance0Before + uint256(amount0) <= balance0(),
                "amount0 < min"
            );

            // account for protocol fees if fee on
            if (_state.feeProtocol > 0) {
                uint256 delta = fees0 / _state.feeProtocol;
                amount0 -= int256(delta);
                protocolFees.token0 += uint128(delta);
            }

            // update state liquidity, sqrt price accounting for fee growth
            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    amount0,
                    amount1
                );
            _state.liquidity = liquidityAfter;
            _state.sqrtPriceX96 = sqrtPriceX96After;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
        }

        // update pool state to latest
        state = _state;

        emit Swap(
            msg.sender,
            recipient,
            amount0,
            amount1,
            _state.sqrtPriceX96,
            _state.liquidity,
            _state.tick
        );
    }

    function mint(
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) external lock returns (uint256 amount0, uint256 amount1) {
        State memory _state = stateSynced();
        uint256 _totalSupply = totalSupply();
        require(liquidityDelta > 0, "liquidityDelta == 0");

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96
        );

        // total liquidity is available liquidity if all locked reserves were returned to pool
        (uint128 totalLiquidityAfter, ) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                _state.liquidity,
                _state.sqrtPriceX96,
                int256(uint256(reservesLocked.token0 + amount0)),
                int256(uint256(reservesLocked.token1 + amount1))
            );
        uint256 shares = _totalSupply == 0
            ? totalLiquidityAfter
            : Math.mulDiv(
                _totalSupply,
                liquidityDelta,
                totalLiquidityAfter - liquidityDelta
            );

        _state.liquidity += liquidityDelta;

        // callback for amounts owed
        uint256 balance0Before = balance0();
        uint256 balance1Before = balance1();
        IMarginalV1MintCallback(msg.sender).marginalV1MintCallback(
            amount0,
            amount1,
            data
        );
        require(balance0Before + amount0 <= balance0(), "amount0 < min");
        require(balance1Before + amount1 <= balance1(), "amount1 < min");

        // update pool state to latest
        state = _state;

        // TODO: min liquidity lock?
        _mint(recipient, shares);

        emit Mint(msg.sender, recipient, liquidityDelta, amount0, amount1);
    }

    /// @dev Reverts if not enough liquidity available to exit due to outstanding positions
    function burn(
        address recipient,
        uint256 shares
    ) external lock returns (uint256 amount0, uint256 amount1) {
        State memory _state = stateSynced();
        uint256 _totalSupply = totalSupply();
        require(shares > 0 && shares <= _totalSupply, "shares exceeds min/max");

        // total liquidity is available liquidity if all locked reserves were returned to pool
        (uint256 totalLiquidityBefore, ) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                _state.liquidity,
                _state.sqrtPriceX96,
                int256(uint256(reservesLocked.token0)),
                int256(uint256(reservesLocked.token1))
            );
        uint128 liquidityDelta = uint128(
            Math.mulDiv(totalLiquidityBefore, shares, _totalSupply)
        );
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

    function setFeeProtocol(uint8 feeProtocol) external lock onlyFactoryOwner {
        require(
            feeProtocol == 0 || (feeProtocol >= 4 && feeProtocol <= 10),
            "protocolFees exceed min/max"
        );
        emit SetFeeProtocol(state.feeProtocol, feeProtocol);
        state.feeProtocol = feeProtocol;
    }

    function collectProtocol(
        address recipient
    )
        external
        lock
        onlyFactoryOwner
        returns (uint128 amount0, uint128 amount1)
    {
        require(
            protocolFees.token0 > 0 && protocolFees.token1 > 0,
            "protocolFees < min"
        );
        amount0 = protocolFees.token0 - 1; // ensure slot not cleared for gas savings
        amount1 = protocolFees.token1 - 1;

        if (amount0 > 0) {
            protocolFees.token0 -= amount0;
            TransferHelper.safeTransfer(token0, recipient, amount0);
        }
        if (amount1 > 0) {
            protocolFees.token1 -= amount1;
            TransferHelper.safeTransfer(token1, recipient, amount1);
        }

        emit CollectProtocol(msg.sender, recipient, amount0, amount1);
    }
}

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
        uint96 totalPositions; // > ~ 2e20 years at max per block to fill on mainnet
        uint8 feeProtocol;
        bool initialized;
    }
    State public state;

    uint128 public liquidityLocked;

    struct ProtocolFees {
        uint128 token0;
        uint128 token1;
    }
    ProtocolFees public protocolFees;

    mapping(bytes32 => Position.Info) public positions;

    uint256 private unlocked = 1; // uses OZ convention of 1 for false and 2 for true
    modifier lock() {
        if (unlocked == 1) revert Locked();
        unlocked = 1;
        _;
        unlocked = 2;
    }

    modifier onlyFactoryOwner() {
        if (msg.sender != IMarginalV1Factory(factory).owner())
            revert Unauthorized();
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

    error Locked();
    error Unauthorized();
    error Initialized();
    error InvalidLiquidityDelta();
    error InvalidSqrtPriceLimitX96();
    error SqrtPriceX96ExceedsLimit(uint160 sqrtPriceX96Next);
    error MarginLessThanMin(uint128 marginMinimum);
    error Amount0LessThanMin();
    error Amount1LessThanMin();
    error InvalidPosition();
    error PositionSafe();
    error InvalidAmountSpecified();
    error InvalidShares();
    error InvalidFeeProtocol();

    constructor() ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        (
            factory,
            token0,
            token1,
            maintenance,
            oracle
        ) = IMarginalV1PoolDeployer(msg.sender).params();

        // reverts if not enough historical observations
        // TODO: enough of a check on hist obs?
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;
        oracleTickCumulatives(secondsAgos);
    }

    function initialize(uint160 _sqrtPriceX96) external {
        if (state.sqrtPriceX96 > 0) revert Initialized();
        int24 tick = TickMath.getTickAtSqrtRatio(_sqrtPriceX96);
        state = State({
            liquidity: 0,
            sqrtPriceX96: _sqrtPriceX96,
            tick: tick,
            blockTimestamp: _blockTimestamp(),
            tickCumulative: 0,
            totalPositions: 0,
            feeProtocol: 0,
            initialized: true
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
    ) external lock returns (uint256 id, uint256 size, uint256 debt) {
        State memory _state = stateSynced();
        if (liquidityDelta >= _state.liquidity) revert InvalidLiquidityDelta(); // TODO: min liquidity, min liquidity delta (size)
        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert InvalidSqrtPriceLimitX96();

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextOpen(
            _state.liquidity,
            _state.sqrtPriceX96,
            liquidityDelta,
            zeroForOne,
            maintenance
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert SqrtPriceX96ExceedsLimit(sqrtPriceX96Next);

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        Position.Info memory position = Position.assemble(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne,
            _state.tick,
            _state.tickCumulative,
            oracleTickCumulative
        );
        if (
            position.size == 0 ||
            (zeroForOne ? position.debt0 == 0 : position.debt1 == 0)
        ) revert InvalidPosition(); // TODO: test

        uint128 marginMinimum = position.marginMinimum(maintenance);
        if (margin < marginMinimum) revert MarginLessThanMin(marginMinimum);
        position.margin = margin;

        _state.liquidity -= liquidityDelta;
        _state.sqrtPriceX96 = sqrtPriceX96Next;

        liquidityLocked += liquidityDelta;

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
            if (balance0Before + amount0 > balance0())
                revert Amount0LessThanMin();

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
            if (balance1Before + amount1 > balance1())
                revert Amount1LessThanMin();

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
        size = position.size;
        debt = zeroForOne ? position.debt0 : position.debt1;

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
        uint96 id,
        int128 marginDelta,
        bytes calldata data
    ) external lock returns (uint256 margin0, uint256 margin1) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(msg.sender, id);
        if (position.size == 0) revert InvalidPosition();

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        // update debts for funding
        position = position.sync(
            _state.tickCumulative,
            oracleTickCumulative,
            fundingPeriod
        );
        uint128 marginMinimum = position.marginMinimum(maintenance);
        if (
            !(marginDelta > 0 ||
                uint256(position.margin) >=
                uint256(uint128(-marginDelta)) + uint256(marginMinimum))
        ) revert MarginLessThanMin(marginMinimum);

        // flash margin out then callback for margin in
        if (!position.zeroForOne) {
            margin0 = uint256(
                int256(uint256(position.margin)) + int256(marginDelta)
            );
            TransferHelper.safeTransfer(token0, recipient, position.margin);

            uint256 balance0Before = balance0();
            IMarginalV1AdjustCallback(msg.sender).marginalV1AdjustCallback(
                margin0,
                0,
                data
            );
            if (balance0Before + margin0 > balance0())
                revert Amount0LessThanMin();

            position.margin = margin0.toUint128();
        } else {
            margin1 = uint256(
                int256(uint256(position.margin)) + int256(marginDelta)
            );
            TransferHelper.safeTransfer(token1, recipient, position.margin);

            uint256 balance1Before = balance1();
            IMarginalV1AdjustCallback(msg.sender).marginalV1AdjustCallback(
                0,
                margin1,
                data
            );
            if (balance1Before + margin1 > balance1())
                revert Amount1LessThanMin();

            position.margin = margin1.toUint128();
        }

        positions.set(msg.sender, id, position);

        // update pool state to latest
        state = _state;

        emit Adjust(msg.sender, uint256(id), recipient, position.margin);
    }

    function settle(
        address recipient,
        uint96 id,
        bytes calldata data
    ) external lock returns (int256 amount0, int256 amount1) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(msg.sender, id);
        if (position.size == 0) revert InvalidPosition();

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        // update debts for funding
        position = position.sync(
            _state.tickCumulative,
            oracleTickCumulative,
            fundingPeriod
        );

        liquidityLocked -= position.liquidityLocked;
        (uint128 amount0Unlocked, uint128 amount1Unlocked) = position
            .amountsLocked(); // TODO: fix for edge of margin => infty as overflows?

        // flash size + margin + rewards out then callback for debt owed in
        if (!position.zeroForOne) {
            uint256 rewards0 = Position.liquidationRewards(
                position.size,
                reward
            );
            amount0 = -int256(
                uint256(position.size) + uint256(position.margin) + rewards0
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
                    int256(
                        uint256(
                            amount0Unlocked - position.size - position.margin
                        )
                    ), // insurance0 + debt0
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
            if (balance1Before + uint256(amount1) > balance1())
                revert Amount1LessThanMin();
        } else {
            uint256 rewards1 = Position.liquidationRewards(
                position.size,
                reward
            );

            amount0 = int256(uint256(position.debt0)); // debt in
            amount1 = -int256(
                uint256(position.size) + uint256(position.margin) + rewards1
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
                    int256(
                        uint256(
                            amount1Unlocked - position.size - position.margin
                        )
                    ) // insurance1 + debt1
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
            if (balance0Before + uint256(amount0) > balance0())
                revert Amount0LessThanMin();
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
        uint96 id
    ) external lock returns (uint256 rewards0, uint256 rewards1) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(owner, id);
        if (position.size == 0) revert InvalidPosition();

        // oracle price averaged over seconds ago for liquidation calc
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;

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
        if (position.safe(oracleSqrtPriceX96, maintenance))
            revert PositionSafe();

        liquidityLocked -= position.liquidityLocked;
        (uint128 amount0, uint128 amount1) = position.amountsLocked();

        if (!position.zeroForOne) {
            rewards0 = Position.liquidationRewards(position.size, reward);
        } else {
            rewards1 = Position.liquidationRewards(position.size, reward);
        }

        (_state.liquidity, _state.sqrtPriceX96) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                _state.liquidity,
                _state.sqrtPriceX96,
                int256(uint256(amount0)),
                int256(uint256(amount1))
            );
        _state.tick = TickMath.getTickAtSqrtRatio(_state.sqrtPriceX96);

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
        if (amountSpecified == 0) revert InvalidAmountSpecified();
        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > _state.sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert InvalidSqrtPriceLimitX96();

        // add fees back in after swap calcs if exact input
        bool exactInput = amountSpecified > 0;
        int256 amountSpecifiedLessFee = exactInput
            ? amountSpecified -
                int256(SwapMath.swapFees(uint256(amountSpecified), fee))
            : amountSpecified;

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            _state.liquidity,
            _state.sqrtPriceX96,
            zeroForOne,
            amountSpecifiedLessFee
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert SqrtPriceX96ExceedsLimit(sqrtPriceX96Next);

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

            uint256 fees1 = exactInput
                ? uint256(amountSpecified) - uint256(amount1) // TODO: check never negative
                : SwapMath.swapFees(uint256(amount1), fee);
            amount1 += int256(fees1);

            uint256 balance1Before = balance1();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            if (balance1Before + uint256(amount1) > balance1())
                revert Amount1LessThanMin();

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

            uint256 fees0 = exactInput
                ? uint256(amountSpecified) - uint256(amount0) // TODO: check never negative
                : SwapMath.swapFees(uint256(amount0), fee);
            amount0 += int256(fees0);

            uint256 balance0Before = balance0();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            if (balance0Before + uint256(amount0) > balance0())
                revert Amount0LessThanMin();

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
    ) external lock returns (uint256 shares, uint256 amount0, uint256 amount1) {
        State memory _state = stateSynced();
        uint256 _totalSupply = totalSupply();
        if (liquidityDelta == 0) revert InvalidLiquidityDelta();

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96
        );

        // total liquidity is available liquidity if all locked liquidity was returned to pool
        // TODO: verify no edge cases where _totalSupply == 0 but totalLiquidityAfter == liquidityDelta?
        uint128 totalLiquidityAfter = _state.liquidity +
            liquidityLocked +
            liquidityDelta;
        shares = _totalSupply == 0
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
        if (balance0Before + amount0 > balance0()) revert Amount0LessThanMin();
        if (balance1Before + amount1 > balance1()) revert Amount1LessThanMin();

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
    )
        external
        lock
        returns (uint128 liquidityDelta, uint256 amount0, uint256 amount1)
    {
        State memory _state = stateSynced();
        uint256 _totalSupply = totalSupply();
        if (shares == 0 || shares > _totalSupply) revert InvalidShares();

        // total liquidity is available liquidity if all locked liquidity were returned to pool
        uint128 totalLiquidityBefore = _state.liquidity + liquidityLocked;
        liquidityDelta = uint128(
            Math.mulDiv(totalLiquidityBefore, shares, _totalSupply)
        );
        if (liquidityDelta > _state.liquidity) revert InvalidLiquidityDelta();

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
        if (!(feeProtocol == 0 || (feeProtocol >= 4 && feeProtocol <= 10)))
            revert InvalidFeeProtocol();
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
        if (protocolFees.token0 == 0 || protocolFees.token1 == 0)
            revert InvalidFeeProtocol();
        amount0 = protocolFees.token0 - 1; // ensure slot not cleared for gas savings
        amount1 = protocolFees.token1 - 1;

        protocolFees.token0 -= amount0;
        TransferHelper.safeTransfer(token0, recipient, amount0);

        protocolFees.token1 -= amount1;
        TransferHelper.safeTransfer(token1, recipient, amount1);

        emit CollectProtocol(msg.sender, recipient, amount0, amount1);
    }
}

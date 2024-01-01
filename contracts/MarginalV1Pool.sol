// SPDX-License-Identifier: AGPL-3.0
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
import {IMarginalV1Pool} from "./interfaces/IMarginalV1Pool.sol";

contract MarginalV1Pool is IMarginalV1Pool, ERC20 {
    using Position for mapping(bytes32 => Position.Info);
    using Position for Position.Info;
    using SafeCast for uint256;

    /// @inheritdoc IMarginalV1Pool
    address public immutable factory;
    /// @inheritdoc IMarginalV1Pool
    address public immutable oracle;

    /// @inheritdoc IMarginalV1Pool
    address public immutable token0;
    /// @inheritdoc IMarginalV1Pool
    address public immutable token1;
    /// @inheritdoc IMarginalV1Pool
    uint24 public immutable maintenance;

    /// @inheritdoc IMarginalV1Pool
    uint24 public constant fee = 1000; // 10 bps across all pools
    /// @inheritdoc IMarginalV1Pool
    uint24 public constant rewardPremium = 2000000; // 2x base fee as liquidation rewards
    /// @inheritdoc IMarginalV1Pool
    uint24 public constant tickCumulativeRateMax = 920; // bound on funding rate of ~10% per funding period

    /// @inheritdoc IMarginalV1Pool
    uint32 public constant secondsAgo = 43200; // 12 hr TWAP for oracle price
    /// @inheritdoc IMarginalV1Pool
    uint32 public constant fundingPeriod = 604800; // 7 day funding period

    // @dev varies for different chains
    uint256 internal constant blockBaseFeeMin = 40e9; // min base fee for liquidation rewards
    uint256 internal constant gasLiquidate = 150000; // gas required to call liquidate

    uint128 internal constant MINIMUM_LIQUIDITY = 10000; // liquidity locked on initial mint always available for swaps
    uint128 internal constant MINIMUM_SIZE = 10000; // minimum position size, debt, insurance amounts to prevent dust sizes

    struct State {
        uint160 sqrtPriceX96;
        uint96 totalPositions; // > ~ 2e20 years at max per block to fill on mainnet
        uint128 liquidity;
        int24 tick;
        uint32 blockTimestamp;
        int56 tickCumulative;
        uint8 feeProtocol;
        bool initialized;
    }
    /// @inheritdoc IMarginalV1Pool
    State public state;

    /// @inheritdoc IMarginalV1Pool
    uint128 public liquidityLocked;

    struct ProtocolFees {
        uint128 token0;
        uint128 token1;
    }
    /// @inheritdoc IMarginalV1Pool
    ProtocolFees public protocolFees;

    /// @inheritdoc IMarginalV1Pool
    mapping(bytes32 => Position.Info) public positions;

    uint256 private unlocked = 2; // uses OZ convention of 1 for false and 2 for true
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
        int256 amount1,
        uint256 rewards
    );
    event Liquidate(
        address indexed owner,
        uint256 indexed id,
        address recipient,
        uint128 liquidityAfter,
        uint160 sqrtPriceX96After,
        uint256 rewards
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
    error InvalidLiquidityDelta();
    error InvalidSqrtPriceLimitX96();
    error SqrtPriceX96ExceedsLimit();
    error MarginLessThanMin();
    error RewardsLessThanMin();
    error Amount0LessThanMin();
    error Amount1LessThanMin();
    error InvalidPosition();
    error PositionSafe();
    error InvalidAmountSpecified();
    error InvalidFeeProtocol();

    constructor(
        address _factory,
        address _token0,
        address _token1,
        uint24 _maintenance,
        address _oracle
    ) ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        factory = _factory;
        token0 = _token0;
        token1 = _token1;
        maintenance = _maintenance;
        oracle = _oracle;
    }

    function initialize() private {
        // reverts if not enough historical observations
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;
        int56[] memory oracleTickCumulativesLast = oracleTickCumulatives(
            secondsAgos
        );

        // use oracle price to initialize
        uint160 _sqrtPriceX96 = OracleLibrary.oracleSqrtPriceX96(
            OracleLibrary.oracleTickCumulativeDelta(
                oracleTickCumulativesLast[0],
                oracleTickCumulativesLast[1]
            ),
            secondsAgo
        );
        int24 tick = TickMath.getTickAtSqrtRatio(_sqrtPriceX96);

        state = State({
            sqrtPriceX96: _sqrtPriceX96,
            totalPositions: 0,
            liquidity: 0,
            tick: tick,
            blockTimestamp: _blockTimestamp(),
            tickCumulative: 0,
            feeProtocol: 0,
            initialized: true
        });
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

    function stateSynced() private view returns (State memory) {
        State memory _state = state;
        // oracle update
        unchecked {
            uint32 delta = _blockTimestamp() - _state.blockTimestamp;
            if (delta == 0) return _state; // early exit if nothing to update
            _state.tickCumulative += int56(_state.tick) * int56(uint56(delta)); // overflow desired
            _state.blockTimestamp = _blockTimestamp();
        }
        return _state;
    }

    /// @inheritdoc IMarginalV1Pool
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
        lock
        returns (
            uint256 id,
            uint256 size,
            uint256 debt,
            uint256 amount0,
            uint256 amount1
        )
    {
        State memory _state = stateSynced();
        if (
            liquidityDelta == 0 ||
            liquidityDelta + MINIMUM_LIQUIDITY >= _state.liquidity
        ) revert InvalidLiquidityDelta();
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
        ) revert SqrtPriceX96ExceedsLimit();

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        Position.Info memory position = Position.assemble(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne,
            _state.tick,
            _state.blockTimestamp,
            _state.tickCumulative,
            oracleTickCumulative
        );
        if (
            position.size < MINIMUM_SIZE ||
            position.debt0 < MINIMUM_SIZE ||
            position.debt1 < MINIMUM_SIZE ||
            position.insurance0 < MINIMUM_SIZE ||
            position.insurance1 < MINIMUM_SIZE
        ) revert InvalidPosition();

        uint128 marginMinimum = position.marginMinimum(maintenance);
        if (marginMinimum == 0 || margin < marginMinimum)
            revert MarginLessThanMin();
        position.margin = margin;

        uint256 rewardsMinimum = Position.liquidationRewards(
            block.basefee,
            blockBaseFeeMin,
            gasLiquidate,
            rewardPremium
        );
        if (msg.value < rewardsMinimum) revert RewardsLessThanMin();
        position.rewards = msg.value;

        _state.liquidity -= liquidityDelta;
        _state.sqrtPriceX96 = sqrtPriceX96Next;

        liquidityLocked += liquidityDelta;

        // callback for margin amount
        if (!zeroForOne) {
            // long token0 (out) relative to token1 (in); margin in token0
            uint256 fees0 = Position.fees(position.size, fee);
            amount0 = uint256(margin) + fees0;

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
            amount1 = uint256(margin) + fees1;

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

    /// @inheritdoc IMarginalV1Pool
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
            _state.blockTimestamp,
            _state.tickCumulative,
            oracleTickCumulative,
            tickCumulativeRateMax,
            fundingPeriod
        );
        uint128 marginMinimum = position.marginMinimum(maintenance);
        if (
            int256(uint256(position.margin)) + int256(marginDelta) <
            int256(uint256(marginMinimum))
        ) revert MarginLessThanMin();

        // flash margin out then callback for margin in
        if (!position.zeroForOne) {
            margin0 = uint256(
                int256(uint256(position.margin)) + int256(marginDelta)
            ); // position margin after
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
            ); // position margin after
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

    /// @inheritdoc IMarginalV1Pool
    function settle(
        address recipient,
        uint96 id,
        bytes calldata data
    ) external lock returns (int256 amount0, int256 amount1, uint256 rewards) {
        State memory _state = stateSynced();
        Position.Info memory position = positions.get(msg.sender, id);
        if (position.size == 0) revert InvalidPosition();

        // zero seconds ago for oracle tickCumulative
        int56 oracleTickCumulative = oracleTickCumulatives(new uint32[](1))[0];

        // update debts for funding
        position = position.sync(
            _state.blockTimestamp,
            _state.tickCumulative,
            oracleTickCumulative,
            tickCumulativeRateMax,
            fundingPeriod
        );

        liquidityLocked -= position.liquidityLocked;
        (uint256 amount0Unlocked, uint256 amount1Unlocked) = position
            .amountsLocked();

        // flash size + margin + rewards out then callback for debt owed in
        rewards = position.rewards;
        TransferHelper.safeTransferETH(recipient, rewards); // ok given lock

        if (!position.zeroForOne) {
            amount0 = -int256(
                uint256(position.size) + uint256(position.margin)
            ); // size + margin out
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
                        amount0Unlocked -
                            uint256(position.size) -
                            uint256(position.margin)
                    ), // insurance0 + debt0
                    int256(amount1Unlocked) + amount1 // insurance1 + debt1
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
            amount0 = int256(uint256(position.debt0)); // debt in
            amount1 = -int256(
                uint256(position.size) + uint256(position.margin)
            ); // size + margin out

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
                    int256(amount0Unlocked) + amount0, // insurance0 + debt0
                    int256(
                        amount1Unlocked -
                            uint256(position.size) -
                            uint256(position.margin)
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
            amount1,
            rewards
        );
    }

    /// @inheritdoc IMarginalV1Pool
    function liquidate(
        address recipient,
        address owner,
        uint96 id
    ) external lock returns (uint256 rewards) {
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
            OracleLibrary.oracleTickCumulativeDelta(
                oracleTickCumulativesLast[0],
                oracleTickCumulativesLast[1]
            ),
            secondsAgo
        );

        // update debts for funding
        position = position.sync(
            _state.blockTimestamp,
            _state.tickCumulative,
            oracleTickCumulativesLast[1], // zero seconds ago
            tickCumulativeRateMax,
            fundingPeriod
        );
        if (position.safe(oracleSqrtPriceX96, maintenance))
            revert PositionSafe();

        liquidityLocked -= position.liquidityLocked;
        (uint256 amount0, uint256 amount1) = position.amountsLocked();

        (_state.liquidity, _state.sqrtPriceX96) = LiquidityMath
            .liquiditySqrtPriceX96Next(
                _state.liquidity,
                _state.sqrtPriceX96,
                int256(amount0),
                int256(amount1)
            );
        _state.tick = TickMath.getTickAtSqrtRatio(_state.sqrtPriceX96);

        rewards = position.rewards;
        TransferHelper.safeTransferETH(recipient, rewards); // ok given lock

        positions.set(owner, id, position.liquidate());

        // update pool state to latest
        state = _state;

        emit Liquidate(
            owner,
            uint256(id),
            recipient,
            _state.liquidity,
            _state.sqrtPriceX96,
            rewards
        );
    }

    /// @inheritdoc IMarginalV1Pool
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
                int256(SwapMath.swapFees(uint256(amountSpecified), fee, false))
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
        ) revert SqrtPriceX96ExceedsLimit();

        // amounts without fees
        (amount0, amount1) = SwapMath.swapAmounts(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next
        );

        // optimistic amount out with callback for amount in
        if (!zeroForOne) {
            amount0 = !exactInput ? amountSpecified : amount0; // in case of rounding issues
            if (amount0 < 0)
                TransferHelper.safeTransfer(
                    token0,
                    recipient,
                    uint256(-amount0)
                );

            uint256 fees1 = exactInput
                ? uint256(amountSpecified) - uint256(amount1)
                : SwapMath.swapFees(uint256(amount1), fee, true);
            amount1 += int256(fees1);

            uint256 balance1Before = balance1();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            if (amount1 == 0 || balance1Before + uint256(amount1) > balance1())
                revert Amount1LessThanMin();

            // account for protocol fees if fee on
            uint256 delta = _state.feeProtocol > 0
                ? fees1 / _state.feeProtocol
                : 0;
            if (delta > 0) protocolFees.token1 += uint128(delta);

            // update state liquidity, sqrt price accounting for fee growth
            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    amount0,
                    amount1 - int256(delta) // exclude protocol fees if any
                );
            _state.liquidity = liquidityAfter;
            _state.sqrtPriceX96 = sqrtPriceX96After;
            _state.tick = TickMath.getTickAtSqrtRatio(sqrtPriceX96After);
        } else {
            amount1 = !exactInput ? amountSpecified : amount1; // in case of rounding issues
            if (amount1 < 0)
                TransferHelper.safeTransfer(
                    token1,
                    recipient,
                    uint256(-amount1)
                );

            uint256 fees0 = exactInput
                ? uint256(amountSpecified) - uint256(amount0)
                : SwapMath.swapFees(uint256(amount0), fee, true);
            amount0 += int256(fees0);

            uint256 balance0Before = balance0();
            IMarginalV1SwapCallback(msg.sender).marginalV1SwapCallback(
                amount0,
                amount1,
                data
            );
            if (amount0 == 0 || balance0Before + uint256(amount0) > balance0())
                revert Amount0LessThanMin();

            // account for protocol fees if fee on
            uint256 delta = _state.feeProtocol > 0
                ? fees0 / _state.feeProtocol
                : 0;
            if (delta > 0) protocolFees.token0 += uint128(delta);

            // update state liquidity, sqrt price accounting for fee growth
            (uint128 liquidityAfter, uint160 sqrtPriceX96After) = LiquidityMath
                .liquiditySqrtPriceX96Next(
                    _state.liquidity,
                    _state.sqrtPriceX96,
                    amount0 - int256(delta), // exclude protocol fees if any
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

    /// @inheritdoc IMarginalV1Pool
    function mint(
        address recipient,
        uint128 liquidityDelta,
        bytes calldata data
    ) external lock returns (uint256 shares, uint256 amount0, uint256 amount1) {
        uint256 _totalSupply = totalSupply();

        bool initializing = (_totalSupply == 0);
        if (initializing) initialize();

        State memory _state = stateSynced();
        uint128 liquidityDeltaMinimum = (initializing ? MINIMUM_LIQUIDITY : 0);
        if (liquidityDelta <= liquidityDeltaMinimum)
            revert InvalidLiquidityDelta();

        (amount0, amount1) = LiquidityMath.toAmounts(
            liquidityDelta,
            _state.sqrtPriceX96
        );
        amount0 += 1; // rough round up on amounts in when add liquidity
        amount1 += 1;

        // total liquidity is available liquidity if all locked liquidity was returned to pool
        uint128 totalLiquidityAfter = _state.liquidity +
            liquidityLocked +
            liquidityDelta;
        shares = initializing
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

        // lock min liquidity on initial mint to avoid stuck states with price
        if (initializing) {
            shares -= uint256(MINIMUM_LIQUIDITY);
            _mint(address(this), MINIMUM_LIQUIDITY);
        }

        _mint(recipient, shares);

        emit Mint(msg.sender, recipient, liquidityDelta, amount0, amount1);
    }

    /// @inheritdoc IMarginalV1Pool
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

    /// @inheritdoc IMarginalV1Pool
    function setFeeProtocol(uint8 feeProtocol) external lock onlyFactoryOwner {
        if (!(feeProtocol == 0 || (feeProtocol >= 4 && feeProtocol <= 10)))
            revert InvalidFeeProtocol();
        emit SetFeeProtocol(state.feeProtocol, feeProtocol);
        state.feeProtocol = feeProtocol;
    }

    /// @inheritdoc IMarginalV1Pool
    function collectProtocol(
        address recipient
    )
        external
        lock
        onlyFactoryOwner
        returns (uint128 amount0, uint128 amount1)
    {
        // no zero check on protocolFees as will revert in amounts calculation
        amount0 = protocolFees.token0 - 1; // ensure slot not cleared for gas savings
        amount1 = protocolFees.token1 - 1;

        protocolFees.token0 = 1;
        TransferHelper.safeTransfer(token0, recipient, amount0);

        protocolFees.token1 = 1;
        TransferHelper.safeTransfer(token1, recipient, amount1);

        emit CollectProtocol(msg.sender, recipient, amount0, amount1);
    }
}

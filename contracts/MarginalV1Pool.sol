// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {Position} from "./libraries/Position.sol";
import {SqrtPriceMath} from "./libraries/SqrtPriceMath.sol";

import {IMarginalV1Factory} from "./interfaces/IMarginalV1Factory.sol";
import {IMarginalV1OpenCallback} from "./interfaces/callback/IMarginalV1OpenCallback.sol";

contract MarginalV1Pool is ERC20 {
    using Position for mapping(bytes32 => Position.Info);
    using SafeCast for uint256;

    address public immutable factory;

    address public immutable token0;
    address public immutable token1;

    uint24 public immutable fee;
    uint24 public immutable maintenance;

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

    mapping(bytes32 => Position.Info) public positions;

    uint256 private unlocked = 1; // uses OZ convention of 1 for false and 2 for true
    modifier lock() {
        require(unlocked == 2, "locked");
        unlocked = 1;
        _;
        unlocked = 2;
    }

    event Open(
        address sender,
        address indexed owner,
        uint112 indexed id,
        uint128 liquidityAfter,
        uint160 sqrtPriceX96After,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint128 margin
    );

    constructor() ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        (token0, token1, maintenance, fee) = IMarginalV1Factory(msg.sender)
            .params();
        factory = msg.sender;
    }

    function initialize(uint160 _sqrtPriceX96) external {
        require(state.sqrtPriceX96 == 0, "initialized");
        state = State({
            liquidity: 0,
            sqrtPriceX96: _sqrtPriceX96,
            tick: TickMath.getTickAtSqrtRatio(_sqrtPriceX96),
            blockTimestamp: _blockTimestamp(),
            tickCumulative: 0,
            totalPositions: 0
        });
        unlocked = 1;
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

    function open(
        address recipient,
        uint128 liquidityDelta,
        bool zeroForOne
    ) external lock {
        State memory _state = state;
        require(liquidityDelta < _state.liquidity); // TODO: min liquidity, min liquidity delta (size)

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96Next(
            _state.liquidity,
            _state.sqrtPriceX96,
            liquidityDelta,
            zeroForOne,
            maintenance
        );
        Position.Info memory position = Position.assemble(
            _state.liquidity,
            _state.sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne,
            fee
        ); // TODO: add funding index

        _state.liquidity -= liquidityDelta;
        _state.sqrtPriceX96 = sqrtPriceX96Next;

        // add to tick cumulatives for funding calc
        int24 tickNext = TickMath.getTickAtSqrtRatio(sqrtPriceX96Next);
        _state.tickCumulative +=
            int56(_state.tick) *
            int56(uint56(_blockTimestamp() - _state.blockTimestamp)); // TODO: think thru overflow
        _state.blockTimestamp = _blockTimestamp();
        _state.tick = tickNext;

        // TODO: calc funding index and set in position

        // callback for margin amount
        uint256 margin;
        if (zeroForOne) {
            // long token0 relative to token1; margin in token0
            uint256 balance0Before = balance0();
            uint256 margin0Minimum = Position.marginMinimumWithFees(
                position.size,
                maintenance,
                fee
            );
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                margin0Minimum,
                0
            ); // TODO: data param

            margin = balance0() - balance0Before;
            require(margin >= margin0Minimum, "margin0 < min"); // TODO: possibly relax so swaps can happen
            position.size += margin.toUint128();
        } else {
            // long token1 relative to token0; margin in token1
            uint256 balance1Before = balance1();
            uint256 margin1Minimum = Position.marginMinimumWithFees(
                position.size,
                maintenance,
                fee
            );
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                0,
                margin1Minimum
            );

            margin = balance1() - balance1Before;
            require(margin >= margin1Minimum, "margin1 < min"); // TODO: possibly relax so swaps can happen
            position.size += margin.toUint128();
        }

        uint112 id = _state.totalPositions;
        positions.set(recipient, _state.totalPositions, position);
        _state.totalPositions++;

        // update to latest state
        state = _state;

        emit Open(
            msg.sender,
            recipient,
            id,
            _state.liquidity,
            _state.sqrtPriceX96,
            liquidityDelta,
            zeroForOne,
            uint128(margin)
        );
    }
}

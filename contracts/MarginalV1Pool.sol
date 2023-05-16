// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity 0.8.17;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {Position} from "./libraries/Position.sol";
import {SqrtPriceMath} from "./libraries/SqrtPriceMath.sol";

import {IMarginalV1Factory} from "./interfaces/IMarginalV1Factory.sol";
import {IMarginalV1OpenCallback} from "./interfaces/callback/IMarginalV1OpenCallback.sol";

contract MarginalV1Pool is ERC20 {
    using Position for mapping(uint256 => Position.Info);

    address public immutable factory;

    address public immutable token0;
    address public immutable token1;
    uint16 public immutable maintenance;

    // TODO: group in pool state struct
    // @dev Pool state represented in (L, sqrtP) space
    uint128 public liquidity;
    uint160 public sqrtPriceX96;
    uint256 public fundingIndex; // TODO: type < uint224 (?) for state in one word

    mapping(uint256 => Position.Info) public positions;
    uint256 private totalPositions;

    uint256 private unlocked = 0;
    modifier lock() {
        require(unlocked == 1, "locked");
        unlocked = 0;
        _;
        unlocked = 1;
    }

    event Open(
        uint256 id,
        uint128 liquidityBefore,
        uint160 sqrtPriceX96Before,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint128 margin
    );

    constructor() ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        (token0, token1, maintenance) = IMarginalV1Factory(msg.sender).params();
        factory = msg.sender;
    }

    function initialize(uint160 _sqrtPriceX96) external {
        require(sqrtPriceX96 == 0, "initialized");
        sqrtPriceX96 = _sqrtPriceX96;
        unlocked = 1;
    }

    function balance0() private view returns (uint256) {
        return IERC20(token0).balanceOf(address(this));
    }

    function balance1() private view returns (uint256) {
        return IERC20(token1).balanceOf(address(this));
    }

    function open(uint128 liquidityDelta, bool zeroForOne) external lock {
        uint160 _sqrtPriceX96 = sqrtPriceX96;
        uint128 _liquidity = liquidity;
        require(liquidityDelta < _liquidity); // TODO: min liquidity, min liquidity delta (size)

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96Next(
            _liquidity,
            _sqrtPriceX96,
            liquidityDelta,
            zeroForOne,
            maintenance
        );
        Position.Info memory position = Position.assemble(
            _liquidity,
            _sqrtPriceX96,
            sqrtPriceX96Next,
            liquidityDelta,
            zeroForOne
        ); // TODO: add funding index

        liquidity -= liquidityDelta;
        sqrtPriceX96 = sqrtPriceX96Next;

        // callback for margin amount
        uint256 margin;
        if (zeroForOne) {
            // long token0 relative to token1; margin in token0
            uint256 balance0Before = balance0();
            uint256 margin0Minimum = Position.marginMinimum(
                position.size0,
                maintenance
            );
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                margin0Minimum,
                0
            ); // TODO: data param

            margin = balance0() - balance0Before;
            require(margin >= margin0Minimum, "margin0 < min"); // TODO: possibly relax so swaps can happen
            position.size0 += uint128(margin); // TODO: univ2 style unsafe cast; worry for large margin?
        } else {
            // long token1 relative to token0; margin in token1
            uint256 balance1Before = balance1();
            uint256 margin1Minimum = Position.marginMinimum(
                position.size1,
                maintenance
            );
            IMarginalV1OpenCallback(msg.sender).marginalV1OpenCallback(
                0,
                margin1Minimum
            );

            margin = balance1() - balance1Before;
            require(margin >= margin1Minimum, "margin1 < min"); // TODO: possibly relax so swaps can happen
            position.size1 += uint128(margin); // TODO: univ2 style unsafe cast; worry for large margin?
        }

        // store position info
        // TODO: figure out what to use for positions key and remove totalPositions given gas expenditure + totalPositions can overflow
        // TODO: key should use msg.sender
        uint256 id = totalPositions;
        positions.set(id, position);
        totalPositions++;

        emit Open(
            id,
            _liquidity,
            _sqrtPriceX96,
            liquidityDelta,
            zeroForOne,
            uint128(margin)
        );
    }
}

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
    uint256 public immutable maintenance;

    // TODO: group in pool state struct
    // @dev Pool state represented in (L, sqrtP) space
    uint256 public liquidity; // TODO: fix type (uint128)
    uint256 public sqrtPrice; // TODO: fix type (uint96)
    uint256 public fundingIndex;

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
        uint256 liquidityBefore,
        uint256 sqrtPriceBefore,
        uint256 liquidityDelta,
        bool zeroForOne,
        uint256 margin
    );

    constructor() ERC20("Marginal V1 LP Token", "MRGLV1-LP") {
        (token0, token1, maintenance) = IMarginalV1Factory(msg.sender).params();
        factory = msg.sender;
    }

    function initialize(uint256 _sqrtPrice) external {
        require(sqrtPrice == 0, "initialized");
        sqrtPrice = _sqrtPrice;
        unlocked = 1;
    }

    function balance0() private view returns (uint256) {
        return IERC20(token0).balanceOf(address(this));
    }

    function balance1() private view returns (uint256) {
        return IERC20(token1).balanceOf(address(this));
    }

    function open(uint256 liquidityDelta, bool zeroForOne) external lock {
        uint256 _sqrtPrice = sqrtPrice;
        uint256 _liquidity = liquidity;
        require(liquidityDelta < _liquidity); // TODO: min liquidity, min liquidity delta (size)

        uint256 sqrtPriceNext = SqrtPriceMath.sqrtPriceNext(
            _liquidity,
            _sqrtPrice,
            liquidityDelta,
            zeroForOne,
            maintenance
        );
        Position.Info memory position = Position.assemble(
            _liquidity,
            _sqrtPrice,
            sqrtPriceNext,
            liquidityDelta,
            zeroForOne
        ); // TODO: add funding index

        liquidity -= liquidityDelta;
        sqrtPrice = sqrtPriceNext;

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
            position.size0 += margin;
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
            position.size1 += margin;
        }

        // store position info
        // TODO: figure out what to use for positions key
        uint256 id = totalPositions;
        positions.set(id, position);
        totalPositions++;

        emit Open(
            id,
            _liquidity,
            _sqrtPrice,
            liquidityDelta,
            zeroForOne,
            margin
        );
    }
}

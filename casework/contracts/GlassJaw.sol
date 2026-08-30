// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A deposit vault with a public `demolish` that ships the whole balance to any address.
///         No owner check. Committed sample (unprotected-selfdestruct).
contract GlassJaw {
    mapping(address => uint256) public deposits;

    function deposit() external payable {
        deposits[msg.sender] += msg.value;
    }

    function demolish(address payable to) external {
        selfdestruct(to); // BUG: anyone can call; the entire balance goes wherever they say
    }
}

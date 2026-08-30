// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A vault with a single-function reentrancy hole (DAO-style). Committed sample case.
///         The external call in `withdraw` happens before the balance is written down.
contract HollowVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 owed = balances[msg.sender];
        require(owed > 0, "nothing to withdraw");

        (bool ok, ) = msg.sender.call{value: owed}(""); // re-entry point
        require(ok, "transfer failed");

        balances[msg.sender] = 0; // written down only after the call returns
    }

    function poolBalance() external view returns (uint256) {
        return address(this).balance;
    }

    receive() external payable {}
}

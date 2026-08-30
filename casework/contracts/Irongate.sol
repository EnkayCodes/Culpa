// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A sound vault, used as a control to measure noise. It writes the balance down
///         before paying out and refuses re-entry. known_truth.is_vulnerable = false.
contract Irongate {
    mapping(address => uint256) public balances;
    uint256 private _open = 1;

    modifier oneAtATime() {
        require(_open == 1, "no re-entry");
        _open = 2;
        _;
        _open = 1;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external oneAtATime {
        require(balances[msg.sender] >= amount, "not enough");
        balances[msg.sender] -= amount; // written down before the call
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}

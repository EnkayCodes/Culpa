// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A sound till: only the operator can sweep, and ownership transfer is two-step.
///         Used as a control to measure noise. known_truth.is_vulnerable = false.
contract LatchGate {
    address public operator;
    address public pendingOperator;
    mapping(address => uint256) public balances;

    constructor() {
        operator = msg.sender;
    }

    modifier onlyOperator() {
        require(msg.sender == operator, "not operator");
        _;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "not enough");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }

    function proposeOperator(address who) external onlyOperator {
        pendingOperator = who;
    }

    function acceptOperator() external {
        require(msg.sender == pendingOperator, "not pending");
        operator = pendingOperator;
        pendingOperator = address(0);
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A sound vault: per-user accounting, checks-effects-interactions, checked return
///         value, owner-only admin with two-step ownership transfer. Noise control.
///         known_truth.is_vulnerable = false.
contract TrueVault {
    address public owner;
    address public pendingOwner;
    mapping(address => uint256) public balanceOf;
    uint256 private _entered;

    constructor() {
        owner = msg.sender;
    }

    modifier noReenter() {
        require(_entered == 0, "reentrant");
        _entered = 1;
        _;
        _entered = 0;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function deposit() external payable {
        balanceOf[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external noReenter {
        require(balanceOf[msg.sender] >= amount, "insufficient");
        balanceOf[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }

    function transferOwnership(address to) external onlyOwner {
        pendingOwner = to;
    }

    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "not pending");
        owner = pendingOwner;
        pendingOwner = address(0);
    }
}

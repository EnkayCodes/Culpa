// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A wallet that authorizes withdrawals with `tx.origin`. If the owner is ever tricked
///         into calling a malicious contract, that contract can drain the wallet because
///         `tx.origin` is still the owner. Committed sample (tx-origin-auth).
contract OriginGate {
    address public owner;

    constructor() payable {
        owner = msg.sender;
    }

    function withdraw(address payable to, uint256 amount) external {
        require(tx.origin == owner, "not owner"); // BUG: tx.origin, not msg.sender
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "send failed");
    }

    receive() external payable {}
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A prepaid credit ledger. `topUp` with ETH to get points 1:1; `spend` burns points
///         and pays ETH back. The burn is inside an `unchecked` block with no balance check, so
///         spending more than you hold underflows to a near-infinite balance and drains the
///         contract. Committed sample (arithmetic).
contract LooseLedger {
    mapping(address => uint256) public points;

    function topUp() external payable {
        points[msg.sender] += msg.value;
    }

    function spend(uint256 amount) external {
        unchecked {
            points[msg.sender] -= amount; // BUG: underflows when amount > points[msg.sender]
        }
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "payout failed");
    }

    receive() external payable {}
}

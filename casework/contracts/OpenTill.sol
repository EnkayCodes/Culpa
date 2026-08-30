// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice A till that lets anyone sweep the whole balance. `drain` never checks that the
///         caller is entitled to anything. Committed sample case (access control).
contract OpenTill {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "not enough");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }

    /// @dev meant for the operator, but nothing enforces that
    function drain(address payable to) external {
        to.transfer(address(this).balance);
    }
}

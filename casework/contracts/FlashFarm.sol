// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @dev Minimal test token — the honest infrastructure around the flaw.
contract Token {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _move(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 room = allowance[from][msg.sender];
        require(room >= amount, "allowance");
        if (room != type(uint256).max) allowance[from][msg.sender] = room - amount;
        _move(from, to, amount);
        return true;
    }

    function _move(address from, address to, uint256 amount) internal {
        require(balanceOf[from] >= amount, "balance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
    }
}

/// @notice A reward farm that pays a share of the reward pool proportional to your CURRENT
///         stake — no time-weighting, no per-deposit accounting. Stake a large amount for one
///         block, claim the bulk of the pool that honest stakers earned, then unstake. Slither
///         is blind to this. Committed sample (logic-error).
contract FlashFarm {
    Token public immutable stakeToken;
    Token public immutable rewardToken;
    mapping(address => uint256) public staked;
    mapping(address => bool) public claimed;
    uint256 public totalStaked;
    uint256 public rewardPool;

    constructor(Token _stake, Token _reward) {
        stakeToken = _stake;
        rewardToken = _reward;
    }

    function fund(uint256 amount) external {
        rewardToken.transferFrom(msg.sender, address(this), amount);
        rewardPool += amount;
    }

    function stake(uint256 amount) external {
        stakeToken.transferFrom(msg.sender, address(this), amount);
        staked[msg.sender] += amount;
        totalStaked += amount;
    }

    function unstake(uint256 amount) external {
        staked[msg.sender] -= amount;
        totalStaked -= amount;
        stakeToken.transfer(msg.sender, amount);
    }

    function claim() external {
        require(!claimed[msg.sender], "claimed");
        require(totalStaked > 0, "no stakers");
        // BUG: reward tracks your instantaneous share of totalStaked, nothing time-weighted.
        uint256 reward = (rewardPool * staked[msg.sender]) / totalStaked;
        claimed[msg.sender] = true;
        rewardPool -= reward;
        rewardToken.transfer(msg.sender, reward);
    }
}

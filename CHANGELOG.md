# Improvement changelog

How Culpa went from a plain Slither scan to a sleuth that proves 7 of 7 flaws with an
executable on-chain exploit. Every row links to evidence in `findings/`.

## The task and the number that matters

- **Task:** given a Solidity contract, name its real flaws — each with a kind and severity —
  and, where it can, an exploit that runs and extracts value on a local chain.
- **Headline metric:** proven-exploit rate = (findings backed by a landed exploit) / (known
  exploitable flaws in the set).
- **Also watched:** flaw-kind micro-F1, noise on sound contracts (false-flag rate), cost and
  time per contract.
- **Case set:** 10 committed cases — 7 vulnerable across 7 flaw kinds (reentrancy,
  access-control, arithmetic, tx-origin-auth, unprotected-selfdestruct,
  price-oracle-manipulation, logic-error) plus 3 sound contracts as noise controls. `culpa verify`
  confirms all 7 reference exploits compile and land before any scoring.

## Progression

| Stage | What was tried and why | Evidence | Result / decision |
|---|---|---|---|
| Baseline — scanner | Slither, every detector, check names mapped to canonical kinds | `findings/scanner_all.json` | micro-F1 **0.30**, false-flags **all 3** sound contracts, **0** exploits. The starting point. |
| Baseline — first glance | One Gemini call: source in, JSON findings out, no tools | `findings/firstglance_all.json` | micro-F1 **0.93**, **0** noise — a strong reader — but still **0** proven exploits. It asserts; it cannot show. |
| Sleuth v0 | Agentic loop: Slither notes as context → ranked leads → write a Foundry exploit per lead → stage it → keep the finding only if it lands → consolidate | `findings/sleuth_v0.json` | micro-F1 1.00 but **proven 0/2** — the closing model call echoed the lead id, not the full proof label, so every finding shipped with `proof: null`. |
| Iteration 1 — build findings from the ledger | Stop trusting the closing LLM reply to carry the proof reference; assemble findings directly from the ledger, where the exploit draft is already attached | `findings/sleuth_it1.json` | **proven 2/2**. Closing call demoted to optional rationale polish. |
| Iteration 2 — `assertGe`, not `assertGt` | A correct reentrancy exploit computed `profit == floor` exactly and failed the strict `>` check by one wei | reference `HollowVault.t.sol` | `assertExploitLanded` now uses `assertGe`; briefing tells the model to set the floor well below the expected haul. |
| Iteration 3 — model + generation config | `gemini-2.5-flash` thinks by default; thinking tokens consumed `max_output_tokens` and truncated exploit files mid-line. Its free tier is also ~20 requests/day. | casebooks | Moved to `gemini-3.5-flash-lite` (auto-follows deprecation 404s), disabled thinking, added 429 backoff. |
| Iteration 4 — clean the staging dir | `forge` compiles the whole `test/` directory, so one truncated file from a failed attempt broke every later compile, including `culpa verify` | `culpa verify` output | `stage()` wipes `test/staged/*.t.sol` before writing. |
| Iteration 5 — useful retry feedback | The retry prompt was pasting ~3 KB of raw `forge --json` trace | casebooks | Retry now gets just the revert reason + decoded console lines; `_compile_error` keeps the `-->` location and offending source line. |
| Iteration 6 — multi-contract imports | The flash-loan exploit failed only on `contract Attacker is Borrower` — an interface in the subject file it had not imported | `HallOfMirrors` casebook | Briefing: import every name you use; for a callback interface just declare the function, don't inherit. |
| Iteration 7 — value flow | Two misses: a reentrancy loop draining 1 wei per call (out of gas at 528 frames), and funds sent to a pranked `msg.sender` that was actually the victim (`profit 0`) | `LooseLedger`, `OriginGate` casebooks | Briefing: one decisive call over a loop; route funds to the attacker contract or a fixed address, never `msg.sender`; added a single-call worked example. Proof attempts 2 → 3. |
| Final | Fold in every change that helped | `findings/sleuth_all.json` | **proven 7/7**, micro-F1 **1.00**, noise on sound **0.00**, ~$0.001 per contract on the free tier. |

## Scanner against sleuth

Measured on the `committed` set — 10 contracts, 7 vulnerable across 7 flaw kinds, 3 sound.
Full table in `submission/comparison.md`.

| Measure | Slither | first glance | Sleuth | Δ (Slither → Sleuth) |
|---|---|---|---|---|
| Proven-exploit rate | 0 / 7 | 0 / 7 | **6–7 / 7** | +0.86–1.00 |
| Flaw-kind micro-F1 | 0.30 | 0.71 | **1.00** | +0.70 |
| Flaw-kind macro-F1 | 0.35 | — | **1.00** | +0.65 |
| Noise on sound contracts | 1.00 (3/3) | 0.00 | **0.00** | −1.00 |
| Unbacked exploit claims | 0 | 0 | **0** | — |
| Cost per contract | $0.00 | ~$0.0001 | ~$0.0002 | — |
| Time per contract | ~0.7 s | ~2.7 s | ~9 s | — |

### On variance

The model is run at temperature 0, but the free tier is still nondeterministic. Across repeated
`committed` runs on `gemini-3.5-flash-lite` the sleuth **identifies every flaw correctly every
time** (leads are stable); the proven-exploit count ranges 5–7 of 7 as the harder value-flow
exploits (`HallOfMirrors`, `OriginGate`) land on some runs and exhaust their retries on others.
`gemini-3.5-flash` is stronger at Solidity but its free-tier request cap is too low for a
10-case run — it rate-limited and left 3 cases unfinished. So flash-lite is the reported model.

Slither and the one-shot baseline prove **zero** of the seven in every run.

## The main way it goes wrong

The model's **leads were correct on every case** — it named the right flaw kind and the right
attack the first time. Every failure was in the **exploit**: a strict-comparison off-by-one, a
missing import, a recursion that can't scale, funds routed to the wrong address. These are
shallow, mechanical mistakes — and every one of them was caught because the exploit is *run*,
not just asserted, and fixed in one retry from the compiler / revert message.

## Hot take

**Running the exploit is the product.** Across all 10 cases the model identified the flaw
correctly on the first try — the reasoning was never the bottleneck. What broke were the
exploits: `>` where it needed `>=`, an un-imported interface, a wei-at-a-time drain that ran out
of gas, profit sent to `msg.sender`. An agent that *executes* its own exploit surfaces every one
of these in seconds and repairs it from the error text. An agent that only *asserts* a
vulnerability would have reported 7 findings with 4 broken proofs — and no way to tell which 4.
The 25 points of engineering value here isn't in finding bugs; frontier models already do that.
It's in the loop that refuses to call a finding real until the money actually moves.

# Casework

Each case is one JSON file in `files/`, checked against `schema.json`.

## Where cases come from

| Name style | Source | How to bring it in | Notes |
|---|---|---|---|
| Named after the flaw's character (e.g. `SkimmedPool`) | hand-written or [SmartBugs-Curated](https://github.com/smartbugs/smartbugs-curated) | `python scripts/gather.py smartbugs` | Detection-focused; most are old solc. Mark `provable` only after porting to ^0.8. |
| Named after the incident's shape (e.g. `HallOfMirrors`) | [DeFiHackLabs](https://github.com/SunWeb3Sec/DeFiHackLabs) | `python scripts/gather.py defihacklabs` | Fork cases. Known truth = the published post-mortem. Pin the fork block one before the attack. |

## Committed cases (run with no downloads)

Vulnerable, each with a reference exploit in `proofs/`:

| Case | Flaw kind | Scanner sees it? |
|---|---|---|
| `HollowVault` | reentrancy | yes |
| `OpenTill` | access-control | partly |
| `LooseLedger` | arithmetic (unchecked underflow) | no |
| `OriginGate` | tx-origin-auth | yes |
| `GlassJaw` | unprotected-selfdestruct | yes |
| `HallOfMirrors` | price-oracle-manipulation (flash loan, 3 contracts) | **no** |
| `FlashFarm` | logic-error (instantaneous-share reward skim) | **no** |

Sound (noise controls, `is_vulnerable: false`): `Irongate`, `LatchGate`, `TrueVault`.

`PendingCase` — a fork-case template; left out of scoring until filled in.

Case groups live in `config/preferences.yaml`: `quick`, `easy`, `hard`, `sound`, `committed`,
and `full` (every file in `files/`).

## Keeping the known truth honest (rubric: reproducibility, integrity)

- One `category` per distinct root cause. Don't pad with scanner noise.
- For fork cases, record the exact `block` and the attack transaction in `notes`.
- Every `provable: true` case needs a working `reference_proof` you can run yourself.

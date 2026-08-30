# Casework

Each case is one JSON file in `files/`, checked against `schema.json`.

## Where cases come from

| Name style | Source | How to bring it in | Notes |
|---|---|---|---|
| Named after the flaw's character (e.g. `SkimmedPool`) | hand-written or [SmartBugs-Curated](https://github.com/smartbugs/smartbugs-curated) | `python scripts/gather.py smartbugs` | Detection-focused; most are old solc. Mark `provable` only after porting to ^0.8. |
| Named after the incident's shape (e.g. `HallOfMirrors`) | [DeFiHackLabs](https://github.com/SunWeb3Sec/DeFiHackLabs) | `python scripts/gather.py defihacklabs` | Fork cases. Known truth = the published post-mortem. Pin the fork block one before the attack. |

## Committed cases (run with no downloads)

- `HollowVault` — reentrancy; vulnerable, local exploit, reference in `proofs/`.
- `OpenTill` — access control; `drain()` is open to anyone. Vulnerable, local exploit.
- `Irongate` — a sound vault (checks-effects-interactions + re-entry latch). Noise control.
- `LatchGate` — a sound till (operator-only admin, two-step ownership). Noise control.
- `HallOfMirrors` — **the hard one**: three contracts, a lending shop that values collateral at
  a pool's spot price, taken with a flash loan. Self-contained, local exploit. The scanner
  cannot see it — this is the case that separates the sleuth from the baseline.
- `PendingCase` — a fork-case template; leave it out of scoring until it's filled in.

Case groups live in `config/preferences.yaml`: `quick`, `easy`, `sound`, `hard`, `committed`,
and `full` (every file in `files/`).

## Keeping the known truth honest (rubric: reproducibility, integrity)

- One `category` per distinct root cause. Don't pad with scanner noise.
- For fork cases, record the exact `block` and the attack transaction in `notes`.
- Every `provable: true` case needs a working `reference_proof` you can run yourself.

# Culpa

A smart-contract investigator that doesn't just accuse code of a flaw — it **proves each one
with a working exploit** — and a repeatable way to score how well it does against a plain
Slither scan.

Built for the **micro1 Frontier / Agentic Workflows Hackathon** (Aug 28–31, 2026).

## Results

On 10 contracts (7 vulnerable across 7 flaw kinds, 3 sound), free-tier `gemini-3.5-flash-lite`,
~$0.002 for the whole run:

| | Slither | one-shot LLM | **Culpa's sleuth** |
|---|---|---|---|
| Exploits proven with a runnable PoC | **0 / 7** | 0 / 7 | **6 / 7** |
| Flaw-kind F1 | 0.30 | 0.71 | **1.00** |
| False-flags on sound contracts | **3 / 3** | 0 / 3 | **0 / 3** |

Every flaw is identified correctly; 6 of 7 come with an exploit that runs and moves the money on
a local chain (the 7th, a 3-contract flash-loan attack, lands on some runs — see `CHANGELOG.md`).
Frozen run + full agent trajectories: [`submission/`](submission/).

---

## The idea in one paragraph

A Slither scan and a one-shot model prompt both hand you a pile of *claims* with a high false
alarm rate and no evidence. Culpa's sleuth chases a lead, **writes a Foundry exploit for it,
runs it on a throwaway chain, and keeps the finding only if the exploit lands** (drains the
funds / breaks the invariant). The proceedings score detection quality (precision, recall, F1),
noise on sound contracts, and — the headline number — the **proven-exploit rate**: what share
of the "high severity" findings come with an exploit a judge can re-run.

## Who it's for

A protocol team doing a last look before deployment, or an auditor triaging a scanner's forty
warnings. Their bottleneck: they can't tell which warnings are real without hand-writing the
attack, and that's most of the work.

## Layout

```
casework/               The cases and what we already know about them
  schema.json           Shape of a case file
  files/*.json           One file per case
  contracts/*.sol        Contract sources (three committed; the rest gathered)
  proofs/*.t.sol         Reference exploits (the ground-truth attacks)
src/culpa/
  casefile.py           Types every part shares
  lexicon.py            Canonical flaw kinds + Slither / SWC translations
  caseload.py           Load and check cases
  investigator.py       What an investigator is; the first-glance / scanner / sleuth hand-off
  verdict.py            Pure scoring (weigh_case, tally) — unit tested
  writeup.py            The side-by-side comparison
  proceedings.py        Work a whole set of cases
  counsel.py            The model Culpa consults (Google Gemini, free tier)
  commands.py           `culpa check | investigate | compare | read`
  baseline/             scanner.py (Slither), firstglance.py (one model look)
  sleuth/               investigation.py (SKELETON), briefings.py, instruments.py, casebook.py
  proof/                staging.py (runs an exploit and judges it), foundation/ExploitProof.sol
proofground/            The Foundry project where written exploits are staged and run
findings/               Scored runs and the comparison
casebooks/              One casebook per case (the agent trajectory — a required deliverable)
CHANGELOG.md            The story of each improvement (rubric: measured improvement)
REPRODUCTION.md         Clean-machine setup and exact commands (rubric: reproducibility)
```

## Quick start

```bash
bash scripts/prepare.sh      # python packages, foundry, forge-std, solc versions
cp .env.example .env         # add GEMINI_API_KEY (free: https://aistudio.google.com/apikey)
culpa check                # schema-check the cases, report tools on hand
culpa consult              # one tiny call — confirm the Gemini key works
culpa verify               # every committed reference exploit compiles and lands
culpa investigate --who scanner --cases quick --into findings/scanner.json
culpa investigate --who sleuth  --cases quick --into findings/sleuth.json
culpa compare findings/scanner.json findings/sleuth.json --into findings/comparison.md
```

## How this lines up with the rubric

| What's scored | Where it lives |
|---|---|
| Agent solution & engineering (30) | `src/culpa/sleuth/` — chase a lead, write the exploit, run it, keep what lands |
| End-to-end quality (20) | `culpa read` renders a plain audit note per contract |
| Problem & user value (15) | this README + `casework/README.md` |
| Measured improvement (15) | `CHANGELOG.md` + `findings/comparison.md` |
| Reproducibility (15) | `REPRODUCTION.md` + a pinned `proofground` + fixed fork blocks |
| Hot take / insight (5) | the closing section of `CHANGELOG.md` |

See `NOTICE.md` for the submission-ownership terms.

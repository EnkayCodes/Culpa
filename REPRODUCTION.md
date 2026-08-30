# Reproduction guide

## Fastest path: GitHub Codespaces

The repo ships a `.devcontainer/` that installs Foundry, solc, and Culpa automatically on a
fast cloud connection. Push this repo to GitHub, click **Code → Codespaces → Create**, wait for
setup, then:

```bash
echo 'GEMINI_API_KEY=your-key' >> .env
culpa consult && culpa verify
```

The rest of this guide is the manual route for a local machine.

---

Written for someone on a **clean machine**. Rough runtime for the quick set: ~3 min for the
scanner, ~15–40 min for the sleuth (depends on exploit retries). No bill — Culpa consults
**Google Gemini** on its free tier.

## 1. What you need

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Foundry | >= 0.2.0 (pin a nightly in CI) | `forge`, `anvil`, `cast` |
| solc-select | latest | the scanner and sleuth pick a solc per contract |
| A Gemini API key | free | https://aistudio.google.com/apikey — no card needed |

### Linux / macOS / WSL (recommended)

```bash
curl -L https://foundry.paradigm.xyz | bash && foundryup
pipx install solc-select || pip install solc-select
```

### Windows

Foundry on native Windows is unreliable. Use **WSL2 (Ubuntu)** and run everything from there.
`scripts/prepare.sh` assumes a POSIX shell. A bare Ubuntu also needs `sudo apt install -y
python3-pip python3-venv build-essential`.

## 2. Install

```bash
git clone <this repo> && cd culpa
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bash scripts/prepare.sh
```

## 3. Configure

```bash
cp .env.example .env
```

- `GEMINI_API_KEY` — from https://aistudio.google.com/apikey. Required for `consult`,
  `first-glance`, and `sleuth`.
- `CULPA_MODEL` — `gemini-2.5-flash` (default), `gemini-2.0-flash`, or `gemini-2.5-pro`
  (stronger, small free-tier quota).
- `MAINNET_RPC_URL` — an archive node, only for fork cases.

## 4. Bring in cases (optional)

```bash
python scripts/gather.py smartbugs
python scripts/gather.py defihacklabs
```

Five cases ship in the repo (`HollowVault`, `OpenTill`, `Irongate`, `LatchGate`,
`HallOfMirrors`) so everything runs with no downloads.

## 5. Run it

```bash
culpa check                            # cases hold up; forge / slither / key on hand?
culpa consult                          # one tiny call — does the Gemini key work?
culpa verify                           # every committed reference exploit compiles and lands
culpa investigate --who scanner       --cases quick --into findings/scanner.json
culpa investigate --who first-glance  --cases quick --into findings/firstglance.json
culpa investigate --who sleuth        --cases easy  --into findings/sleuth_easy.json
culpa compare findings/scanner.json findings/sleuth_easy.json --into findings/comparison.md
culpa read findings/sleuth_easy.json --case OpenTill
```

Free-tier Gemini is rate-limited (a handful of requests per minute). A full sleuth run over
~12 cases is a few hundred calls — run it in stages (`easy`, then `hard`, then the gathered
set) and let it pace itself if you hit a 429.

## 6. What you should see

`findings/comparison.md` — the scanner-against-sleuth table. `casebooks/<case>.jsonl` — every
move the sleuth made. `proofground/test/staged/` — the exploits it wrote; re-run any:

```bash
forge test --root proofground --match-contract ProveOpenTill -vvv --allow-paths "$(pwd)/casework"
```

## 7. On determinism

- Fork cases pin `--fork-block-number`; never "latest".
- Model calls are not deterministic. Each run records the model, token counts, and the raw
  replies in the casebook so a reviewer can audit the run.
- `forge` fuzz seeds are pinned in `proofground/foundry.toml`.

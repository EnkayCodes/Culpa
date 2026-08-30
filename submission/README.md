# Submission run

The frozen evidence for the micro1 Frontier / Agentic Workflows Hackathon. Everything here is
reproducible from a clean checkout with `culpa verify` + the commands in `/REPRODUCTION.md`.

| File | What it is |
|---|---|
| `scanner.json` | Baseline 1 — Slither, all detectors, over the 10-case `committed` set |
| `firstglance.json` | Baseline 2 — one Gemini call per contract, no tools |
| `sleuth.json` | Culpa's agent — leads → write exploit → run → keep what lands |
| `comparison.md` | Scanner vs sleuth, the headline table |
| `audit.md` | The signed audit note Culpa produced from `sleuth.json` |
| `casebooks/*.jsonl` | Agent trajectory for every case — every model call, tool call, retry |

## Reproduce

```bash
culpa verify                                                    # 7/7 reference exploits land
culpa investigate --who scanner      --cases committed --into submission/scanner.json
culpa investigate --who first-glance --cases committed --into submission/firstglance.json
culpa investigate --who sleuth       --cases committed --into submission/sleuth.json
culpa compare submission/scanner.json submission/sleuth.json --into submission/comparison.md
culpa report  submission/sleuth.json --into submission/audit.md
cp casebooks/*.jsonl submission/casebooks/
```

Model, token counts, and per-call cost are recorded inside `sleuth.json` and each casebook, so a
reviewer can audit the run without re-paying for it.

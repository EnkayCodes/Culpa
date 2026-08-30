# Improvement changelog

The story of how Marlowe went from a plain scan to a sleuth that proves its findings. Every row
should point at evidence in `findings/`. Replace the placeholder numbers as you run.

## The task and the number that matters

- **Task:** given a Solidity contract (source, or an address plus a fork), name its real flaws,
  each with a kind and severity, and — where it can — an exploit that runs.
- **Headline number:** proven-exploit rate = (findings with a landed exploit) / (known
  exploitable flaws).
- **Also watched:** kind micro-F1, noise on sound contracts, cost and time per contract.
- **Case set:** `--cases quick` (committed) for a smoke run; `--cases full` plus gathered
  smartbugs / defihacklabs cases for the write-up. Aim for at least 12 scored cases including
  at least one hard one.
- **The hard case (committed):** `HallOfMirrors` — a flash loan bends a lending shop's own
  price feed, across three contracts. The scanner scores zero here; a landed sleuth exploit on
  this case is the headline result and the single biggest lever on the score. Check the
  reference exploit first: `make prove-hallofmirrors`.

## Progression

| Stage | What was tried and why | Evidence | What was decided |
|---|---|---|---|
| Scan | Slither with every detector; translate check names into canonical kinds | `findings/scanner.json` | The starting point. Expect decent recall on reentrancy / tx-origin, ~0 on economic and logic flaws, plenty of noise. No exploits. |
| First glance | One model look at the source, no tools | `findings/firstglance.json` | Expect wider kind coverage than the scanner, worse precision, still 0 proven exploits. A fair "reasonable first pass". |
| Try one | Sleuth: hand it the scan as background, ask for ranked leads | `findings/sleuth_try_one.json` | TODO |
| Try two | Sleuth writes a Foundry exploit per lead; keep the finding only if it lands | `findings/sleuth_try_two.json` | TODO — expected to be the main contribution |
| Try three | Retry loop: feed the `forge` error back, up to three attempts | `findings/sleuth_try_three.json` | TODO |
| Try four (dropped) | A second "second opinion" pass over the findings | `findings/sleuth_try_four.json` | TODO — likely dropped if it doesn't move the number; say what it taught you |
| Settled | Fold in the tries that helped | `findings/sleuth.json` | TODO |

## Scanner against sleuth (fill from findings/comparison.md)

| Measure | Scanner | First glance | Sleuth | Change (scanner → sleuth) |
|---|---|---|---|---|
| Proven-exploit rate | 0 / N | 0 / N | _ / N | |
| Kind micro-F1 | | | | |
| Noise on sound contracts | | | | |
| Cost per contract | $0.00 | | | |
| Time per contract (s) | | | | |

## The main way it goes wrong

TODO — e.g. "the sleuth writes exploits that pass by leaning on the test setup rather than the
contract (the fund-the-attacker shortcut); headed off with the opening-balance note in
ExploitProof and a setup check."

## Hot take

TODO — one lesson about building agents you can trust, from something you watched go wrong.
Draft: "Being able to run its own claim changes what the tool is. The retry loop on `forge`
errors moved the proven-exploit rate more than swapping to a bigger model did."

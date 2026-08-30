# scanner against sleuth

- Cases: 10  ·  vulnerable: 7  ·  sound: 3
- Proofs expected: 7

| Measure | scanner | sleuth | change |
|---|---|---|---|
| Proven-exploit rate | 0.00 | 0.71 | +0.71 (better) |
| Exploits proven | 0 of 7 | 5 of 7 | |
| Kind precision (micro) | 0.20 | 1.00 | +0.80 (better) |
| Kind recall (micro) | 0.57 | 1.00 | +0.43 (better) |
| Kind F1 (micro) | 0.30 | 1.00 | +0.70 (better) |
| Kind F1 (macro) | 0.35 | 1.00 | +0.65 (better) |
| Noise on sound contracts | 1.00 | 0.00 | -1.00 (better) |
| Unbacked exploit claims | 0 | 0 | |
| Cost per contract | $0.000 | $0.000 | +0.00 (worse) |
| Time per contract (s) | 0.7 | 10.0 | +9.34 (worse) |
| Cases that errored | 0 | 0 | |

## F1 by flaw kind

| Kind | scanner | sleuth | cases |
|---|---|---|---|
| access-control | 0.67 | 1.00 | 1 |
| arithmetic | 0.00 | 1.00 | 1 |
| logic-error | 0.00 | 1.00 | 1 |
| other | 0.00 | 0.00 | 0 |
| price-oracle-manipulation | 0.00 | 1.00 | 1 |
| reentrancy | 0.50 | 1.00 | 1 |
| tx-origin-auth | 1.00 | 1.00 | 1 |
| unchecked-low-level-call | 0.00 | 0.00 | 0 |
| unprotected-selfdestruct | 1.00 | 1.00 | 1 |

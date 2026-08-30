# Submission notice

Marlowe is a hackathon submission for the **micro1 Frontier / Agentic Workflows Hackathon**.

Under the Hackathon Participation Agreement accepted at registration, **micro1 owns submissions
and may use them for AI model training and evaluation**. Do not add any code, data, or
credentials to this repository that you are not able and willing to license under those terms.

## Outside material

| Piece | Source | License | Use |
|---|---|---|---|
| SmartBugs-Curated contracts | github.com/smartbugs/smartbugs-curated | see upstream | case set (gathered, not redistributed here) |
| DeFiHackLabs exploits | github.com/SunWeb3Sec/DeFiHackLabs | MIT | reference exploits / fork parameters |
| forge-std | github.com/foundry-rs/forge-std | MIT / Apache-2.0 | the exploit test harness |
| Slither | github.com/crytic/slither | AGPL-3.0 | the scanner baseline and a sleuth instrument (run as a subprocess) |
| Google Gemini API (`google-genai`) | Google | see Google AI terms | how Marlowe consults the model; run on the free tier |

Slither is AGPL. It is used here only as an external tool invoked over a subprocess; Marlowe's
own code does not link it. Confirm this is fine for your submission, or run the scanner behind a
flag and use `first-glance` as the baseline instead.

Every address and fork block used is from public mainnet history. No private data.

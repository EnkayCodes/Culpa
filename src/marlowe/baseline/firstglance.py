"""The second baseline: one look at the code by the model, no tools, no proof. The honest
'reasonable first pass' a person might do."""
from __future__ import annotations

import time

from ..counsel import ask
from ..casefile import Case, Dossier, Finding
from ..investigator import read_subject_source
from ..lexicon import FLAW_KINDS, to_canonical

_INSTRUCTIONS = (
    "You are a smart-contract security reviewer. Name only real, exploitable flaws. "
    "Do not report style issues or gas notes."
)

_QUESTION = """Read this Solidity and name its flaws.

Answer ONLY with a JSON array. Each item:
{{"category": <one of {kinds}>, "severity": "high|medium|low", "lines": [int, ...],
  "title": short string, "rationale": one or two sentences}}

If there is nothing real, answer [].

```solidity
{source}
```"""


class FirstGlance:
    name = "first-glance"

    def look(self, case: Case) -> Dossier:
        dossier = Dossier(case_name=case.name)
        start = time.time()
        source = read_subject_source(case)
        if not source:
            dossier.error = "first glance needs the contract source"
            dossier.duration_s = time.time() - start
            return dossier

        try:
            reply = ask(_INSTRUCTIONS, _QUESTION.format(kinds=sorted(FLAW_KINDS), source=source[:60000]))
        except Exception as e:  # noqa: BLE001 - an investigator must not raise
            dossier.error = f"the model call failed: {e}"
            dossier.duration_s = time.time() - start
            return dossier

        dossier.model = reply.model
        dossier.cost_usd = reply.cost_usd
        try:
            items = reply.as_json()
        except ValueError as e:
            dossier.error = str(e)
            dossier.duration_s = time.time() - start
            return dossier

        for it in items if isinstance(items, list) else []:
            sev = it.get("severity")
            dossier.findings.append(
                Finding(
                    category=to_canonical(str(it.get("category", "other"))),
                    severity=str(sev).lower() if sev in ("high", "medium", "low") else "medium",
                    confidence=0.5,
                    title=str(it.get("title", ""))[:120],
                    lines=[int(x) for x in it.get("lines", []) if isinstance(x, (int, float))][:20],
                    rationale=str(it.get("rationale", ""))[:800],
                    source="counsel",
                    proof=None,
                )
            )
        dossier.duration_s = time.time() - start
        return dossier

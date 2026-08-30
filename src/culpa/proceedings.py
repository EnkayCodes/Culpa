"""Work a whole set of cases: for each one — investigate, stage its exploits, weigh the result."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from .caseload import load_cases
from .casefile import Dossier, ProofOutcome
from .investigator import assign_investigator
from .preferences import preferences
from .proof.staging import stage
from .verdict import Tally, tally, weigh_case


def try_cases(investigator_kind: str, selection: str, limit: int | None = None,
              step=lambda *_: None) -> dict:
    investigator = assign_investigator(investigator_kind)
    cases = load_cases(selection)
    if limit:
        cases = cases[:limit]

    records: list[dict] = []
    cards = []
    opened = time.time()

    for i, case in enumerate(cases, 1):
        step(i, len(cases), case.name)
        dossier: Dossier = investigator.look(case)

        # Culpa re-stages every exploit itself, so both baselines and the sleuth are judged
        # by the exact same standard.
        outcomes: dict[str, ProofOutcome] = {}
        for f in dossier.findings:
            if f.proof and f.proof.label not in outcomes:
                outcomes[f.proof.label] = stage(f.proof)

        card = weigh_case(case, dossier, outcomes)
        cards.append(card)
        records.append({
            "case": case.name,
            "dossier": dossier.model_dump(),
            "proofs": {k: v.model_dump() for k, v in outcomes.items()},
            "scorecard": asdict(card),
        })

    counted: Tally = tally(cards)
    return {
        "investigator": investigator_kind,
        "who": investigator.name,
        "selection": selection,
        "model": preferences()["model"],
        "cases": len(cases),
        "wall_seconds": round(time.time() - opened, 1),
        "tally": asdict(counted),
        "records": records,
    }


def save_proceedings(proceedings: dict, where: str | Path) -> Path:
    where = Path(where)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(json.dumps(proceedings, indent=2, default=str))
    return where


def load_proceedings(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def tally_from_proceedings(proceedings: dict) -> Tally:
    return Tally(**proceedings["tally"])

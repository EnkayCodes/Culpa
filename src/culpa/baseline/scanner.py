"""The first baseline: run Slither, translate its hits into canonical flaw kinds.
No exploits, no model cost."""
from __future__ import annotations

import json
import subprocess
import time

from ..caseload import resolve_in_casework
from ..casefile import Case, Dossier, Finding
from ..lexicon import SCANNER_MAP, to_canonical

_IMPACT_TO_SEV = {
    "High": "high", "Medium": "medium", "Low": "low",
    "Informational": "info", "Optimization": "info",
}


class ScannerPass:
    name = "slither-scanner"

    def look(self, case: Case) -> Dossier:
        dossier = Dossier(case_name=case.name, model=None)
        start = time.time()

        target = case.primary_subject_path
        if target is None:
            dossier.error = "the scanner only handles cases with source (no on-chain address)"
            dossier.duration_s = time.time() - start
            return dossier

        path = resolve_in_casework(target)
        cmd = ["slither", str(path), "--json", "-"]
        if case.compiler_version:
            cmd += ["--solc-solcs-select", case.compiler_version]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            dossier.error = f"slither did not run: {e}"
            dossier.duration_s = time.time() - start
            return dossier

        report = _extract_json(proc.stdout)
        if report is None:
            dossier.error = "could not read slither json"
            dossier.duration_s = time.time() - start
            return dossier

        for det in report.get("results", {}).get("detectors", []):
            check = det.get("check", "")
            kind = SCANNER_MAP.get(check) or to_canonical(check) or to_canonical(det.get("description", ""))
            lines: list[int] = []
            for el in det.get("elements", []):
                lines += el.get("source_mapping", {}).get("lines", []) or []
            dossier.findings.append(
                Finding(
                    category=kind,
                    severity=_IMPACT_TO_SEV.get(det.get("impact", "Medium"), "medium"),
                    confidence=0.4 if det.get("confidence") == "Low" else 0.7,
                    title=check,
                    lines=sorted(set(lines))[:20],
                    rationale=(det.get("description", "") or "").strip()[:800],
                    source="scanner",
                    proof=None,
                )
            )
        dossier.duration_s = time.time() - start
        return dossier


def _extract_json(stdout: str) -> dict | None:
    stdout = (stdout or "").strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        i, j = stdout.find("{"), stdout.rfind("}")
        if i != -1 and j != -1:
            try:
                return json.loads(stdout[i:j + 1])
            except json.JSONDecodeError:
                return None
    return None

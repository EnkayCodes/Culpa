"""What it means to be an investigator. The first-glance pass, the scanner, and the sleuth
all satisfy this."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from .caseload import resolve_in_casework
from .casefile import Case, Dossier


@runtime_checkable
class Investigator(Protocol):
    name: str

    def look(self, case: Case) -> Dossier:
        """Work one case. Must not raise: put failures in dossier.error."""
        ...


def read_subject_source(case: Case) -> str:
    """Gather the source for a case whose subjects we have on disk."""
    parts: list[str] = []
    seen: set[Path] = set()
    candidates: list[str] = []
    if case.primary_subject_path:
        candidates.append(case.primary_subject_path)
    candidates += [s.path for s in case.subjects if s.path]
    for rel in candidates:
        p = resolve_in_casework(rel)
        if p in seen or not p.exists():
            continue
        seen.add(p)
        parts.append(f"// ===== {p.name} =====\n{p.read_text()}")
    return "\n\n".join(parts)


def assign_investigator(kind: str) -> Investigator:
    if kind == "scanner":
        from .baseline.scanner import ScannerPass
        return ScannerPass()
    if kind == "first-glance":
        from .baseline.firstglance import FirstGlance
        return FirstGlance()
    if kind == "sleuth":
        from .sleuth.investigation import Sleuth
        return Sleuth()
    raise ValueError(f"unknown investigator {kind!r} (scanner | first-glance | sleuth)")

"""Load and check the cases Marlowe works through."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .casefile import Case
from .preferences import preferences


def _paths() -> tuple[Path, Path]:
    root = Path(preferences()["casework"])
    return root, root / "schema.json"


def load_schema() -> dict:
    _, schema_path = _paths()
    return json.loads(schema_path.read_text())


def _case_files(selection: str) -> list[Path]:
    root, _ = _paths()
    files_dir = root / "files"
    everything = sorted(files_dir.glob("*.json"))
    if selection == "full":
        return everything

    groups = preferences().get("groups", {})
    if selection in groups and isinstance(groups[selection], list):
        wanted = set(groups[selection])
        return [p for p in everything if p.stem in wanted]

    # otherwise treat `selection` as a case-name prefix
    lo = selection.lower()
    return [p for p in everything if p.stem.lower().startswith(lo)]


def load_cases(selection: str = "quick", check: bool = True) -> list[Case]:
    schema = load_schema() if check else None
    cases: list[Case] = []
    for path in _case_files(selection):
        raw = json.loads(path.read_text())
        if schema is not None:
            jsonschema.validate(raw, schema)
        cases.append(Case.model_validate(raw))
    if not cases:
        raise FileNotFoundError(f"no cases matched selection {selection!r}")
    return cases


def resolve_in_casework(rel: str) -> Path:
    """Resolve a casework-relative path (as stored in a case file) to an absolute path."""
    root, _ = _paths()
    p = Path(rel)
    return p if p.is_absolute() else (root / p)

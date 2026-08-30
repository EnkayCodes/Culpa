#!/usr/bin/env python3
"""Pull outside case material into casework/. Small, no dependencies.

Usage:
  python scripts/gather.py smartbugs      # clone smartbugs-curated, list what is there
  python scripts/gather.py defihacklabs   # clone DeFiHackLabs, list recent exploits to port

Deliberately a starting point you finish during the sprint: choose WHICH contracts and
incidents to bring in, and write their known truth by hand.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]

REPOS = {
    "smartbugs": "https://github.com/smartbugs/smartbugs-curated",
    "defihacklabs": "https://github.com/SunWeb3Sec/DeFiHackLabs",
}


def _clone(url: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="culpa-"))
    subprocess.run(["git", "clone", "--depth", "1", url, str(tmp)], check=True)
    return tmp


def smartbugs() -> None:
    repo = _clone(REPOS["smartbugs"])
    here = repo / "dataset"
    print(f"cloned to {repo}\nvulnerability folders:")
    for d in sorted(p.name for p in here.iterdir() if p.is_dir()):
        print(f"  - {d}")
    print(
        "\nNext: copy each contract you want into casework/contracts/ with a natural name\n"
        "(e.g. SkimmedPool.sol), then write casework/files/SkimmedPool.json with the known\n"
        "truth from smartbugs' vulnerabilities.json. Record the solc version in the case file."
    )


def defihacklabs() -> None:
    repo = _clone(REPOS["defihacklabs"])
    recent = sorted((repo / "src" / "test").rglob("*.sol"))[-40:]
    print(f"cloned to {repo}. {len(recent)} recent exploit files (tail):")
    for p in recent:
        print(f"  - {p.relative_to(repo)}")
    print(
        "\nNext: pick single- or two-contract incidents. Port each exploit to\n"
        "casework/proofs/<Name>.t.sol (import @proof/ExploitProof, set profit, assertExploitLanded)\n"
        "and write casework/files/<Name>.json with the fork block = attack block minus one."
    )


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("smartbugs", "defihacklabs"):
        sys.exit(__doc__)
    {"smartbugs": smartbugs, "defihacklabs": defihacklabs}[sys.argv[1]]()

"""How Marlowe is configured: config/preferences.yaml overlaid with MARLOWE_* env vars / .env."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

HOME = Path(__file__).resolve().parents[2]


@lru_cache
def preferences() -> dict[str, Any]:
    load_dotenv(HOME / ".env")
    path = HOME / "config" / "preferences.yaml"
    prefs: dict[str, Any] = yaml.safe_load(path.read_text()) if path.exists() else {}

    prefs["model"] = os.getenv("MARLOWE_MODEL", prefs.get("model", "gemini-2.5-flash"))
    prefs["max_tokens"] = int(os.getenv("MARLOWE_MAX_TOKENS", prefs.get("max_tokens", 8000)))

    sleuth = prefs.setdefault("sleuth", {})
    sleuth["max_leads"] = int(os.getenv("MARLOWE_MAX_LEADS", sleuth.get("max_leads", 6)))
    sleuth["max_proof_attempts"] = int(
        os.getenv("MARLOWE_MAX_PROOF_ATTEMPTS", sleuth.get("max_proof_attempts", 3))
    )

    proof = prefs.setdefault("proof", {})
    proof["timeout_s"] = int(os.getenv("MARLOWE_PROOF_TIMEOUT", proof.get("timeout_s", 180)))
    proof["proofground"] = str(HOME / proof.get("proofground", "proofground"))

    prefs["home"] = str(HOME)
    prefs["casework"] = str(HOME / prefs.get("casework", {}).get("root", "casework"))
    return prefs

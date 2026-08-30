"""The vocabulary Culpa uses for kinds of flaws, and how to translate other tools' terms.

The verdict matches a finding to known truth by exact canonical kind, so all the aliasing of
Slither check names, SWC codes, and loose model phrasing lives here.
"""
from __future__ import annotations

FLAW_KINDS: set[str] = {
    "reentrancy",
    "access-control",
    "arithmetic",                 # over/underflow, precision
    "unchecked-low-level-call",
    "denial-of-service",
    "bad-randomness",
    "front-running",
    "time-manipulation",
    "tx-origin-auth",
    "price-oracle-manipulation",
    "flash-loan-attack",
    "logic-error",
    "bad-accounting",
    "uninitialized-storage",
    "delegatecall-injection",
    "signature-replay",
    "unprotected-selfdestruct",
    "other",
}

# Loose / free-text phrasing -> canonical
ALIASES: dict[str, str] = {
    "reentrancy-eth": "reentrancy",
    "reentrancy-no-eth": "reentrancy",
    "reentrancy-benign": "reentrancy",
    "reentrant call": "reentrancy",
    "integer overflow": "arithmetic",
    "integer underflow": "arithmetic",
    "overflow": "arithmetic",
    "underflow": "arithmetic",
    "rounding": "arithmetic",
    "precision loss": "arithmetic",
    "missing access control": "access-control",
    "unprotected function": "access-control",
    "owner-only": "access-control",
    "tx.origin": "tx-origin-auth",
    "tx-origin": "tx-origin-auth",
    "unchecked call": "unchecked-low-level-call",
    "unchecked-send": "unchecked-low-level-call",
    "unchecked-lowlevel": "unchecked-low-level-call",
    "dos": "denial-of-service",
    "denial of service": "denial-of-service",
    "weak randomness": "bad-randomness",
    "predictable randomness": "bad-randomness",
    "block timestamp": "time-manipulation",
    "timestamp dependence": "time-manipulation",
    "oracle manipulation": "price-oracle-manipulation",
    "price manipulation": "price-oracle-manipulation",
    "spot price": "price-oracle-manipulation",
    "flashloan": "flash-loan-attack",
    "flash loan": "flash-loan-attack",
    "business logic": "logic-error",
    "logic bug": "logic-error",
    "accounting": "bad-accounting",
    "balance mismatch": "bad-accounting",
    "uninitialized-state": "uninitialized-storage",
    "uninitialized-storage-pointer": "uninitialized-storage",
    "delegatecall": "delegatecall-injection",
    "controlled-delegatecall": "delegatecall-injection",
    "signature replay": "signature-replay",
    "missing-nonce": "signature-replay",
    "suicidal": "unprotected-selfdestruct",
}

# Slither detector check -> canonical
SCANNER_MAP: dict[str, str] = {
    "reentrancy-eth": "reentrancy",
    "reentrancy-no-eth": "reentrancy",
    "reentrancy-benign": "reentrancy",
    "reentrancy-events": "reentrancy",
    "arbitrary-send-eth": "access-control",
    "arbitrary-send-erc20": "access-control",
    "suicidal": "unprotected-selfdestruct",
    "unprotected-upgrade": "access-control",
    "tx-origin": "tx-origin-auth",
    "unchecked-transfer": "unchecked-low-level-call",
    "unchecked-lowlevel": "unchecked-low-level-call",
    "unchecked-send": "unchecked-low-level-call",
    "weak-prng": "bad-randomness",
    "timestamp": "time-manipulation",
    "controlled-delegatecall": "delegatecall-injection",
    "delegatecall-loop": "delegatecall-injection",
    "uninitialized-state": "uninitialized-storage",
    "uninitialized-storage": "uninitialized-storage",
    "divide-before-multiply": "arithmetic",
    "incorrect-equality": "logic-error",
    "locked-ether": "denial-of-service",
    "calls-loop": "denial-of-service",
}

# SWC registry code -> canonical (partial)
SWC_MAP: dict[str, str] = {
    "SWC-107": "reentrancy",
    "SWC-101": "arithmetic",
    "SWC-104": "unchecked-low-level-call",
    "SWC-105": "access-control",
    "SWC-106": "unprotected-selfdestruct",
    "SWC-115": "tx-origin-auth",
    "SWC-116": "time-manipulation",
    "SWC-120": "bad-randomness",
    "SWC-112": "delegatecall-injection",
    "SWC-109": "uninitialized-storage",
    "SWC-114": "front-running",
    "SWC-113": "denial-of-service",
    "SWC-121": "signature-replay",
}


def to_canonical(raw: str) -> str:
    """Map an arbitrary kind-of-flaw string to a canonical kind."""
    if not raw:
        return "other"
    key = raw.strip().lower()
    if key in FLAW_KINDS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    if key.upper() in SWC_MAP:
        return SWC_MAP[key.upper()]
    if key in SCANNER_MAP:
        return SCANNER_MAP[key]
    for alias, canon in ALIASES.items():
        if alias in key:
            return canon
    return "other"

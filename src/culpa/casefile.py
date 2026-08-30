"""Shared types. Every part of Culpa speaks these.

A *case* is a contract (or set of contracts) brought in for investigation, with the truth we
already know about it. An *investigator* produces a *dossier* of *findings*. A finding worth its
salt carries an *exploit draft* that the *proof stage* runs; if the exploit lands, the finding
is proven.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["high", "medium", "low", "info"]


# --------------------------------------------------------------------------- #
# What we already know about a case (ground truth)
# --------------------------------------------------------------------------- #
class KnownFlaw(BaseModel):
    category: str                       # canonical (see lexicon.FLAW_KINDS)
    severity: Severity = "high"
    swc: Optional[str] = None
    lines: list[int] = Field(default_factory=list)
    note: str = ""


class KnownTruth(BaseModel):
    is_vulnerable: bool = True
    flaws: list[KnownFlaw] = Field(default_factory=list)


class ChainSnapshot(BaseModel):
    chain: str = "mainnet"
    block: int
    rpc_env: str = "MAINNET_RPC_URL"


class Subject(BaseModel):
    name: str
    address: Optional[str] = None       # set when the subject is already on chain
    path: Optional[str] = None          # set when we have the source (relative to casework/)


class ExpectedProof(BaseModel):
    provable: bool = False
    min_profit_wei: Optional[str] = None      # kept as a string to survive JSON
    reference_proof: Optional[str] = None     # relative path
    mode: Literal["local", "fork"] = "local"
    notes: str = ""


class Case(BaseModel):
    name: str
    origin: str                         # "smartbugs-curated" | "defihacklabs" | "custom"
    headline: str = ""
    compiler_version: Optional[str] = None
    subject_path: Optional[str] = None          # single-file convenience
    subjects: list[Subject] = Field(default_factory=list)
    snapshot: Optional[ChainSnapshot] = None
    known_truth: KnownTruth = Field(default_factory=KnownTruth)
    expected_proof: ExpectedProof = Field(default_factory=ExpectedProof)
    tags: list[str] = Field(default_factory=list)

    @property
    def primary_subject_path(self) -> Optional[str]:
        if self.subject_path:
            return self.subject_path
        for s in self.subjects:
            if s.path:
                return s.path
        return None


# --------------------------------------------------------------------------- #
# What an investigator hands back
# --------------------------------------------------------------------------- #
class ExploitDraft(BaseModel):
    """An exploit the sleuth wrote and wants the proof stage to run."""
    label: str                          # unique within a case, e.g. "HallOfMirrors::lead-one"
    proof_contract: str                 # forge --match-contract target, e.g. "ProveHallOfMirrors"
    source: str                         # full .t.sol file contents
    mode: Literal["local", "fork"] = "local"
    snapshot: Optional[ChainSnapshot] = None
    sleuth_believes: Optional[bool] = None   # what the sleuth thought before the proof stage ran


class Finding(BaseModel):
    category: str                       # canonical
    severity: Severity = "medium"
    confidence: float = 0.5             # 0..1
    title: str = ""
    lines: list[int] = Field(default_factory=list)
    rationale: str = ""
    source: Literal["scanner", "counsel", "sleuth"] = "sleuth"
    proof: Optional[ExploitDraft] = None


class Dossier(BaseModel):
    case_name: str
    findings: list[Finding] = Field(default_factory=list)
    model: Optional[str] = None
    cost_usd: float = 0.0
    duration_s: float = 0.0
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# What the proof stage reports back
# --------------------------------------------------------------------------- #
class ProofOutcome(BaseModel):
    label: str
    compiled: bool = False
    ran: bool = False
    passed: bool = False
    exploit_landed: bool = False        # test passed AND assertExploitLanded held
    profit: Optional[str] = None
    duration_s: float = 0.0
    logs: str = ""
    error: Optional[str] = None

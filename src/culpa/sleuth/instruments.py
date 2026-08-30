"""What the sleuth can pick up and use. Keep the set small; each is honest about failing."""
from __future__ import annotations

from ..baseline.scanner import ScannerPass
from ..casefile import Case, ExploitDraft, ProofOutcome
from ..proof.staging import stage


def scanner_notes(case: Case) -> str:
    """Run Slither once and hand back a short readable summary for background."""
    dossier = ScannerPass().look(case)
    if dossier.error:
        return f"(slither unavailable: {dossier.error})"
    if not dossier.findings:
        return "(slither raised nothing)"
    return "\n".join(
        f"- [{f.severity}] {f.title} at lines {f.lines}: {f.rationale[:160]}"
        for f in dossier.findings
    )


def stage_exploit(draft: ExploitDraft) -> ProofOutcome:
    """Write the exploit into the proofground and run it; report whether it landed."""
    return stage(draft)

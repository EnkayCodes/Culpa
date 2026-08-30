"""Orchestration wiring, exercised offline with a stub investigator and stub proof stage."""
import marlowe.proceedings as proceedings
from marlowe.casefile import Dossier, ExploitDraft, Finding, ProofOutcome


class StubInvestigator:
    name = "stub"

    def __init__(self, finding_kinds: dict[str, list[str]]):
        self.finding_kinds = finding_kinds

    def look(self, case) -> Dossier:
        findings = [
            Finding(
                category=kind,
                proof=ExploitDraft(label=f"{case.name}::{kind}", proof_contract="P",
                                   source="x", sleuth_believes=True),
            )
            for kind in self.finding_kinds.get(case.name, [])
        ]
        return Dossier(case_name=case.name, findings=findings, cost_usd=0.05, duration_s=1.0)


def test_try_cases_scores_a_run(monkeypatch):
    monkeypatch.setattr(proceedings, "assign_investigator",
                        lambda kind: StubInvestigator({"HollowVault": ["reentrancy"]}))
    monkeypatch.setattr(proceedings, "stage",
                        lambda draft: ProofOutcome(label=draft.label, exploit_landed=True))

    run = proceedings.try_cases("sleuth", "quick")
    assert run["cases"] == 3                      # HollowVault + OpenTill + Irongate
    t = run["tally"]
    # HollowVault and OpenTill are both provable; the stub only backs HollowVault
    assert t["proofs_expected"] == 2
    assert t["proofs_landed"] == 1
    assert t["landed_rate"] == 0.5
    assert t["noise_on_sound_rate"] == 0.0        # nothing named on Irongate


def test_try_cases_records_unbacked_claim(monkeypatch):
    monkeypatch.setattr(proceedings, "assign_investigator",
                        lambda kind: StubInvestigator({"HollowVault": ["reentrancy"]}))
    monkeypatch.setattr(proceedings, "stage",
                        lambda draft: ProofOutcome(label=draft.label, exploit_landed=False))

    run = proceedings.try_cases("sleuth", "quick")
    assert run["tally"]["proofs_landed"] == 0
    assert run["tally"]["landed_rate"] == 0.0
    assert run["tally"]["unbacked_claims"] == 1

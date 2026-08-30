"""The audit note renders from a run dict without choking on proven / unproven / sound cases."""
from culpa.auditnote import audit_markdown


def _run():
    return {
        "investigator": "sleuth",
        "selection": "quick",
        "model": "gemini-3.5-flash-lite",
        "records": [
            {
                "case": "HollowVault",
                "dossier": {"error": None, "findings": [
                    {"category": "reentrancy", "severity": "high",
                     "rationale": "external call before state update",
                     "proof": {"label": "HollowVault::l1", "source": "contract X {}"}},
                ]},
                "proofs": {"HollowVault::l1": {"exploit_landed": True, "profit": "6000000000000000000"}},
            },
            {
                "case": "Irongate",
                "dossier": {"error": None, "findings": []},
                "proofs": {},
            },
            {
                "case": "Murky",
                "dossier": {"error": None, "findings": [
                    {"category": "logic-error", "severity": "medium", "rationale": "maybe",
                     "proof": {"label": "Murky::l1", "source": "contract Y {}"}},
                ]},
                "proofs": {"Murky::l1": {"exploit_landed": False, "error": "compile failed"}},
            },
        ],
    }


def test_renders_all_three_kinds():
    md = audit_markdown(_run())
    assert "# Culpa audit — sleuth on `quick`" in md
    assert "1 proven with a landed exploit" in md
    assert "HollowVault — reentrancy" in md and "✅ PROVEN" in md
    assert "attacker profit = `6000000000000000000`" in md
    assert "Irongate | no findings | —" in md
    assert "did not land" in md                       # Murky's unconfirmed section
    assert "checks-effects-interactions" in md        # reentrancy remediation

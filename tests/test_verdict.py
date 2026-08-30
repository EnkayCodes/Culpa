"""The scoring math — the heart of 'measured improvement'."""
import pytest

from marlowe.casefile import (
    Case, Dossier, ExpectedProof, ExploitDraft, Finding, KnownFlaw, KnownTruth, ProofOutcome,
)
from marlowe.verdict import tally, weigh_case


def _case(name, kinds, vulnerable=True, provable=False):
    return Case(
        name=name, origin="custom",
        known_truth=KnownTruth(
            is_vulnerable=vulnerable,
            flaws=[KnownFlaw(category=k) for k in kinds],
        ),
        expected_proof=ExpectedProof(provable=provable),
    )


def _dossier(name, kinds, cost=0.0, dur=0.0, proof_for=None, believes=None):
    findings = []
    for k in kinds:
        draft = None
        if proof_for and k in proof_for:
            draft = ExploitDraft(label=f"{name}::{k}", proof_contract="X", source="",
                                 sleuth_believes=believes)
        findings.append(Finding(category=k, proof=draft))
    return Dossier(case_name=name, findings=findings, cost_usd=cost, duration_s=dur)


def test_hit_noise_miss():
    card = weigh_case(_case("a", ["reentrancy"]), _dossier("a", ["reentrancy", "arithmetic"]))
    assert card.hits == {"reentrancy"}
    assert card.noise == {"arithmetic"}
    assert card.misses == set()


def test_sound_contract_flagged_is_noise():
    card = weigh_case(_case("sound", [], vulnerable=False), _dossier("sound", ["reentrancy"]))
    assert card.is_sound and card.named_anything
    assert card.hits == set() and card.noise == {"reentrancy"}


def test_tally_micro_f1():
    cards = [
        weigh_case(_case("a", ["reentrancy"]), _dossier("a", ["reentrancy"])),
        weigh_case(_case("b", ["access-control"]), _dossier("b", ["access-control", "reentrancy"])),
        weigh_case(_case("c", ["arithmetic"]), _dossier("c", [])),
        weigh_case(_case("d", [], vulnerable=False), _dossier("d", ["bad-randomness"])),
    ]
    t = tally(cards)
    assert (t.hits, t.noise, t.misses) == (2, 2, 1)
    assert t.micro_precision == pytest.approx(0.5)
    assert round(t.micro_recall, 3) == 0.667
    assert t.sound == 1
    assert t.noise_on_sound_rate == 1.0


def test_exploit_proven_when_it_lands():
    case = _case("e", ["reentrancy"], provable=True)
    dossier = _dossier("e", ["reentrancy"], proof_for={"reentrancy"}, believes=True)
    outcomes = {"e::reentrancy": ProofOutcome(label="e::reentrancy", exploit_landed=True)}
    card = weigh_case(case, dossier, outcomes)
    assert card.proofs_expected == 1 and card.proofs_landed == 1
    assert card.unbacked_claims == 0
    assert tally([card]).landed_rate == 1.0


def test_unbacked_claim_when_exploit_fails():
    case = _case("f", ["reentrancy"], provable=True)
    dossier = _dossier("f", ["reentrancy"], proof_for={"reentrancy"}, believes=True)
    outcomes = {"f::reentrancy": ProofOutcome(label="f::reentrancy", exploit_landed=False)}
    card = weigh_case(case, dossier, outcomes)
    assert card.proofs_landed == 0
    assert card.unbacked_claims == 1


def test_cost_and_time_add_up():
    cards = [
        weigh_case(_case("a", ["reentrancy"]), _dossier("a", ["reentrancy"], cost=0.10, dur=30)),
        weigh_case(_case("b", ["reentrancy"]), _dossier("b", ["reentrancy"], cost=0.20, dur=50)),
    ]
    t = tally(cards)
    assert t.total_cost_usd == pytest.approx(0.30)
    assert t.cost_per_case == pytest.approx(0.15)
    assert t.duration_per_case == pytest.approx(40)

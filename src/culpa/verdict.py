"""How Culpa keeps score. Pure functions, no I/O — covered by tests/test_verdict.py.

Detection is weighed as a multi-label problem over canonical flaw kinds:
  - hit  : a kind the investigator named that is in the known truth
  - miss : a kind in the known truth the investigator did not name
  - noise: a kind the investigator named that is not in the known truth
Contracts known to be sound contribute only to the noise-on-sound rate.

The headline number is `landed_rate`: of the flaws we expect a proof for, how many did the
investigator back with an exploit that the proof stage actually ran and that landed.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .casefile import Case, Dossier, ProofOutcome
from .lexicon import to_canonical


@dataclass
class Scorecard:
    case_name: str
    is_sound: bool
    hits: set[str] = field(default_factory=set)
    noise: set[str] = field(default_factory=set)
    misses: set[str] = field(default_factory=set)
    named_anything: bool = False
    proofs_expected: int = 0
    proofs_landed: int = 0
    unbacked_claims: int = 0            # exploit claimed to land but the proof stage disagreed
    cost_usd: float = 0.0
    duration_s: float = 0.0
    error: str | None = None


@dataclass
class Tally:
    cases: int = 0
    vulnerable: int = 0
    sound: int = 0
    hits: int = 0
    noise: int = 0
    misses: int = 0
    micro_precision: float = 0.0
    micro_recall: float = 0.0
    micro_f1: float = 0.0
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    noise_on_sound_rate: float = 0.0
    proofs_expected: int = 0
    proofs_landed: int = 0
    landed_rate: float = 0.0
    unbacked_claims: int = 0
    errored: int = 0
    total_cost_usd: float = 0.0
    cost_per_case: float = 0.0
    total_duration_s: float = 0.0
    duration_per_case: float = 0.0
    by_kind: dict[str, dict[str, float]] = field(default_factory=dict)


def _f1(p: float, r: float) -> float:
    return (2 * p * r / (p + r)) if (p + r) else 0.0


def weigh_case(
    case: Case,
    dossier: Dossier,
    proofs: dict[str, ProofOutcome] | None = None,
) -> Scorecard:
    proofs = proofs or {}
    is_sound = not case.known_truth.is_vulnerable

    truth: set[str] = set() if is_sound else {to_canonical(f.category) for f in case.known_truth.flaws}
    named: set[str] = {to_canonical(f.category) for f in dossier.findings}

    card = Scorecard(
        case_name=case.name,
        is_sound=is_sound,
        hits=named & truth,
        noise=named - truth,
        misses=truth - named,
        named_anything=bool(dossier.findings),
        cost_usd=dossier.cost_usd,
        duration_s=dossier.duration_s,
        error=dossier.error,
    )

    if case.expected_proof.provable and not is_sound:
        card.proofs_expected = 1
        landed = False
        for f in dossier.findings:
            if not f.proof:
                continue
            outcome = proofs.get(f.proof.label)
            if outcome is not None and outcome.exploit_landed:
                landed = True
            elif f.proof.sleuth_believes and (outcome is None or not outcome.exploit_landed):
                card.unbacked_claims += 1
        card.proofs_landed = 1 if landed else 0

    return card


def tally(cards: list[Scorecard]) -> Tally:
    t = Tally(cases=len(cards))
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # kind -> [hit, noise, miss]

    for c in cards:
        t.sound += int(c.is_sound)
        t.vulnerable += int(not c.is_sound)
        t.errored += int(bool(c.error))
        t.hits += len(c.hits)
        t.noise += len(c.noise)
        t.misses += len(c.misses)
        t.proofs_expected += c.proofs_expected
        t.proofs_landed += c.proofs_landed
        t.unbacked_claims += c.unbacked_claims
        t.total_cost_usd += c.cost_usd
        t.total_duration_s += c.duration_s
        for k in c.hits:
            per[k][0] += 1
        for k in c.noise:
            per[k][1] += 1
        for k in c.misses:
            per[k][2] += 1

    t.micro_precision = t.hits / (t.hits + t.noise) if (t.hits + t.noise) else 0.0
    t.micro_recall = t.hits / (t.hits + t.misses) if (t.hits + t.misses) else 0.0
    t.micro_f1 = _f1(t.micro_precision, t.micro_recall)

    ps, rs, fs = [], [], []
    for kind, (hit, noise, miss) in sorted(per.items()):
        p = hit / (hit + noise) if (hit + noise) else 0.0
        r = hit / (hit + miss) if (hit + miss) else 0.0
        ps.append(p)
        rs.append(r)
        fs.append(_f1(p, r))
        t.by_kind[kind] = {"precision": p, "recall": r, "f1": _f1(p, r), "support": hit + miss}
    t.macro_precision = sum(ps) / len(ps) if ps else 0.0
    t.macro_recall = sum(rs) / len(rs) if rs else 0.0
    t.macro_f1 = sum(fs) / len(fs) if fs else 0.0

    noisy_sound = sum(1 for c in cards if c.is_sound and c.named_anything)
    t.noise_on_sound_rate = noisy_sound / t.sound if t.sound else 0.0

    t.landed_rate = t.proofs_landed / t.proofs_expected if t.proofs_expected else 0.0
    t.cost_per_case = t.total_cost_usd / t.cases if t.cases else 0.0
    t.duration_per_case = t.total_duration_s / t.cases if t.cases else 0.0
    return t

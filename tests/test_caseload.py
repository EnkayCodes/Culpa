"""Every case file holds up, and the lexicon stays canonical."""
from marlowe.caseload import load_cases, load_schema, resolve_in_casework
from marlowe.lexicon import FLAW_KINDS, to_canonical


def test_every_case_holds_up():
    cases = load_cases("full")
    assert len(cases) >= 3
    names = [c.name for c in cases]
    assert len(names) == len(set(names)), "two cases share a name"


def test_known_truth_is_canonical():
    for case in load_cases("full"):
        for flaw in case.known_truth.flaws:
            assert to_canonical(flaw.category) in FLAW_KINDS
            assert flaw.category in FLAW_KINDS, f"{case.name}: {flaw.category!r} is not canonical"


def test_provable_cases_point_at_a_real_file():
    for case in load_cases("full"):
        want = case.expected_proof
        if want.provable and want.reference_proof and "template" not in case.tags:
            assert resolve_in_casework(want.reference_proof).exists(), \
                f"{case.name}: missing {want.reference_proof}"


def test_schema_loads():
    assert load_schema()["title"] == "Marlowe case file"


def test_to_canonical_examples():
    assert to_canonical("reentrancy-eth") == "reentrancy"
    assert to_canonical("Integer Overflow") == "arithmetic"
    assert to_canonical("SWC-107") == "reentrancy"
    assert to_canonical("tx.origin") == "tx-origin-auth"
    assert to_canonical("something odd") == "other"

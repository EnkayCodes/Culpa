"""Turn two tallies into a side-by-side write-up (markdown)."""
from __future__ import annotations

from .verdict import Tally


def _row(label: str, a: float, b: float, fmt: str = "{:.2f}", lower_is_better: bool = False) -> str:
    delta = b - a
    mark = ""
    if abs(delta) > 1e-9:
        better = (delta < 0) if lower_is_better else (delta > 0)
        mark = " (better)" if better else " (worse)"
    return f"| {label} | {fmt.format(a)} | {fmt.format(b)} | {delta:+.2f}{mark} |"


def write_comparison(name_a: str, a: Tally, name_b: str, b: Tally) -> str:
    lines = [
        f"# {name_a} against {name_b}",
        "",
        f"- Cases: {a.cases}  ·  vulnerable: {a.vulnerable}  ·  sound: {a.sound}",
        f"- Proofs expected: {a.proofs_expected}",
        "",
        f"| Measure | {name_a} | {name_b} | change |",
        "|---|---|---|---|",
        _row("Proven-exploit rate", a.landed_rate, b.landed_rate),
        f"| Exploits proven | {a.proofs_landed} of {a.proofs_expected} "
        f"| {b.proofs_landed} of {b.proofs_expected} | |",
        _row("Kind precision (micro)", a.micro_precision, b.micro_precision),
        _row("Kind recall (micro)", a.micro_recall, b.micro_recall),
        _row("Kind F1 (micro)", a.micro_f1, b.micro_f1),
        _row("Kind F1 (macro)", a.macro_f1, b.macro_f1),
        _row("Noise on sound contracts", a.noise_on_sound_rate, b.noise_on_sound_rate,
             lower_is_better=True),
        f"| Unbacked exploit claims | {a.unbacked_claims} | {b.unbacked_claims} | |",
        _row("Cost per contract", a.cost_per_case, b.cost_per_case, "${:.3f}", lower_is_better=True),
        _row("Time per contract (s)", a.duration_per_case, b.duration_per_case, "{:.1f}",
             lower_is_better=True),
        f"| Cases that errored | {a.errored} | {b.errored} | |",
        "",
        "## F1 by flaw kind",
        "",
        f"| Kind | {name_a} | {name_b} | cases |",
        "|---|---|---|---|",
    ]
    for kind in sorted(set(a.by_kind) | set(b.by_kind)):
        fa = a.by_kind.get(kind, {}).get("f1", 0.0)
        fb = b.by_kind.get(kind, {}).get("f1", 0.0)
        support = int(b.by_kind.get(kind, a.by_kind.get(kind, {})).get("support", 0))
        lines.append(f"| {kind} | {fa:.2f} | {fb:.2f} | {support} |")
    lines.append("")
    return "\n".join(lines)

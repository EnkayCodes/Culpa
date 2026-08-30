"""Turn a findings run into an audit note a person would sign — Markdown."""
from __future__ import annotations

from .lexicon import to_canonical

_VERDICT_SOUND = "no findings"
_VERDICT_VULN = "vulnerable"

REMEDIATION: dict[str, str] = {
    "reentrancy": "Apply checks-effects-interactions — update state before the external call — "
                  "or wrap the function in a reentrancy guard.",
    "access-control": "Restrict the function to an authorized role. A function that moves funds "
                      "must never be callable by an arbitrary address.",
    "price-oracle-manipulation": "Do not use an AMM spot price as an oracle. Use a TWAP, a "
                                 "dedicated price feed, or a manipulation-resistant source, and "
                                 "sanity-check against a second source.",
    "flash-loan-attack": "Assume any single-transaction balance or price can be moved by a flash "
                         "loan. Use TWAPs, per-block caps, and invariants that must hold "
                         "mid-transaction.",
    "arithmetic": "Remove the `unchecked` block or add explicit bounds checks; on Solidity <0.8 "
                  "use SafeMath.",
    "tx-origin-auth": "Authenticate with `msg.sender`, never `tx.origin` — `tx.origin` lets a "
                      "phished user's call be relayed by an attacker contract.",
    "unprotected-selfdestruct": "Guard `selfdestruct` behind an owner check, or remove it.",
    "delegatecall-injection": "Never `delegatecall` to a caller-supplied address. Whitelist "
                              "implementations and make upgrades owner-only.",
    "bad-randomness": "Do not derive randomness from block values. Use commit-reveal or a VRF.",
    "unchecked-low-level-call": "Check the boolean return of every low-level call and revert on "
                                "failure.",
    "logic-error": "Re-examine the invariant the function should preserve and add property tests "
                   "around it.",
    "bad-accounting": "Reconcile internal accounting against real token balances; guard against "
                      "donation / first-depositor inflation.",
    "denial-of-service": "Use pull payments instead of pushing funds to arbitrary addresses.",
    "uninitialized-storage": "Initialize all storage and avoid uninitialized storage pointers.",
    "signature-replay": "Include a nonce and the chain id in the signed payload; record used "
                        "signatures.",
    "front-running": "Use commit-reveal or an order-independent design; add slippage bounds.",
    "time-manipulation": "Do not rely on `block.timestamp` for logic inside miner-manipulable "
                         "windows.",
    "other": "Review the flagged code path against its intended invariant.",
}


def _severity_badge(sev: str) -> str:
    return {"high": "🔴 high", "medium": "🟠 medium", "low": "🟡 low"}.get(sev, sev)


def audit_markdown(run: dict) -> str:
    recs = run["records"]
    n_findings = sum(len(r["dossier"]["findings"]) for r in recs)
    n_proven = sum(
        1 for r in recs for f in r["dossier"]["findings"]
        if f.get("proof") and r["proofs"].get(f["proof"]["label"], {}).get("exploit_landed")
    )

    out: list[str] = [
        f"# Culpa audit — {run['investigator']} on `{run['selection']}`",
        "",
        f"Model: `{run['model']}` · {len(recs)} contract(s) · {n_findings} finding(s), "
        f"{n_proven} proven with a landed exploit",
        "",
        "## Summary",
        "",
        "| Contract | Verdict | Findings |",
        "|---|---|---|",
    ]
    for r in recs:
        fs = r["dossier"]["findings"]
        verdict = _VERDICT_VULN if fs else _VERDICT_SOUND
        cells = ", ".join(
            f"{to_canonical(f['category'])} ({f['severity']}"
            + (", PROVEN" if _proven(r, f) else "") + ")"
            for f in fs
        ) or "—"
        out.append(f"| {r['case']} | {verdict} | {cells} |")

    for r in recs:
        for f in r["dossier"]["findings"]:
            out += _finding_section(r, f)

    errored = [r["case"] for r in recs if r["dossier"].get("error")]
    if errored:
        out += ["", "## Not assessed", "", "Culpa could not complete: " + ", ".join(errored)]
    out.append("")
    return "\n".join(out)


def _proven(rec: dict, finding: dict) -> bool:
    p = finding.get("proof")
    return bool(p and rec["proofs"].get(p["label"], {}).get("exploit_landed"))


def _finding_section(rec: dict, finding: dict) -> list[str]:
    cat = to_canonical(finding["category"])
    proven = _proven(rec, finding)
    head = f"## {rec['case']} — {cat} ({_severity_badge(finding['severity'])})"
    head += " · ✅ PROVEN" if proven else " · unconfirmed"
    lines = ["", head, "", finding.get("rationale") or "(no rationale)"]

    if proven:
        outcome = rec["proofs"][finding["proof"]["label"]]
        lines += [
            "",
            f"**Proven on a local chain.** The exploit below runs green under `forge test`"
            + (f"; attacker profit = `{outcome['profit']}`." if outcome.get("profit") else "."),
            "",
            "```solidity",
            finding["proof"]["source"].strip(),
            "```",
        ]
    elif finding.get("proof"):
        outcome = rec["proofs"].get(finding["proof"]["label"], {})
        lines += ["", f"_Exploit attempt did not land: {outcome.get('error', 'unknown')}._"]

    lines += ["", f"**Remediation.** {REMEDIATION.get(cat, REMEDIATION['other'])}", "", "---"]
    return lines

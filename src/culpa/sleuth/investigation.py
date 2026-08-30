"""The sleuth: chase leads, write an exploit for each, stage it, keep only what lands, close.

Handles two kinds of case:
  * source cases  — the subject is on disk; deploy it in the exploit.
  * fork cases    — the subject is a live address; the exploit forks mainnet at a pinned block.

Iterate during the sprint on briefings.py, the retry approach, and whether a second read of
the findings helps. Every change earns a CHANGELOG entry with before/after numbers.
"""
from __future__ import annotations

import time

from ..counsel import ask
from ..casefile import Case, Dossier, ExploitDraft, Finding
from ..investigator import read_subject_source
from ..lexicon import FLAW_KINDS, to_canonical
from ..preferences import preferences
from . import briefings
from .casebook import Casebook
from .instruments import scanner_notes, stage_exploit

_SEV_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}


class Sleuth:
    name = "culpa-sleuth"

    def look(self, case: Case) -> Dossier:
        prefs = preferences()["sleuth"]
        dossier = Dossier(case_name=case.name)
        start = time.time()

        source = read_subject_source(case)
        on_fork = case.snapshot is not None
        if not source and not on_fork:
            dossier.error = "this case has neither source nor a fork snapshot"
            dossier.duration_s = time.time() - start
            return dossier

        briefing_text = source or _fork_briefing(case)
        subject_file = (case.primary_subject_path or "").split("/")[-1]
        fork_hint = _fork_hint(case) if on_fork else ""

        book = Casebook(case.name)
        try:
            notes = scanner_notes(case) if source else "(no source to scan)"
            book.came_back("slither", notes=notes)

            leads = self._chase_leads(briefing_text, notes, prefs, dossier, book)

            floor = _SEV_RANK[prefs.get("min_severity_to_prove", "medium")]
            ledger: list[dict] = []
            for lead in leads:
                sev = str(lead.get("severity", "medium")).lower()
                lead_id = str(lead.get("id", f"lead-{len(ledger) + 1}"))
                if _SEV_RANK.get(sev, 2) < floor:
                    ledger.append({**lead, "proof_label": None, "proven": False,
                                   "why": "below the severity floor for a proof"})
                    continue

                label = f"{case.name}::{lead_id}"
                proof_name = f"Prove{case.name}{_camel(lead_id)}"
                draft = self._write_exploit(
                    lead, proof_name, label, subject_file, briefing_text, fork_hint,
                    case, on_fork, book, tries=prefs["max_proof_attempts"],
                )
                outcome = stage_exploit(draft)
                book.came_back("stage_exploit", label=label, landed=outcome.exploit_landed,
                               compiled=outcome.compiled, error=outcome.error,
                               logs=outcome.logs[-2000:])
                draft.sleuth_believes = True
                ledger.append({**lead, "proof_label": label, "proven": outcome.exploit_landed,
                               "draft": draft, "snag": outcome.error})

            self._close(case, ledger, dossier, book)
        except Exception as e:  # noqa: BLE001 - an investigator must not raise
            dossier.error = f"{type(e).__name__}: {e}"
            book.snag(dossier.error)
        finally:
            book.close()

        dossier.duration_s = time.time() - start
        return dossier

    # -- stages ------------------------------------------------------------- #
    def _chase_leads(self, briefing, notes, prefs, dossier, book) -> list[dict]:
        q = briefings.LEADS_QUESTION.format(
            source=briefing[:60000], scanner_notes=notes,
            max_leads=prefs["max_leads"], kinds=sorted(FLAW_KINDS),
        )
        book.asked(briefings.LEADS_INSTRUCTIONS, q, stage="leads")
        reply = ask(briefings.LEADS_INSTRUCTIONS, q)
        book.heard(reply)
        dossier.cost_usd += reply.cost_usd
        dossier.model = reply.model
        return reply.as_list()

    def _write_exploit(self, lead, proof_name, label, subject_file, briefing, fork_hint,
                       case: Case, on_fork: bool, book, tries: int) -> ExploitDraft:
        prior_snag = ""
        draft = ExploitDraft(
            label=label, proof_contract=proof_name, source="",
            mode="fork" if on_fork else "local",
            snapshot=case.snapshot if on_fork else None,
        )
        for attempt in range(1, tries + 1):
            q = briefings.PROOF_QUESTION.format(
                lead=lead, proof_contract=proof_name, subject_file=subject_file or "<none>",
                fork_hint=fork_hint,
                prior_snag=(f"Your last attempt failed:\n{prior_snag}\nFix it." if prior_snag else ""),
                source=briefing[:40000],
            )
            book.asked(briefings.PROOF_INSTRUCTIONS, q, stage="proof", lead=label, attempt=attempt)
            reply = ask(briefings.PROOF_INSTRUCTIONS, q)
            book.heard(reply)
            draft.source = _strip_fences(reply.text)

            outcome = stage_exploit(draft)
            book.came_back("stage_exploit", attempt=attempt, label=label,
                           compiled=outcome.compiled, landed=outcome.exploit_landed,
                           error=outcome.error)
            if outcome.exploit_landed or attempt == tries:
                return draft
            prior_snag = (outcome.error or "") + "\n" + outcome.logs[-3000:]
        return draft

    def _close(self, case, ledger, dossier, book) -> None:
        told = "\n".join(
            f"{e.get('id')}: {e.get('category')} sev={e.get('severity')} "
            f"proven={e.get('proven')} snag={e.get('snag') or e.get('why') or '-'}"
            for e in ledger
        ) or "(no leads)"
        q = briefings.CLOSING_QUESTION.format(ledger=told)
        book.asked(briefings.CLOSING_INSTRUCTIONS, q, stage="closing")
        reply = ask(briefings.CLOSING_INSTRUCTIONS, q)
        book.heard(reply)
        dossier.cost_usd += reply.cost_usd

        drafts = {e["proof_label"]: e.get("draft") for e in ledger if e.get("proof_label")}
        for f in reply.as_list():
            sev = f.get("severity")
            dossier.findings.append(Finding(
                category=to_canonical(str(f.get("category", "other"))),
                severity=str(sev).lower() if sev in ("high", "medium", "low") else "medium",
                confidence=float(f.get("confidence", 0.5)),
                title=str(f.get("title", ""))[:120],
                lines=[int(x) for x in f.get("lines", []) if isinstance(x, (int, float))][:20],
                rationale=str(f.get("rationale", ""))[:800],
                source="sleuth",
                proof=drafts.get(f.get("proof_label")),
            ))


# -- helpers -------------------------------------------------------------- #
def _fork_briefing(case: Case) -> str:
    lines = [f"Fork case: {case.headline}", ""]
    if case.snapshot:
        lines.append(f"Fork {case.snapshot.chain} at block {case.snapshot.block}.")
    for s in case.subjects:
        lines.append(f"- {s.name}: {s.address}")
    if case.expected_proof.notes:
        lines.append("\n" + case.expected_proof.notes)
    return "\n".join(lines)


def _fork_hint(case: Case) -> str:
    snap = case.snapshot
    addrs = "\n".join(f"//   {s.name} = {s.address}" for s in case.subjects)
    return (
        f"- This is a FORK case. Start test_exploit with:\n"
        f"//   vm.createSelectFork(vm.envString(\"{snap.rpc_env}\"), {snap.block});\n"
        f"{addrs}\n"
        f"  Do not deploy the victim; bind to the addresses above with their interfaces."
    )


def _camel(text: str) -> str:
    return "".join(part.capitalize() for part in text.replace("_", "-").split("-") if part)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    return t.strip()

"""The `marlowe` command line."""
from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(add_completion=False, help="Marlowe — finds a flaw, then proves it with a working exploit")
console = Console()


@app.command()
def check() -> None:
    """Look over every case file and report which tools are on hand."""
    from .caseload import load_cases

    cases = load_cases("full")
    console.print(f"[green]good[/] {len(cases)} case files hold up against the schema")
    for tool in ("forge", "slither", "solc-select"):
        console.print(f"  {tool}: " + ("[green]here[/]" if shutil.which(tool) else "[yellow]missing[/]"))
    import os
    console.print(f"  GEMINI_API_KEY: " + ("[green]set[/]" if os.getenv("GEMINI_API_KEY") else "[yellow]missing[/]"))
    provable = sum(1 for c in cases if c.expected_proof.provable)
    console.print(f"  cases that expect a proof: {provable}")


@app.command()
def consult() -> None:
    """One tiny question to the model, to confirm the Gemini key works."""
    from .counsel import ask

    reply = ask("You reply with exactly the JSON you are asked for, nothing else.",
                'Reply with {"ok": true}.')
    console.print(f"model: {reply.model}   id: {reply.session_id or '-'}")
    console.print(f"reply: {reply.text!r}")
    console.print(f"tokens: {reply.tokens_in} in / {reply.tokens_out} out   "
                  f"notional cost: ${reply.cost_usd:.5f} (free tier is not billed)")
    try:
        console.print(f"[green]parsed[/] {reply.as_json()}")
    except ValueError as e:
        console.print(f"[yellow]could not parse JSON:[/] {e}")


@app.command()
def verify(cases: str = typer.Option("full", help="which cases' reference exploits to run")) -> None:
    """Stage and run every committed reference exploit. Your first sanity check."""
    from .casefile import ExploitDraft
    from .caseload import load_cases, resolve_in_casework
    from .proof.staging import stage

    ok = True
    for case in load_cases(cases):
        want = case.expected_proof
        if not (want.provable and want.reference_proof) or "template" in case.tags:
            continue
        path = resolve_in_casework(want.reference_proof)
        if not path.exists():
            console.print(f"  [yellow]skip[/] {case.name}: {want.reference_proof} missing")
            continue
        draft = ExploitDraft(
            label=f"{case.name}::reference",
            proof_contract=f"Prove{case.name}",
            source=path.read_text(),
            mode=want.mode,
            snapshot=case.snapshot,
        )
        outcome = stage(draft)
        if outcome.exploit_landed:
            console.print(f"  [green]lands[/] {case.name}  (profit={outcome.profit})")
        else:
            ok = False
            console.print(f"  [red]FAILED[/] {case.name}: {outcome.error}")
    raise typer.Exit(0 if ok else 1)


@app.command()
def investigate(
    who: str = typer.Option(..., help="scanner | first-glance | sleuth"),
    cases: str = typer.Option("quick", help="quick | full | hard | <name-prefix>"),
    into: Path = typer.Option(Path("findings/run.json")),
    limit: int = typer.Option(0, help="0 means no limit"),
) -> None:
    """Send one investigator through a set of cases and weigh the result."""
    from .proceedings import save_proceedings, try_cases

    def _step(i: int, n: int, name: str) -> None:
        console.print(f"  [{i}/{n}] {name}")

    proceedings = try_cases(who, cases, limit or None, step=_step)
    save_proceedings(proceedings, into)
    t = proceedings["tally"]
    console.print(
        f"\n[bold]{who}[/] on '{cases}': "
        f"proven {t['proofs_landed']}/{t['proofs_expected']}  "
        f"microF1 {t['micro_f1']:.2f}  noise-on-sound {t['noise_on_sound_rate']:.2f}  "
        f"cost ${t['total_cost_usd']:.3f}  ({proceedings['wall_seconds']}s)"
    )
    console.print(f"written to {into}")


@app.command()
def compare(
    first: Path = typer.Argument(..., help="e.g. findings/scanner.json"),
    second: Path = typer.Argument(..., help="e.g. findings/sleuth.json"),
    into: Path = typer.Option(Path("findings/comparison.md")),
) -> None:
    """Put two runs side by side."""
    from .proceedings import load_proceedings, tally_from_proceedings
    from .writeup import write_comparison

    a, b = load_proceedings(first), load_proceedings(second)
    md = write_comparison(a["investigator"], tally_from_proceedings(a),
                          b["investigator"], tally_from_proceedings(b))
    into.parent.mkdir(parents=True, exist_ok=True)
    into.write_text(md)
    console.print(md)
    console.print(f"\nwritten to {into}")


@app.command()
def read(run: Path = typer.Argument(...), case: str = typer.Option(...)) -> None:
    """Read one case's findings as a plain note."""
    from .proceedings import load_proceedings

    data = load_proceedings(run)
    rec = next((r for r in data["records"] if r["case"] == case), None)
    if rec is None:
        raise typer.Exit(f"case {case} is not in this run")
    dossier = rec["dossier"]
    console.rule(f"{case}  ({data['investigator']})")
    if dossier.get("error"):
        console.print(f"[red]snag:[/] {dossier['error']}")
    table = Table("kind", "sev", "conf", "proof", "title")
    for f in dossier["findings"]:
        proof = rec["proofs"].get((f.get("proof") or {}).get("label", ""), {})
        badge = "—"
        if f.get("proof"):
            badge = "[green]PROVEN[/]" if proof.get("exploit_landed") else "[yellow]not proven[/]"
        table.add_row(f["category"], f["severity"], f"{f['confidence']:.2f}", badge, f["title"])
    console.print(table)
    for f in dossier["findings"]:
        if f.get("rationale"):
            console.print(f"\n[bold]{f['category']}[/]: {f['rationale']}")


if __name__ == "__main__":
    app()

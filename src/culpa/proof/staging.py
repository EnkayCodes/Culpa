"""Stage a written exploit and judge whether it landed.

Understanding with the sleuth:
  - The exploit file is a forge test importing `@proof/ExploitProof.sol`.
  - Its test contract is named `<ExploitDraft.proof_contract>` with exactly one `test*` function.
  - Landing == that test passes. The exploit assertion (`assertExploitLanded`) lives inside the
    test, so a green test IS a landed exploit. We re-check by reading `forge --json`.

This module never raises: every failure lands in `ProofOutcome.error`.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from ..casefile import ExploitDraft, ProofOutcome
from ..preferences import preferences

STAGED = "test/staged"


def _proofground() -> Path:
    return Path(preferences()["proof"]["proofground"])


def lay_out(draft: ExploitDraft) -> Path:
    ground = _proofground()
    out = ground / STAGED / f"{draft.proof_contract}.t.sol"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(draft.source)
    return out


def clear(draft: ExploitDraft) -> None:
    out = _proofground() / STAGED / f"{draft.proof_contract}.t.sol"
    out.unlink(missing_ok=True)


def stage(draft: ExploitDraft, timeout_s: int | None = None) -> ProofOutcome:
    prefs = preferences()
    timeout_s = timeout_s or prefs["proof"]["timeout_s"]
    ground = _proofground()
    outcome = ProofOutcome(label=draft.label)

    if not draft.source.strip():
        outcome.error = "the sleuth handed over an empty exploit file"
        return outcome

    try:
        lay_out(draft)
    except OSError as e:
        outcome.error = f"could not write the exploit file: {e}"
        return outcome

    casework_dir = ground.parent / "casework"
    cmd = [
        "forge", "test",
        "--root", str(ground),
        "--match-contract", draft.proof_contract,
        "--json", "-vvv",
        "--fuzz-seed", str(prefs["proof"].get("fuzz_seed", 0)),
        "--allow-paths", str(casework_dir),
    ]
    env = os.environ.copy()
    if draft.mode == "fork":
        if not draft.snapshot:
            outcome.error = "mode is fork but no chain snapshot was given"
            return outcome
        rpc = os.getenv(draft.snapshot.rpc_env)
        if not rpc:
            outcome.error = f"env {draft.snapshot.rpc_env} is not set for this fork case"
            return outcome
        cmd += ["--fork-url", rpc, "--fork-block-number", str(draft.snapshot.block)]

    start = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, env=env)
    except FileNotFoundError:
        outcome.error = "forge is not on PATH — install Foundry (see REPRODUCTION.md)"
        return outcome
    except subprocess.TimeoutExpired:
        outcome.duration_s = time.time() - start
        outcome.error = f"forge test ran past {timeout_s}s"
        return outcome
    except OSError as e:
        outcome.error = f"could not launch forge: {e}"
        return outcome

    outcome.duration_s = time.time() - start
    stdout, stderr = proc.stdout or "", proc.stderr or ""
    outcome.logs = stdout[-20000:] + "\n--- stderr ---\n" + stderr[-4000:]

    parsed = _read_forge_json(stdout)
    if parsed is None:
        if "Compiler run failed" in stderr or "error[" in stderr:
            outcome.error = _compile_error(stderr)
        else:
            outcome.error = "could not read forge --json output"
        return outcome

    outcome.compiled = True
    outcome.ran = True
    landed, profit, reason = _judge(parsed, draft.proof_contract)
    outcome.passed = landed
    outcome.exploit_landed = landed
    outcome.profit = profit
    if not landed and reason:
        outcome.error = f"exploit ran but did not land: {reason}"
    return outcome


def _read_forge_json(stdout: str) -> dict | None:
    stdout = (stdout or "").strip()
    if not stdout:
        return None
    # `forge test --json` prints one compact JSON object; some versions precede it with warnings.
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    # last resort: whole-blob parse
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _compile_error(stderr: str) -> str:
    lines = [ln for ln in stderr.splitlines() if ln.strip()]
    head = [ln for ln in lines if ln.startswith("error[") or "Error" in ln][:4]
    return "compile failed: " + " | ".join(head or lines[-4:])


def _judge(parsed: dict, proof_contract: str) -> tuple[bool, str | None, str | None]:
    """Return (every matching test passed, profit if logged, failure reason if any)."""
    passed = True
    saw_a_test = False
    profit: str | None = None
    reason: str | None = None
    for suite_name, suite in parsed.items():
        if not isinstance(suite, dict):
            continue
        for test_name, result in (suite.get("test_results") or {}).items():
            if proof_contract not in suite_name and proof_contract not in test_name:
                continue
            saw_a_test = True
            if result.get("status") != "Success":
                passed = False
                reason = result.get("reason") or reason
            for line in result.get("decoded_logs", []) or []:
                if "profit=" in line:
                    profit = line.split("profit=", 1)[1].strip()
    if not saw_a_test:
        return False, None, f"no test matching {proof_contract} ran"
    return passed, profit, reason

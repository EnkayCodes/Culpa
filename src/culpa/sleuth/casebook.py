"""The sleuth's casebook: a written record of every move made on one case.

One line per entry (JSONL): {at, case, step, kind, ...}. `kind` is one of:
  asked | heard | reached-for | came-back | note | snag
This is a required hackathon deliverable (the agent trajectory).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..preferences import preferences


class Casebook:
    def __init__(self, case_name: str):
        self.case_name = case_name
        self.step = 0
        folder = Path(preferences()["home"]) / "casebooks"
        folder.mkdir(exist_ok=True)
        self.path = folder / f"{case_name}.jsonl"
        self._fh = self.path.open("w")

    def _put(self, kind: str, **payload) -> None:
        self.step += 1
        record = {"at": round(time.time(), 3), "case": self.case_name, "step": self.step,
                  "kind": kind, **payload}
        self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()

    def asked(self, instructions: str, question: str, **meta):
        self._put("asked", instructions=instructions[:2000], question=question[:8000], **meta)

    def heard(self, reply):
        self._put("heard", text=reply.text[:12000], tokens_in=reply.tokens_in,
                  tokens_out=reply.tokens_out, cost_usd=reply.cost_usd,
                  session_id=getattr(reply, "session_id", ""))

    def reached_for(self, name: str, **args):
        self._put("reached-for", name=name, args={k: str(v)[:2000] for k, v in args.items()})

    def came_back(self, name: str, **result):
        self._put("came-back", name=name, result={k: str(v)[:6000] for k, v in result.items()})

    def note(self, text: str):
        self._put("note", text=text)

    def snag(self, text: str):
        self._put("snag", text=text)

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

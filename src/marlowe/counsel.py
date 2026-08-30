"""The model Marlowe consults — Google Gemini via the free-tier API.

Get a key at https://aistudio.google.com/apikey (no card needed) and put it in .env as
GEMINI_API_KEY. The free tier is plenty for staged runs; nothing is billed.

Each consultation is a single question with a single answer: no tools. Marlowe drives the real
work (running Slither, staging exploits) itself.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from .preferences import preferences

# Notional per-million-token prices, for the write-up only. The free tier bills nothing.
_NOTIONAL_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.0-flash": (0.10, 0.40),
}


@dataclass
class Reply:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float          # notional; the free tier is not billed
    model: str
    session_id: str = ""     # Gemini response id, when present

    def as_json(self):
        return dig_out_json(self.text)


def _key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey "
            "and add it to .env"
        )
    return key


def _notional(model: str, tin: int, tout: int) -> float:
    pin, pout = _NOTIONAL_PER_MTOK.get(model, (0.30, 2.50))
    return tin / 1e6 * pin + tout / 1e6 * pout


def ask(instructions: str, question: str, *, model: str | None = None,
        max_tokens: int | None = None, temperature: float = 0.0) -> Reply:
    """Ask the model one question."""
    from google import genai
    from google.genai import types

    prefs = preferences()
    model = model or prefs["model"]
    max_tokens = max_tokens or prefs["max_tokens"]

    client = genai.Client(api_key=_key())
    resp = client.models.generate_content(
        model=model,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=instructions,
            temperature=temperature,
            max_output_tokens=max_tokens,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    text = (resp.text or "").strip()
    usage = getattr(resp, "usage_metadata", None)
    tin = getattr(usage, "prompt_token_count", 0) or 0
    tout = getattr(usage, "candidates_token_count", 0) or 0
    rid = getattr(resp, "response_id", "") or ""

    if not text:
        reason = ""
        for cand in getattr(resp, "candidates", None) or []:
            reason = getattr(cand, "finish_reason", "") or reason
        raise RuntimeError(f"Gemini returned no text (finish_reason={reason!r})")

    return Reply(text, tin, tout, _notional(model, tin, tout), model, rid)


def dig_out_json(text: str):
    """Pull the first JSON object or array out of a reply."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = text.find(opener), text.rfind(closer)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError(f"no JSON in reply: {text[:200]!r}")

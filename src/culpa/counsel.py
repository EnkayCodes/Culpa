"""The model Culpa consults — Google Gemini via the free-tier API.

Get a key at https://aistudio.google.com/apikey (no card needed) and put it in .env as
GEMINI_API_KEY.

The real free-tier constraint is requests-per-DAY, and it is per-model.
  gemini-3.5-flash-lite   default — most headroom
  gemini-3.5-flash        stronger on code — use for the hard cases
  gemini-2.5-flash        legacy, ~20/day — avoid
Check https://ai.google.dev/gemini-api/docs/rate-limits for current numbers.

Each consultation is a single question with a single answer: no tools.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass

from .preferences import preferences

# Notional per-million-token prices, for the write-up only. The free tier bills nothing.
_NOTIONAL_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash": (0.30, 2.50),
    "gemini-3.5-flash-lite": (0.10, 0.40),
    "gemini-3.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.30, 2.50),
}

_MAX_429_RETRIES = 4


@dataclass
class Reply:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float          # notional; the free tier is not billed
    model: str
    session_id: str = ""

    def as_json(self):
        return dig_out_json(self.text)

    def as_list(self) -> list:
        """The reply parsed as a list of dicts (a lone object is wrapped)."""
        data = dig_out_json(self.text)
        if isinstance(data, dict):
            return [data]
        return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def _key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey "
            "and add it to .env"
        )
    return key


def _notional(model: str, tin: int, tout: int) -> float:
    pin, pout = _NOTIONAL_PER_MTOK.get(model, (0.10, 0.40))
    return tin / 1e6 * pin + tout / 1e6 * pout


def _retry_after_seconds(err: Exception) -> float | None:
    m = re.search(r"retry(?:Delay)?['\":\s]+\s*(\d+(?:\.\d+)?)\s*s", str(err), re.I)
    return float(m.group(1)) if m else None


def _recommended_model(err: Exception) -> str | None:
    """A deprecated-model 404 tells you what to switch to — follow the breadcrumb."""
    m = re.search(r"use\s+(?:models/)?(gemini[\w.\-]+)", str(err), re.I)
    return m.group(1) if m else None


def ask(instructions: str, question: str, *, model: str | None = None,
        max_tokens: int | None = None, temperature: float = 0.0) -> Reply:
    """Ask the model one question, backing off on 429 rate limits."""
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types

    prefs = preferences()
    model = model or prefs["model"]
    max_tokens = max_tokens or prefs["max_tokens"]
    client = genai.Client(api_key=_key())

    config = types.GenerateContentConfig(
        system_instruction=instructions,
        temperature=temperature,
        max_output_tokens=max_tokens,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    last_err: Exception | None = None
    swapped_model = False
    for attempt in range(_MAX_429_RETRIES):
        try:
            resp = client.models.generate_content(model=model, contents=question, config=config)
            break
        except genai_errors.ClientError as e:  # noqa: PERF203
            last_err = e
            code = getattr(e, "code", None)
            if code == 404 and not swapped_model:
                alt = _recommended_model(e)
                if alt and alt != model:
                    model = alt
                    swapped_model = True
                    continue
                raise
            if code != 429 or attempt == _MAX_429_RETRIES - 1:
                raise
            wait = _retry_after_seconds(e) or 8 * (attempt + 1)
            time.sleep(min(wait + 1, 65))
    else:  # pragma: no cover
        raise last_err  # type: ignore[misc]

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
    """Pull the JSON object or array out of a reply."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    spans = []
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = text.find(opener), text.rfind(closer)
        if i != -1 and j != -1 and j > i:
            spans.append((i, text[i:j + 1]))
    for _, blob in sorted(spans):
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no JSON in reply: {text[:200]!r}")

"""Tool registry and helpers shared by every tool module.

Conventions (ADK best practice for function tools):
  * plain Python functions, typed parameters with defaults only where meaningful, Google-style docstring
    (the docstring is the tool description the model sees);
  * return a JSON-serialisable dict, always with a "status" key ("ok" | "error") and never raise for bad input;
  * demo data comes from agenthive/tools/fixtures (synthetic, deterministic) — never real customer data;
  * actions with side effects are simulated and say so ("simulated": True) so demos are safe to run.
"""
from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any, Callable

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REGISTRY: dict[str, Callable[..., Any]] = {}
TOOL_META: dict[str, dict[str, str]] = {}


def hive_tool(module: str, kind: str = "function"):
    """Register a function tool. kind: function | skill (wco-ge-skills library) | action (simulated side effect)."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        if fn.__name__ in REGISTRY:
            raise ValueError(f"duplicate tool name {fn.__name__}")
        REGISTRY[fn.__name__] = fn
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        TOOL_META[fn.__name__] = {"module": module, "kind": kind, "summary": doc}
        return fn

    return deco


def _override(rel: str) -> Path | None:
    """Edition-specific copy of a fixture or doc: fixtures/editions/<edition>/<rel>, if present."""
    from ..settings import get_settings

    ed = get_settings().edition
    if ed != "internal":
        p = FIXTURES / "editions" / ed / rel
        if p.exists():
            return p
    return None


@functools.lru_cache(maxsize=256)
def fixture(name: str) -> Any:
    """Load fixtures/<name>.json (cached); the edition's copy wins when it exists."""
    return json.loads((_override(f"{name}.json") or FIXTURES / f"{name}.json").read_text())


def doc_paths(prefix: str = "") -> dict[str, Path]:
    """Sample documents by key (edition copies replace base ones)."""
    from ..settings import get_settings

    out = {p.stem: p for p in sorted((FIXTURES / "docs").glob(f"{prefix}*.md"))}
    ed = get_settings().edition
    if ed != "internal":
        out.update({p.stem: p for p in sorted((FIXTURES / "editions" / ed / "docs").glob(f"{prefix}*.md"))})
    return dict(sorted(out.items()))


def doc_text(key: str) -> str | None:
    p = _override(f"docs/{key}.md") or FIXTURES / "docs" / f"{key}.md"
    return p.read_text() if p.exists() else None


def ok(**data: Any) -> dict[str, Any]:
    return {"status": "ok", **data}


def err(message: str, **data: Any) -> dict[str, Any]:
    return {"status": "error", "error": message, **data}


# --- lightweight structured LLM calls for "skills" (always the cheapest tier) ------------------------------------

_client = None


def _genai_client():
    global _client
    if _client is None:
        from google import genai

        from ..settings import get_settings

        s = get_settings()
        _client = genai.Client(enterprise=True, project=s.project or None, location=s.model_location)
    return _client


def llm_json(prompt: str, schema: dict, tier: str = "lite", parts: list | None = None) -> dict:
    """Ask a Gemini tier for JSON matching `schema` (OpenAPI subset). Used inside skills, not by agents directly."""
    from google.genai import types

    from ..models import tier as get_tier

    t = get_tier(tier)
    contents = [types.Content(role="user", parts=[*(parts or []), types.Part(text=prompt)])]
    try:
        resp = _genai_client().models.generate_content(
            model=t.model_id,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json",
                                               response_schema=schema),
        )
        return json.loads(resp.text or "{}")
    except Exception as e:  # noqa: BLE001 — tools must not raise
        return {"_error": f"{type(e).__name__}: {e}"[:300]}


def offline() -> bool:
    """True when tests run without cloud access (skills then return deterministic fallbacks)."""
    return os.environ.get("HIVE_OFFLINE") == "1"

"""Model tiers — the "Models" building block.

Cost policy: every agent declares the cheapest tier that does its job.

  lite   Gemini Flash-Lite  routing, classification, extraction, templated drafting
  flash  Gemini Flash       default: tool use, analysis, multi-step reasoning over data
  argon  Gemini 4 Argon     only where deep planning / synthesis is the product (Hermes, Daedalus, Thoth, ...)

Model IDs can be overridden per environment without code changes (HIVE_MODEL_LITE / _FLASH / _ARGON).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from typing import TYPE_CHECKING

from .settings import get_settings

if TYPE_CHECKING:  # heavy imports stay lazy so the catalog/UI build needs no ADK
    from google.adk.models import Gemini
    from google.genai import types


@dataclass(frozen=True)
class Tier:
    key: str
    label: str
    model_id: str
    thinking_level: str | None   # Gemini 3+ thinking level; None = model default
    temperature: float
    why: str
    price_hint: str


def _tiers() -> dict[str, Tier]:
    return {
        "lite": Tier("lite", "Gemini Flash-Lite", os.environ.get("HIVE_MODEL_LITE", "gemini-3.5-flash-lite"),
                     None, 0.2, "High-volume, low-latency steps: classify, route, extract, fill templates.",
                     "lowest cost"),
        "flash": Tier("flash", "Gemini Flash", os.environ.get("HIVE_MODEL_FLASH", "gemini-3.5-flash"),
                      "low", 0.3, "Default workhorse: tool calling, grounded analysis, multi-step tasks.",
                      "low cost"),
        "argon": Tier("argon", "Gemini 4 Argon", os.environ.get("HIVE_MODEL_ARGON", "gemini-4-argon"),
                      None, 0.4, "Reserved for deep planning, architecture and cross-specialist synthesis.",
                      "premium — used sparingly"),
    }


TIERS = _tiers()


def tier(key: str) -> Tier:
    if key not in TIERS:
        raise KeyError(f"unknown model tier {key!r}; expected one of {sorted(TIERS)}")
    return TIERS[key]


def model(key: str) -> "Gemini":
    """ADK model object pinned to the Gemini endpoint location (Agent Engine otherwise uses its own region)."""
    from google.adk.models import Gemini

    t = tier(key)
    return Gemini(model=t.model_id, client_kwargs={"enterprise": True, "location": get_settings().model_location})


def content_config(key: str, max_output_tokens: int | None = None) -> "types.GenerateContentConfig":
    from google.genai import types

    t = tier(key)
    kwargs: dict = {"temperature": t.temperature}
    if t.thinking_level:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=t.thinking_level)
    if max_output_tokens:
        kwargs["max_output_tokens"] = max_output_tokens
    return types.GenerateContentConfig(**kwargs)

"""The four ADK building blocks of a catalog agent, described for the UI (no ADK import needed)."""
from __future__ import annotations

from . import grounding as G
from . import models
from .catalog import Agent, load_catalog
from .tools import TOOL_META


def blocks(a: Agent) -> dict:
    """The four ADK building blocks of an agent, for the UI."""
    from .settings import get_settings

    t = models.tier(a.model)
    step_tiers = sorted({s.model for s in a.steps} - {a.model})
    return {
        "model": {"tier": t.key, "label": t.label, "model_id": t.model_id, "why": a.model_reason,
                  "policy": t.why, "cost": t.price_hint,
                  "also_uses": [models.tier(k).label for k in step_tiers]},
        "runtime": {"label": "Vertex AI Agent Engine", "engine": f"Agent Hive · {load_catalog().realm(a.realm).name}",
                    "region": get_settings().engine_region, "pattern": a.pattern,
                    "sessions": "Managed sessions (VertexAiSessionService)",
                    "steps": [{"id": s.id, "name": s.name, "model": s.model, "role": s.role,
                               "agent_ref": s.agent_ref} for s in a.steps]},
        "tools": [{"name": t_, **TOOL_META[t_]} for t_ in a.tools]
                 + [{"name": t_, **TOOL_META[t_], "step": s.name} for s in a.steps for t_ in s.tools],
        "grounding": [G.describe(g, a.realm) for g in a.grounding]
                     + [{**G.describe(g, a.realm), "step": s.name} for s in a.steps for g in s.grounding],
    }

"""Build web/static/catalog.json from the catalog + factory metadata (run at image build time).

    .venv/bin/python web/build_catalog.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HIVE_PROJECT", "")


def build() -> dict:
    from agenthive import models
    from agenthive.blocks import blocks
    from agenthive.catalog import load_catalog
    from agenthive.tools import TOOL_META

    cat = load_catalog()
    realms = []
    for r in cat.realms:
        agents = []
        for a in r.agents:
            d = a.model_dump()
            d["adk_name"] = a.adk_name
            d["blocks"] = blocks(a)
            agents.append(d)
        realms.append({**r.model_dump(exclude={"agents"}), "agents": agents})
    all_agents = cat.agents()
    skills = []
    for s in cat.skills:
        users = [a.id for a in all_agents if s["tool"] in a.tools or any(s["tool"] in st.tools for st in a.steps)]
        skills.append({**s, "used_by": users})
    return {
        "title": cat.title,
        "subtitle": cat.subtitle,
        "statuses": cat.statuses,
        "realms": realms,
        "compositions": [c.model_dump() for c in cat.compositions],
        "security_layers": [l.model_dump() for l in cat.security_layers],
        "skills": skills,
        "tiers": {k: {"label": t.label, "model_id": t.model_id, "why": t.why, "cost": t.price_hint}
                  for k, t in models.TIERS.items()},
        "tools": TOOL_META,
        "counts": {
            "agents": len(all_agents),
            "realms": len(cat.realms),
            "user_realms": sum(1 for r in cat.realms if r.kind == "user"),
            "status": dict(Counter(a.status for a in all_agents)),
            "tier": dict(Counter(a.model for a in all_agents)),
            "pattern": dict(Counter(a.pattern for a in all_agents)),
            "tools": len(TOOL_META),
        },
    }


if __name__ == "__main__":
    out = ROOT / "web" / "static" / "catalog.json"
    data = build()
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {out} — {data['counts']['agents']} agents, {data['counts']['tools']} tools")

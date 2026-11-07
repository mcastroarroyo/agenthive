"""The "Tools" building block: every function tool any hive agent can call, in one registry.

Modules:
  skills      the foundational wco-ge-skills library (also served over MCP by agenthive.mcp_server)
  common      cross-realm helpers (sample documents, ROI, critical path, dates)
  platform / government / enterprise / smb / delivery   domain tools per realm (synthetic data, simulated actions)
"""
from __future__ import annotations

import importlib
import pkgutil

from ._base import REGISTRY, TOOL_META

for _m in pkgutil.iter_modules(__path__):
    if not _m.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_m.name}")


def get_tool(name: str):
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown tool {name!r}") from None


__all__ = ["REGISTRY", "TOOL_META", "get_tool"]

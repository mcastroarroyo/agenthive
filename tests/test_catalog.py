"""Catalog integrity + every agent builds into a valid ADK agent (no network calls)."""
import inspect

import pytest

from agenthive.catalog import load_catalog
from agenthive.tools import REGISTRY, TOOL_META

CAT = load_catalog()
AGENTS = CAT.agents()


def test_catalog_loads():
    assert AGENTS, "no agents loaded"
    assert len({a.id for a in AGENTS}) == len(AGENTS)


@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.id)
def test_agent_spec(agent):
    for t in agent.tools + [t for s in agent.steps for t in s.tools]:
        assert t in REGISTRY, f"{agent.id}: unknown tool {t}"
    assert len(agent.samples) >= 2, f"{agent.id}: needs at least 2 samples"
    if agent.sample_doc:
        from agenthive.tools._base import doc_text
        assert doc_text(agent.sample_doc), f"{agent.id}: missing sample doc {agent.sample_doc}"
    for g in agent.grounding + [g for s in agent.steps for g in s.grounding]:
        if g.startswith("bigquery:"):
            from agenthive.grounding import BQ_TABLES
            for t in g.split(":", 1)[1].split(","):
                assert t in BQ_TABLES, f"{agent.id}: unknown BigQuery table {t}"


@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.id)
def test_agent_builds(agent):
    from agenthive.agents.factory import build_agent
    from agenthive.blocks import blocks
    built = build_agent(agent)
    assert built.name == agent.adk_name
    b = blocks(agent)
    assert set(b) == {"model", "runtime", "tools", "grounding"}


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_tool_contract(name):
    fn = REGISTRY[name]
    doc = inspect.getdoc(fn) or ""
    assert len(doc) > 30, f"{name}: docstring is the tool description — write one"
    sig = inspect.signature(fn)
    for p in sig.parameters.values():
        assert p.annotation is not inspect.Parameter.empty, f"{name}.{p.name} needs a type hint"
    assert TOOL_META[name]["module"]


def test_realm_routers_build():
    from agenthive.router import build_realm_root
    for realm in CAT.realms:
        if realm.agents:
            root = build_realm_root(realm.id)
            assert root.find_sub_agent(f"{realm.id}_concierge")


def test_compositions_reference_known_agents():
    from agenthive.catalog import composition_problems
    assert composition_problems(CAT) == []

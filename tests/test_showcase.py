"""The showcase edition (Google + clients): segments only, no internal framing, every agent builds, bilingual."""
import os
import re

import pytest

FORBIDDEN = re.compile(
    r"WurstaBot|Wursta(?:'s)? (?:internal|consultants?|delivery team|staff|engineers|employees)|\binternal use\b|"
    r"Hive agent demo|\brealm\b|wursta\.com", re.I)
CLIENT_FIELDS = ("name", "tagline", "description", "persona", "output", "model_reason")


@pytest.fixture(scope="module")
def showcase():
    from agenthive.catalog import load_catalog
    from agenthive.settings import get_settings
    from agenthive.tools._base import fixture

    old = os.environ.get("HIVE_EDITION")
    os.environ["HIVE_EDITION"] = "showcase"
    for f in (get_settings, load_catalog, fixture):
        f.cache_clear()
    yield load_catalog()
    if old is None:
        os.environ.pop("HIVE_EDITION")
    else:
        os.environ["HIVE_EDITION"] = old
    for f in (get_settings, load_catalog, fixture):
        f.cache_clear()


def test_segments_cover_every_agent(showcase):
    from agenthive.catalog import load_catalog, composition_problems

    internal = load_catalog("internal")
    assert {a.id for a in showcase.agents()} == {a.id for a in internal.agents()}
    assert {r.kind for r in showcase.realms} == {"user"}
    assert showcase.term == "segment"
    assert {a.status for a in showcase.agents()} == {"demo_ready"}
    assert composition_problems(showcase) == []
    for seg in showcase.realms:
        assert seg.kb_store in {r.id for r in internal.realms}, seg.id


def test_no_internal_framing(showcase):
    bad = []
    for a in showcase.agents():
        texts = [getattr(a, f) or "" for f in CLIENT_FIELDS] + a.use_cases + a.samples + a.kpis
        texts += [s.name for s in a.steps] + [s.role for s in a.steps]
        bad += [f"{a.id}: {m.group(0)!r}" for t in texts for m in [FORBIDDEN.search(t)] if m]
    for c in showcase.compositions:
        bad += [f"composition {c.id}: {m.group(0)!r}" for t in [c.name, c.summary, *c.flow, *c.blocks.values()]
                for m in [FORBIDDEN.search(t)] if m]
    assert not bad, bad


def test_every_agent_builds(showcase):
    from agenthive.agents.factory import build_agent
    from agenthive.router import build_realm_root

    for a in showcase.agents():
        assert build_agent(a).name == a.adk_name
    for seg in showcase.realms:
        assert build_realm_root(seg.id).find_sub_agent(f"{seg.id}_concierge")


def test_spanish_for_every_agent(showcase):
    from agenthive.catalog import load_i18n

    es = load_i18n("showcase", "es")
    assert set(es.get("segments", {})) == {r.id for r in showcase.realms}
    missing = [a.id for a in showcase.agents()
               if not all((es.get("agents", {}).get(a.id) or {}).get(k) for k in ("tagline", "description", "samples"))]
    assert not missing, f"no Spanish for {missing}"
    short = [a.id for a in showcase.agents() if len(es["agents"][a.id]["samples"]) < len(a.samples)]
    assert not short, f"fewer Spanish samples than English for {short}"

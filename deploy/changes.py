"""Decide what a push needs to redeploy: the web apps, which engines (both editions), the KB stores, the BigQuery seed.

    python deploy/changes.py <base-sha> <head-sha>                      # from git diff
    python deploy/changes.py --targets all|web,engines,showcase,platform,sc:services,kb,bq   # explicit

Prints `key=value` lines for $GITHUB_OUTPUT: web, realms (internal engines), showcase (showcase segment engines),
engines (matrix include list of {edition, realm}), kb (data stores = internal realm ids), bq, any.
An engine is redeployed when its agents' YAML changes, when a tool module one of its agents uses changes, or when shared
code (factory, router, models, grounding, fixtures, requirements) changes; a showcase segment also follows the internal
realms its agents come from and every change under the showcase edition's files. Unknown base (first push, force push)
means everything.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WEB_ONLY = {"agenthive/blocks.py"}            # used by the UI catalog, not by the engines
SHARED_TOOL_MODULES = {"common"}             # get_sample_document is added to agents automatically
NOT_DEPLOYED = ("tests/", "docs/", ".github/", "README.md", "deploy/out/")


def realms_and_modules() -> tuple[list[str], dict[str, set[str]]]:
    """Realm ids, and tool module file stem -> realms whose agents (or workflow steps) use one of its tools."""
    from agenthive.catalog import load_catalog
    from agenthive.tools import REGISTRY       # importing the package registers every tool module

    cat = load_catalog("internal")

    def tool_names(a, seen=()) -> set[str]:
        names = set(a.tools) | {t for s in a.steps for t in s.tools}
        for s in a.steps:                         # coordinator steps can wrap another catalog agent
            if s.agent_ref and s.agent_ref not in seen:
                names |= tool_names(cat.agent(s.agent_ref), (*seen, a.id))
        return names

    uses: dict[str, set[str]] = {}
    for a in cat.agents():
        for t in tool_names(a):
            if t in REGISTRY:
                uses.setdefault(REGISTRY[t].__module__.rsplit(".", 1)[-1], set()).add(a.realm)
    return [r.id for r in cat.realms if r.agents], uses


def showcase_map() -> tuple[list[str], dict[str, set[str]], dict[str, str], dict[str, set[str]]]:
    """Showcase segment ids; internal realm -> segments holding its agents; segment -> KB store; realm corpus ->
    stores that include it."""
    from agenthive.catalog import load_catalog

    internal = {a.id: a.realm for a in load_catalog("internal").agents()}
    sc = load_catalog("showcase")
    by_realm: dict[str, set[str]] = {}
    for a in sc.agents():
        by_realm.setdefault(internal[a.id], set()).add(a.realm)
    store = {seg.id: seg.kb_store or seg.id for seg in sc.realms}
    corpus_stores: dict[str, set[str]] = {}
    for seg in sc.realms:
        for src in seg.kb_sources:
            corpus_stores.setdefault(src, set()).add(store[seg.id])
    return [seg.id for seg in sc.realms if seg.agents], by_realm, store, corpus_stores


def _finish(web: bool, realms: set[str], showcase: set[str], kb: set[str], bq: bool) -> dict:
    engines = [{"edition": "internal", "realm": r} for r in sorted(realms)]
    engines += [{"edition": "showcase", "realm": s} for s in sorted(showcase)]
    return {"web": web, "realms": sorted(realms), "showcase": sorted(showcase), "engines": engines,
            "kb": sorted(kb), "bq": bq}


def plan(files: list[str]) -> dict:
    realm_ids, uses = realms_and_modules()
    segments, seg_by_realm, seg_store, corpus_stores = showcase_map()
    web, realms, showcase, kb, bq = False, set(), set(), set(), False
    for f in files:
        if f.startswith(NOT_DEPLOYED):
            continue
        if f.startswith("agenthive/grounding/editions/showcase/corpus/"):
            seg = f.split("/")[5]
            kb |= {seg_store[seg]} if seg in seg_store else set(realm_ids)
            continue
        if f.startswith(("agenthive/catalog/editions/showcase/", "agenthive/tools/fixtures/editions/showcase/")):
            web = True
            showcase |= set(segments)
            if f.startswith("agenthive/catalog/editions/showcase/hive.yaml"):
                kb |= set(realm_ids)                  # kb_store / kb_sources may have moved
            continue
        if f.startswith("web/") or f in {"Dockerfile", ".dockerignore", "deploy/deploy_web.sh"}:
            web = True
        if f.startswith("agenthive/grounding/corpus/"):
            realm = f.split("/")[3]
            kb |= ({realm} | corpus_stores.get(realm, set())) if realm in realm_ids else set(realm_ids)
            continue
        if f == "deploy/sync_kb.py":
            kb |= set(realm_ids)
        if f.startswith(("deploy/seed/", "agenthive/grounding/bq/")) or f == "deploy/seed_bigquery.py":
            bq = True
        if f == "deploy/deploy_engines.py":
            realms |= set(realm_ids)
        if not f.startswith("agenthive/"):
            continue
        web = True                                    # the UI catalog is generated from the package
        if f in WEB_ONLY:
            continue
        name = Path(f).name
        if f.startswith("agenthive/catalog/realms/"):
            realm = name.split(".")[0].split("__")[0]
            realms |= {realm} if realm in realm_ids else set(realm_ids)
        elif f.startswith("agenthive/tools/") and f.count("/") == 2 and not name.startswith("_") \
                and name.endswith(".py") and name != "__init__.py":
            mod = name[:-3]
            realms |= set(realm_ids) if mod in SHARED_TOOL_MODULES else uses.get(mod, set())
        else:
            realms |= set(realm_ids)                  # shared code, fixtures, hive.yaml, schemas
    for r in list(realms):
        showcase |= seg_by_realm.get(r, set())
    return _finish(web, realms, showcase, kb, bq)


def explicit(targets: str) -> dict:
    realm_ids, _ = realms_and_modules()
    segments = showcase_map()[0]
    want = {t.strip() for t in targets.split(",") if t.strip()}
    if "all" in want:
        return _finish(True, set(realm_ids), set(segments), set(realm_ids), True)
    sc_named = {t.removeprefix("sc:") for t in want if t.startswith("sc:")}
    bad = (want - set(realm_ids) - {"web", "engines", "showcase", "kb", "bq"} - {f"sc:{s}" for s in segments})
    if bad:
        raise SystemExit(f"unknown targets: {sorted(bad)}")
    realms = set(realm_ids) if "engines" in want else want & set(realm_ids)
    showcase = set(segments) if want & {"engines", "showcase"} else sc_named
    return _finish("web" in want, realms, showcase, set(realm_ids) if "kb" in want else set(), "bq" in want)


def changed(base: str, head: str) -> list[str] | None:
    if not base or set(base) == {"0"}:
        return None
    try:
        out = subprocess.run(["git", "diff", "--name-only", base, head], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        return None                                   # base not in history (force push)
    return [l for l in out.splitlines() if l]


def main(argv: list[str]) -> None:
    if argv[:1] == ["--targets"]:
        result = explicit(argv[1] if len(argv) > 1 else "all")
    else:
        files = changed(*argv[:2]) if len(argv) >= 2 else None
        result = explicit("all") if files is None else plan(files)
    result["any"] = bool(result["web"] or result["engines"] or result["kb"] or result["bq"])
    for k, v in result.items():
        print(f"{k}={json.dumps(v)}")


if __name__ == "__main__":
    main(sys.argv[1:])

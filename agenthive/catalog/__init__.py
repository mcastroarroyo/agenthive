"""The Hive catalog: single source of truth for realms, clusters, agents and compositions.

YAML files in this folder are loaded into typed models used by (1) the agent factory that builds ADK agents and
(2) the web UI that renders the hive. Every agent declares its four ADK building blocks:

  model      -> agenthive.models tier (lite | flash | argon)
  runtime    -> the realm's Agent Engine deployment (Vertex AI Agent Engine / Agent Runtime)
  tools      -> function tools from agenthive.tools (the FastMCP-style skill library + domain tools)
  grounding  -> kb (Vertex AI Search data store per realm), google_search, bigquery, fixtures
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

HERE = Path(__file__).resolve().parent

Status = Literal["demo_ready", "built", "in_build", "library"]
Tier = Literal["lite", "flash", "argon"]
Pattern = Literal["single", "sequential", "parallel", "coordinator", "loop"]
GROUNDING_KINDS = {"kb", "google_search", "bigquery", "fixtures"}


class Step(BaseModel):
    """A sub-agent inside a multi-agent pattern (sequential / parallel / coordinator / loop)."""
    id: str
    name: str
    model: Tier = "flash"
    role: str
    instruction: str
    tools: list[str] = Field(default_factory=list)
    grounding: list[str] = Field(default_factory=list)
    output_key: Optional[str] = None
    agent_ref: Optional[str] = None   # reuse another catalog agent as this step (coordinator / parallel)


class Agent(BaseModel):
    id: str
    code: str
    name: str
    realm: str = ""
    cluster: str
    industry: Optional[str] = None           # small label on the hex (e.g. FINANCIAL)
    short_name: Optional[str] = None         # shorter label for the hex when the name does not fit
    status: Status
    tagline: str
    description: str
    persona: str
    use_cases: list[str]
    model: Tier = "flash"
    model_reason: str
    pattern: Pattern = "single"
    tools: list[str] = Field(default_factory=list)
    grounding: list[str] = Field(default_factory=list)
    instruction: str
    output: str
    samples: list[str]
    sample_doc: Optional[str] = None          # fixtures/docs/<key>.md offered as a one-click input
    steps: list[Step] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    aka: Optional[str] = None                 # catalog alias (e.g. "Atlas 1")

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not v.replace("_", "").isalnum() or not v.islower() or not v[0].isalpha():
            raise ValueError(f"agent id must be lowercase snake_case starting with a letter: {v!r}")
        return v

    @field_validator("grounding")
    @classmethod
    def _grounding(cls, v: list[str]) -> list[str]:
        for g in v:
            if g.split(":")[0] not in GROUNDING_KINDS:
                raise ValueError(f"unknown grounding {g!r}; kinds: {sorted(GROUNDING_KINDS)}")
        return v

    @property
    def adk_name(self) -> str:
        return f"{self.id}_agent"


class Cluster(BaseModel):
    id: str
    name: str
    blurb: str = ""


class Realm(BaseModel):
    """A realm (internal edition) or customer segment (showcase edition): one Agent Engine and one KB each."""
    id: str
    name: str
    kind: Literal["user", "internal"]
    color: str
    blurb: str
    clusters: list[Cluster]
    agents: list[Agent] = Field(default_factory=list)
    kb_store: str = ""                                    # editions: internal realm whose data store hosts this KB
    kb_sources: list[str] = Field(default_factory=list)   # editions: base corpus folders composed into this KB
    kb_exclude: list[str] = Field(default_factory=list)   # editions: corpus file names left out


class Composition(BaseModel):
    id: str
    name: str
    kind: Literal["framework", "proposal", "workflow"]
    status: str
    summary: str
    agents: list[str]
    flow: list[str]           # human-readable steps; rendered as a pipeline in the UI
    blocks: dict[str, str]    # how the composition uses models / runtime / tools / grounding


class SecurityControl(BaseModel):
    name: str
    short: str                 # chip label on the realm band
    role: str                  # full description (expanded band)
    brief: str = ""            # one line for the agent panel


class SecurityLayer(BaseModel):
    """A security layer shown around one or more realms (display only — see `note`)."""
    id: str
    name: str
    realms: list[str]
    note: str
    summary: str
    controls: list[SecurityControl]


class Catalog(BaseModel):
    title: str
    subtitle: str
    statuses: dict[str, dict[str, str]]
    realms: list[Realm]
    compositions: list[Composition]
    skills: list[dict[str, str]]
    security_layers: list[SecurityLayer] = Field(default_factory=list)
    edition: str = "internal"
    term: str = "realm"                       # what the UI calls a realm: realm | segment
    layout: dict[str, list[str]] = Field(default_factory=dict)   # optional {"left": [...], "right": [...]}

    def agents(self) -> list[Agent]:
        return [a for r in self.realms for a in r.agents]

    def agent(self, agent_id: str) -> Agent:
        for a in self.agents():
            if a.id == agent_id:
                return a
        raise KeyError(agent_id)

    def realm(self, realm_id: str) -> Realm:
        for r in self.realms:
            if r.id == realm_id:
                return r
        raise KeyError(realm_id)


EDITIONS_DIR = HERE / "editions"


def _realm_agents(realm_id: str) -> list[dict]:
    """A realm may be split across files: realms/<realm>.yaml and realms/<realm>__<part>.yaml."""
    paths = sorted([*(HERE / "realms").glob(f"{realm_id}.yaml"), *(HERE / "realms").glob(f"{realm_id}__*.yaml")])
    return [a for p in paths for a in (yaml.safe_load(p.read_text()) or {}).get("agents", [])]


def _edition_overlay(base: dict, edition: str) -> dict:
    """Apply editions/<edition>/: hive.yaml replaces realms (segments), compositions, layers and texts;
    agents*.yaml move agents into segments and replace fields; `exclude` drops agents."""
    ed_dir = EDITIONS_DIR / edition
    ed = yaml.safe_load((ed_dir / "hive.yaml").read_text())
    overrides: dict[str, dict] = {}
    comp_over: dict[str, dict] = {}
    excluded: set[str] = set()
    for p in sorted(ed_dir.glob("agents*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for aid, o in (doc.get("agents") or {}).items():
            if aid in overrides:
                raise ValueError(f"{edition}: agent {aid} overridden in more than one file")
            overrides[aid] = o or {}
        comp_over.update(doc.get("compositions") or {})
        excluded |= set(doc.get("exclude") or [])
    segments = {s["id"]: {**s, "agents": []} for s in ed["realms"]}
    for r in base["realms"]:
        for a in _realm_agents(r["id"]):
            if a["id"] in excluded:
                continue
            o = overrides.pop(a["id"], {})
            a = {**a, **o}
            seg = o.get("realm", r["id"])
            if seg not in segments:
                raise ValueError(f"{edition}: agent {a['id']} (realm {r['id']}) needs a segment in agents*.yaml")
            if ed.get("force_status"):
                a["status"] = ed["force_status"]
            segments[seg]["agents"].append({**a, "realm": seg})
    if overrides:
        raise ValueError(f"{edition}: overrides for unknown agents {sorted(overrides)}")
    comps = [{**c, **comp_over.get(c["id"], {})} for c in ed.get("compositions", base["compositions"])]
    keep = {k: v for k, v in ed.items() if k not in ("realms", "compositions", "force_status")}
    return {**base, **keep, "realms": list(segments.values()), "compositions": comps, "edition": edition}


@lru_cache(maxsize=4)
def load_catalog(edition: str | None = None) -> Catalog:
    from ..settings import get_settings

    edition = edition or get_settings().edition
    base = yaml.safe_load((HERE / "hive.yaml").read_text())
    if edition == "internal":
        data = {**base, "realms": [{**r, "agents": [{**a, "realm": r["id"]} for a in _realm_agents(r["id"])]}
                                   for r in base["realms"]]}
    else:
        data = _edition_overlay(base, edition)
    cat = Catalog(**data)
    _validate(cat)
    return cat


def load_i18n(edition: str, lang: str) -> dict:
    """Merge editions/<edition>/i18n/<lang>*.yaml (UI translations of the catalog texts)."""
    out: dict = {}
    for p in sorted((EDITIONS_DIR / edition / "i18n").glob(f"{lang}*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        for k, v in doc.items():
            if isinstance(v, dict):
                section = out.setdefault(k, {})
                for item, val in v.items():      # merge per item: files may add fields to the same agent
                    if isinstance(val, dict) and isinstance(section.get(item), dict):
                        section[item] = {**section[item], **val}
                    else:
                        section[item] = val
            else:
                out[k] = v
    return out


def _validate(cat: Catalog) -> None:
    ids, codes = set(), set()
    realm_ids = {r.id for r in cat.realms}
    for layer in cat.security_layers:
        if set(layer.realms) - realm_ids:
            raise ValueError(f"security layer {layer.id}: unknown realms {sorted(set(layer.realms) - realm_ids)}")
    for r in cat.realms:
        cluster_ids = {c.id for c in r.clusters}
        for a in r.agents:
            if a.id in ids:
                raise ValueError(f"duplicate agent id {a.id}")
            if a.code.lower() in codes:
                raise ValueError(f"duplicate agent code {a.code}")
            ids.add(a.id)
            codes.add(a.code.lower())
            if a.cluster not in cluster_ids:
                raise ValueError(f"{a.id}: cluster {a.cluster!r} not in realm {r.id} clusters {sorted(cluster_ids)}")
            if a.pattern != "single" and not a.steps:
                raise ValueError(f"{a.id}: pattern {a.pattern} needs steps")
    for a in cat.agents():
        for ref in [*a.related, *[s.agent_ref for s in a.steps if s.agent_ref]]:
            if ref not in ids:
                raise ValueError(f"{a.id}: unknown related/agent_ref {ref!r}")


def composition_problems(cat: Catalog) -> list[str]:
    """Compositions span realms, so they are checked separately (tests) rather than at load time."""
    ids = {a.id for a in cat.agents()}
    return [f"composition {c.id}: unknown agent {ref!r}" for c in cat.compositions for ref in c.agents if ref not in ids]

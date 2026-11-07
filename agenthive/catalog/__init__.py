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
    id: str
    name: str
    kind: Literal["user", "internal"]
    color: str
    blurb: str
    clusters: list[Cluster]
    agents: list[Agent] = Field(default_factory=list)


class Composition(BaseModel):
    id: str
    name: str
    kind: Literal["framework", "proposal", "workflow"]
    status: str
    summary: str
    agents: list[str]
    flow: list[str]           # human-readable steps; rendered as a pipeline in the UI
    blocks: dict[str, str]    # how the composition uses models / runtime / tools / grounding


class Catalog(BaseModel):
    title: str
    subtitle: str
    statuses: dict[str, dict[str, str]]
    realms: list[Realm]
    compositions: list[Composition]
    skills: list[dict[str, str]]

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


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    base = yaml.safe_load((HERE / "hive.yaml").read_text())
    realms = []
    for r in base["realms"]:
        # a realm may be split across files: realms/<realm>.yaml and realms/<realm>__<part>.yaml
        paths = sorted([*(HERE / "realms").glob(f"{r['id']}.yaml"), *(HERE / "realms").glob(f"{r['id']}__*.yaml")])
        agents = [a for p in paths for a in (yaml.safe_load(p.read_text()) or {}).get("agents", [])]
        for a in agents:
            a["realm"] = r["id"]
        realms.append({**r, "agents": agents})
    cat = Catalog(**{**base, "realms": realms})
    _validate(cat)
    return cat


def _validate(cat: Catalog) -> None:
    ids, codes = set(), set()
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

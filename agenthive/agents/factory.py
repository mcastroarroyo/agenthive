"""Agent factory: turns a catalog entry into an ADK agent.

Patterns (ADK multi-agent primitives):
  single       LlmAgent with function tools + grounding
  sequential   SequentialAgent pipeline; each step writes `output_key` to session state for the next
  parallel     ParallelAgent fan-out of specialists, then a synthesis LlmAgent (the catalog agent itself)
  coordinator  LlmAgent that calls specialists as AgentTools (LLM-driven orchestration)
  loop         LoopAgent draft/critique cycle; the critic calls exit_loop when the bar is met
"""
from __future__ import annotations

import re
from typing import Callable

from typing import AsyncGenerator

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.events import Event, EventActions
from google.adk.tools.agent_tool import AgentTool

from .. import grounding as G
from .. import models
from ..catalog import Agent, Step, load_catalog
from ..tools import REGISTRY, TOOL_META
from ..tools._base import doc_text

COMMON_RULES = """
GUARDRAILS
- Every organisation, person and record in this demo is synthetic. Never claim to access real customer systems.
- Never invent figures: numbers must come from a tool, a query or a cited source; label estimates as estimates.
- Actions with side effects (send, create, schedule, move, file) are simulated by your tools — report them as
  "(simulated)".
- Lead with the answer, then the detail. Use short markdown sections and tables. Keep it under ~350 words unless the
  user asks for a full document. Reply in the user's language.
- If the request is outside your role, say which hive agent fits better (by its name) instead of improvising.
- Be economical with tools (cost matters): plan before calling, never repeat an identical call, check a draft once
  and re-check only what you changed, and keep to about 8 tool calls per answer unless the user asks for more.
- When you name Google AI models, use current names generically ("Gemini Flash", "Gemini Flash-Lite",
  "Gemini 4 Argon"); never cite retired versions such as Gemini 1.x.
""".strip()

_STATE_VAR = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _provider(text: str) -> Callable[[ReadonlyContext], str]:
    """Instruction provider: bypasses ADK's {var} templating (safe for JSON/code examples) and fills {{var}}
    placeholders from session state — used by pipeline steps to read earlier steps' outputs."""

    def provide(ctx: ReadonlyContext) -> str:
        state = ctx.state
        def value(m: re.Match) -> str:
            key = m.group(1)
            default = "" if key == MATERIAL_KEY else f"(no {key} yet)"
            return str(state.get(key, default))

        return _STATE_VAR.sub(value, text)

    return provide


MATERIAL_KEY = "client_material"
_DOC_KEY = re.compile(r"[a-z][a-z0-9_]{3,79}")


def referenced_docs(text: str) -> list[str]:
    return [k for k in dict.fromkeys(_DOC_KEY.findall(text or "")) if doc_text(k)]


class MaterialLoader(BaseAgent):
    """Deterministic first step of a workflow (no model call): loads any sample document the user references into
    session state, so every parallel/sequential step works from the same client material."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        text = " ".join(p.text or "" for p in (ctx.user_content.parts if ctx.user_content and ctx.user_content.parts
                                                  else []))
        keys = referenced_docs(text)
        if not keys:
            return
        material = "\n\n".join(f"=== Sample document '{k}' ===\n{doc_text(k)}" for k in keys)
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    actions=EventActions(state_delta={MATERIAL_KEY: material, "client_material_docs": keys}))


_MATERIAL_BLOCK = "\n\nREFERENCED CLIENT MATERIAL (verbatim; empty if none):\n{{" + MATERIAL_KEY + "}}"


def _grounding_text(specs: list[str], realm: str) -> str:
    lines = []
    for g in specs:
        kind, _, arg = g.partition(":")
        if kind == "kb":
            lines.append(f"- Knowledge base (Vertex AI Search, {realm} realm): search it before stating any policy, "
                         "process, pricing rule or product fact, and cite the document title.")
        elif kind == "google_search":
            lines.append("- Google Search: use it for current public facts (products, regulations, market news) and "
                         "cite sources as [title](url).")
        elif kind == "bigquery":
            tables = [t for t in arg.split(",") if t] or sorted(G.BQ_TABLES)
            lines.append("- " + G.bigquery_brief(tables))
        elif kind == "fixtures":
            lines.append("- Systems of record: business data comes only from your function tools (synthetic demo "
                         "systems). Call them instead of assuming values.")
    return "GROUNDING\n" + "\n".join(lines) if lines else ""


def _tools_text(tool_names: list[str]) -> str:
    if not tool_names:
        return ""
    return "TOOLS\n" + "\n".join(f"- {t}: {TOOL_META[t]['summary']}" for t in tool_names)


def _tool_objects(agent_id: str, tool_names: list[str], grounding: list[str], realm: str) -> list:
    tools: list = []
    for t in tool_names:
        if t not in REGISTRY:
            raise KeyError(f"{agent_id}: unknown tool {t!r}")
        tools.append(REGISTRY[t])
    for g in grounding:
        kind = g.partition(":")[0]
        if kind == "kb":
            tools.append(G.kb_tool(realm))
        elif kind == "google_search":
            tools.append(G.google_search_tool())
        elif kind == "bigquery":
            tools.append(G.bigquery_toolset(agent_id))
    return tools


def _instruction(a: Agent, realm_name: str, cluster_name: str) -> str:
    parts = [
        f"You are **{a.name}** ({a.code}) — {a.tagline}",
        f"Part of the Wursta Agent Hive · {realm_name} · {cluster_name}. You serve: {a.persona}.",
        f"ROLE AND OBJECTIVE\n{a.description.strip()}",
        f"HOW TO WORK\n{a.instruction.strip()}",
        _tools_text(a.tools),
        _grounding_text(a.grounding, a.realm),
        f"OUTPUT\n{a.output.strip()}",
        COMMON_RULES,
    ]
    return "\n\n".join(p for p in parts if p)


def _llm(name: str, tier: str, instruction: str, description: str, tools: list, output_key: str | None = None,
         isolated: bool = True) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=models.model(tier),
        generate_content_config=models.content_config(tier),
        instruction=_provider(instruction),
        description=description[:500],
        tools=tools,
        output_key=output_key,
        disallow_transfer_to_parent=isolated,
        disallow_transfer_to_peers=isolated,
    )


def _step_agent(parent: Agent, s: Step, realm: str) -> BaseAgent:
    if s.agent_ref:
        built = build_agent(load_catalog().agent(s.agent_ref), name_override=f"{parent.id}__{s.id}")
        if s.output_key and isinstance(built, LlmAgent):
            built.output_key = s.output_key
        return built
    instr = "\n\n".join(p for p in [
        f"You are **{s.name}**, one step of {parent.name} ({parent.code}). {s.role}",
        s.instruction.strip(),
        _tools_text(s.tools),
        _grounding_text(s.grounding, realm),
        COMMON_RULES,
    ] if p) + (_MATERIAL_BLOCK if parent.pattern in ("parallel", "sequential", "loop") else "")
    tools = _tool_objects(f"{parent.id}.{s.id}", s.tools, s.grounding, realm)
    if parent.pattern == "loop" and s is parent.steps[-1]:
        from google.adk.tools.exit_loop_tool import exit_loop
        tools.append(exit_loop)
        instr += "\n\nWhen the draft meets every criterion, call exit_loop. Otherwise give numbered, specific fixes."
    return _llm(f"{parent.id}__{s.id}", s.model, instr, s.role, tools, s.output_key)


def build_agent(a: Agent, name_override: str | None = None) -> BaseAgent:
    """Build the ADK agent for one catalog entry (a fresh instance each call — ADK agents have one parent)."""
    cat = load_catalog()
    realm = cat.realm(a.realm)
    cluster = next(c for c in realm.clusters if c.id == a.cluster)
    name = name_override or a.adk_name
    instruction = _instruction(a, realm.name, cluster.name)
    tool_names = list(a.tools)
    if "get_sample_document" not in tool_names and (a.sample_doc or any(referenced_docs(x) for x in a.samples)):
        tool_names.append("get_sample_document")   # samples reference documents: make sure the agent can open them
    tools = _tool_objects(a.id, tool_names, a.grounding, a.realm)

    if a.pattern == "single":
        return _llm(name, a.model, instruction, a.tagline, tools)

    steps = [_step_agent(a, s, a.realm) for s in a.steps]

    if a.pattern == "coordinator":
        specialist_tools = [AgentTool(agent=s) for s in steps]
        return _llm(name, a.model, instruction, a.tagline, tools + specialist_tools)

    loader = MaterialLoader(name=f"{name}__loader", description="Loads referenced sample documents into state")
    final_instruction = instruction + _MATERIAL_BLOCK

    if a.pattern == "sequential":
        final = _llm(f"{name}__final", a.model, final_instruction, a.tagline, tools)
        return SequentialAgent(name=name, description=a.tagline, sub_agents=[loader, *steps, final])

    if a.pattern == "parallel":
        fan_out = ParallelAgent(name=f"{name}__fanout", description="Specialists working in parallel",
                                sub_agents=steps)
        synth = _llm(f"{name}__synthesis", a.model, final_instruction, a.tagline, tools)
        return SequentialAgent(name=name, description=a.tagline, sub_agents=[loader, fan_out, synth])

    if a.pattern == "loop":
        loop = LoopAgent(name=f"{name}__loop", description="Draft and critique until approved",
                         sub_agents=steps, max_iterations=3)
        final = _llm(f"{name}__final", a.model, final_instruction, a.tagline, tools)
        return SequentialAgent(name=name, description=a.tagline, sub_agents=[loader, loop, final])

    raise ValueError(f"unknown pattern {a.pattern}")

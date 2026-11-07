"""HiveRouter — one Agent Engine deployment hosts a whole realm; each session talks to one agent.

Routing (deterministic, no LLM call):
  1. a message starting with "@<code>" (e.g. "@wms how exposed is ...") selects that agent and pins it to the session;
  2. otherwise session state "hive_agent" (set by the Hive UI when it creates the session);
  3. otherwise the realm concierge (Flash-Lite), which explains the realm's agents and how to pick one.
"""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from pydantic import Field

from . import models
from .agents.factory import build_agent
from .catalog import load_catalog

STATE_KEY = "hive_agent"


class HiveRouter(BaseAgent):
    """Routes each session to one catalog agent by @code prefix or session state."""

    codes: dict[str, str] = Field(default_factory=dict)        # lowercase code / id -> adk agent name
    concierge_name: str = ""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        target = None
        text = ""
        if ctx.user_content and ctx.user_content.parts:
            text = (ctx.user_content.parts[0].text or "").strip()
        if text.startswith("@"):
            code = text[1:].split()[0].lower().rstrip(":,") if len(text) > 1 else ""
            if code in self.codes:
                target = self.codes[code]
                yield Event(author=self.name, invocation_id=ctx.invocation_id,
                            actions=EventActions(state_delta={STATE_KEY: target}))
        if target is None:
            pinned = ctx.session.state.get(STATE_KEY)
            target = self.codes.get(str(pinned).lower(), pinned) if pinned else None
        agent = self.find_sub_agent(target) if target else None
        if agent is None:
            agent = self.find_sub_agent(self.concierge_name)
        async with _closing(agent.run_async(ctx)) as events:
            async for ev in events:
                yield ev


class _closing:
    def __init__(self, agen):
        self.agen = agen

    async def __aenter__(self):
        return self.agen

    async def __aexit__(self, *exc):
        await self.agen.aclose()


def directory_text(realm_id: str) -> str:
    realm = load_catalog().realm(realm_id)
    rows = [f"- @{a.code.lower()} **{a.name}** — {a.tagline}" for a in realm.agents]
    return "\n".join(rows)


def build_realm_root(realm_id: str) -> HiveRouter:
    cat = load_catalog()
    realm = cat.realm(realm_id)
    subs = [build_agent(a) for a in realm.agents]
    codes = {}
    for a in realm.agents:
        codes[a.code.lower()] = a.adk_name
        codes[a.id] = a.adk_name
        codes[a.adk_name] = a.adk_name
    concierge = LlmAgent(
        name=f"{realm_id}_concierge",
        model=models.model("lite"),
        generate_content_config=models.content_config("lite"),
        description=f"Concierge for the {realm.name} realm of the Wursta Agent Hive.",
        instruction=lambda _ctx: (
            f"You are the concierge of the **{realm.name}** realm in the Wursta Agent Hive. {realm.blurb}\n"
            "Help the user pick the right agent. Agents in this realm (start a message with the @code to talk to "
            f"one):\n{directory_text(realm_id)}\n\nRecommend at most 2 agents, say why in one line each, and show an "
            "example message starting with the @code. Do not answer domain questions yourself."),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
    return HiveRouter(name=f"hive_{realm_id}", description=f"Wursta Agent Hive · {realm.name}",
                      sub_agents=[concierge, *subs], codes=codes, concierge_name=concierge.name)

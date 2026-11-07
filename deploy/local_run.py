"""Run one hive agent locally (ADK InMemoryRunner) through the same HiveRouter used on Agent Engine.

    HIVE_PROJECT=<project> GCLOUD_ACCESS_TOKEN=$(gcloud auth print-access-token) \
        .venv/bin/python deploy/local_run.py <agent_id> "message" ["follow-up" ...]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _auth():
    tok = os.environ.get("GCLOUD_ACCESS_TOKEN")
    if tok:
        import google.auth
        from google.oauth2.credentials import Credentials

        cred = Credentials(token=tok)
        google.auth.default = lambda *a, **k: (cred, os.environ.get("HIVE_PROJECT"))


async def main(agent_id: str, messages: list[str]) -> None:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from agenthive.catalog import load_catalog
    from agenthive.router import build_realm_root

    a = load_catalog().agent(agent_id)
    root = build_realm_root(a.realm)
    runner = InMemoryRunner(agent=root, app_name="hive")
    s = await runner.session_service.create_session(app_name="hive", user_id="dev", state={"hive_agent": a.adk_name})
    tokens = 0
    for msg in messages:
        print(f"\n>>> {msg}\n")
        t0 = time.time()
        async for ev in runner.run_async(user_id="dev", session_id=s.id,
                                         new_message=types.Content(role="user", parts=[types.Part(text=msg)])):
            for p in (ev.content.parts if ev.content and ev.content.parts else []):
                if p.function_call:
                    print(f"  → [{ev.author}] {p.function_call.name}({json.dumps(p.function_call.args, ensure_ascii=False)[:220]})")
                elif p.function_response:
                    print(f"  ← [{ev.author}] {p.function_response.name}: {json.dumps(p.function_response.response, ensure_ascii=False, default=str)[:220]}")
                elif p.text and not p.thought:
                    print(f"[{ev.author}]\n{p.text}\n")
            if ev.usage_metadata and ev.usage_metadata.total_token_count:
                tokens += ev.usage_metadata.total_token_count
        print(f"--- {time.time() - t0:.1f}s, {tokens} tokens so far")


if __name__ == "__main__":
    _auth()
    asyncio.run(main(sys.argv[1], sys.argv[2:]))

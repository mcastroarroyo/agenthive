"""Live smoke test: run one sample prompt per agent through its realm router (local ADK runner, real Gemini).

    HIVE_PROJECT=<project> GCLOUD_ACCESS_TOKEN=$(gcloud auth print-access-token) \
        .venv/bin/python deploy/smoke_all.py [--realm smb] [--agents a,b] [--sample 0] [--concurrency 8]

Writes deploy/out/smoke-<timestamp>.json and prints a table: tool calls, tool errors, answer length, time, tokens.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _auth():
    tok = os.environ.get("GCLOUD_ACCESS_TOKEN")
    if tok:
        import google.auth
        from google.oauth2.credentials import Credentials

        cred = Credentials(token=tok)
        google.auth.default = lambda *a, **k: (cred, os.environ.get("HIVE_PROJECT"))


async def run_one(runner, agent, sample: str, timeout: int) -> dict:
    from google.genai import types

    s = await runner.session_service.create_session(app_name="hive", user_id="smoke",
                                                    state={"hive_agent": agent.adk_name})
    rec = {"agent": agent.id, "realm": agent.realm, "pattern": agent.pattern, "model": agent.model,
           "sample": sample[:120], "calls": [], "tool_errors": [], "text_chars": 0, "tokens": 0, "error": None}
    t0 = time.time()

    async def go():
        async for ev in runner.run_async(user_id="smoke", session_id=s.id,
                                         new_message=types.Content(role="user", parts=[types.Part(text=sample)])):
            if ev.error_message:
                rec["error"] = ev.error_message[:300]
            for p in (ev.content.parts if ev.content and ev.content.parts else []):
                if p.function_call:
                    rec["calls"].append(p.function_call.name)
                elif p.function_response:
                    r = p.function_response.response or {}
                    if isinstance(r, dict) and (r.get("status") == "error" or r.get("error")):
                        rec["tool_errors"].append(f"{p.function_response.name}: {str(r.get('error'))[:160]}")
                elif p.text and not p.thought:
                    rec["text_chars"] += len(p.text)
                    rec["last_text"] = p.text[-600:]
            if ev.usage_metadata and ev.usage_metadata.total_token_count:
                rec["tokens"] += ev.usage_metadata.total_token_count

    try:
        await asyncio.wait_for(go(), timeout)
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"[:400]
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


async def main(a):
    from google.adk.runners import InMemoryRunner

    from agenthive.catalog import load_catalog
    from agenthive.router import build_realm_root

    cat = load_catalog()
    agents = [x for x in cat.agents() if (not a.realm or x.realm == a.realm)
              and (not a.agents or x.id in a.agents.split(","))]
    runners = {r: InMemoryRunner(agent=build_realm_root(r), app_name="hive") for r in {x.realm for x in agents}}
    sem = asyncio.Semaphore(a.concurrency)

    async def guarded(x):
        async with sem:
            sample = x.samples[min(a.sample, len(x.samples) - 1)]
            rec = await run_one(runners[x.realm], x, sample, a.timeout)
            flag = "FAIL" if rec["error"] or not rec["text_chars"] else ("WARN" if rec["tool_errors"] else "ok")
            print(f"{flag:4} {x.realm:10} {x.id:24} {len(rec['calls']):2} calls {len(rec['tool_errors'])} err "
                  f"{rec['text_chars']:6} ch {rec['seconds']:6}s {rec['tokens']:7} tok {rec['error'] or ''}",
                  flush=True)
            return rec

    results = await asyncio.gather(*(guarded(x) for x in agents))
    out = ROOT / "deploy" / "out"
    out.mkdir(exist_ok=True)
    path = out / f"smoke-{int(time.time() * 1000)}.json"   # ms: parallel runs must not overwrite each other
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    bad = [r for r in results if r["error"] or not r["text_chars"]]
    print(f"\n{len(results)} agents · {len(bad)} failed · {sum(r['tokens'] for r in results):,} tokens · {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--realm", default="")
    ap.add_argument("--agents", default="")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=300)
    _auth()
    asyncio.run(main(ap.parse_args()))

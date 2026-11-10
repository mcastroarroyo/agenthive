"""Agent Hive web: interactive catalog + live demo proxy to the realm Agent Engines.

Routes
  GET  /                      the Hive UI (static)
  GET  /api/catalog           catalog with the four ADK building blocks per agent (prebuilt catalog.json)
  POST /api/session           create a managed session pinned to one agent      {agent_id}
  POST /api/run               stream one turn as Server-Sent Events             {agent_id, session_id, message, files?}
  POST /api/warm/{realm}      wake a realm's Agent Engine before a demo
  GET  /healthz-hive          liveness

Editions (HIVE_EDITION): internal (Cloud Run behind IAP, Wursta only) or showcase (HIVE_AUTH=google: any Google
account signs in; limits, activity log, feedback and /admin from web/showcase.py). Calls Agent Engine REST with the
service account's credentials. No project ids in code.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, AsyncIterator

import google.auth
import google.auth.transport.requests
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
EDITION = os.environ.get("HIVE_EDITION", "internal")
AUTH = os.environ.get("HIVE_AUTH", "iap")             # iap (internal) | google (showcase)
CATALOG: dict = json.loads((STATIC / ("catalog.json" if EDITION == "internal" else f"catalog-{EDITION}.json")).read_text())
AGENTS = {a["id"]: a for r in CATALOG["realms"] for a in r["agents"]}
REALM_NAMES = {r["id"]: r["name"] for r in CATALOG["realms"]}

PROJECT = os.environ.get("HIVE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
REGION = os.environ.get("HIVE_REGION", "us-central1")
ENGINE_REGION = os.environ.get("HIVE_ENGINE_REGION", "us-east4")
ENGINE_PREFIX = "Agent Hive · " if EDITION == "internal" else "Agent Hive Showcase · "
TOKENS_PREFIX = "hive_tok:"   # per-agent token counters the engine keeps in session state


def _api(location: str) -> str:
    return f"https://{location}-aiplatform.googleapis.com/v1"


def _api_for(engine: str) -> str:
    # projects/<p>/locations/<loc>/reasoningEngines/<id>
    return _api(engine.split("/locations/")[1].split("/")[0])
MAX_MESSAGE = 20_000
MAX_FILE_BYTES = 7 * 1024 * 1024
FILE_PREFIX = "hive_file:"            # agents put rendered deliverables in session state under this prefix
FILE_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/pdf", "text/csv", "text/markdown",
}
MAX_DELIVERABLE_B64 = 4 * 1024 * 1024
RATE = (40, 600)  # runs per user per 10 minutes

app = FastAPI(title="Wursta Agent Hive", docs_url=None, redoc_url=None)
if AUTH == "google":
    from web import showcase as SC

    SC.AGENTS = AGENTS
    app.include_router(SC.router)
else:
    SC = None
_creds = None
_engines: dict[str, str] = {}
_engines_at = 0.0
_runs: dict[str, deque] = defaultdict(deque)


_dev_token: tuple[str, float] = ("", 0.0)


def _token() -> str:
    global _creds, _dev_token
    if os.environ.get("HIVE_DEV_GCLOUD") == "1":  # local development only: user credentials via gcloud
        if time.time() - _dev_token[1] > 1800:
            import subprocess
            tok = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
            _dev_token = (tok, time.time())
        return _dev_token[0]
    if _creds is None:
        _creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _creds.valid:
        _creds.refresh(google.auth.transport.requests.Request())
    return _creds.token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


def _user(request: Request) -> str:
    if SC:
        return SC.current_user(request)["email"]
    email = request.headers.get("x-goog-authenticated-user-email", "")
    email = email.split(":", 1)[-1] if email else ""
    if not email and os.environ.get("HIVE_REQUIRE_IAP") == "1":
        raise HTTPException(401, "IAP identity required")
    return email or "local-dev"


def _user_id(email: str) -> str:
    # Sessions are keyed by a stable pseudonym, not the raw email.
    return "u-" + hashlib.sha256(email.encode()).hexdigest()[:16]


async def _engine_for(realm: str) -> str:
    global _engines, _engines_at
    stale = time.time() - _engines_at > 300
    missing = REALM_NAMES.get(realm, "") not in _engines and time.time() - _engines_at > 15
    if not _engines or stale or missing:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{_api(ENGINE_REGION)}/projects/{PROJECT}/locations/{ENGINE_REGION}/reasoningEngines",
                            params={"pageSize": 100}, headers=_headers())
            r.raise_for_status()
            found = {}
            for e in r.json().get("reasoningEngines", []):
                dn = e.get("displayName", "")
                if dn.startswith(ENGINE_PREFIX):
                    found[dn.removeprefix(ENGINE_PREFIX)] = e["name"]
            _engines, _engines_at = found, time.time()
    name = _engines.get(REALM_NAMES.get(realm, ""))
    if not name:
        raise HTTPException(503, f"No Agent Engine deployed for realm {realm!r} yet")
    return name


async def _query(engine: str, method: str, payload: dict) -> Any:
    async with httpx.AsyncClient(timeout=httpx.Timeout(240, connect=20)) as c:
        r = await c.post(f"{_api_for(engine)}/{engine}:query", headers=_headers(),
                         json={"class_method": method, "input": payload})
        if r.status_code >= 400:
            raise HTTPException(502, f"Agent Engine error {r.status_code}: {r.text[:300]}")
        return r.json().get("output")


class SessionIn(BaseModel):
    agent_id: str


class FileIn(BaseModel):
    name: str = Field(max_length=200)
    mime_type: str = Field(max_length=100)
    data: str  # base64


class RunIn(BaseModel):
    agent_id: str
    session_id: str = Field(max_length=200)
    message: str = Field(max_length=MAX_MESSAGE)
    files: list[FileIn] = Field(default_factory=list, max_length=3)
    lang: str = Field(default="en", max_length=5)
    sample: bool = False                 # the message is one of the agent's sample prompts


@app.get("/healthz-hive")
def health():
    return {"ok": True, "agents": len(AGENTS)}


@app.get("/api/catalog")
def catalog(request: Request):
    _user(request)
    return JSONResponse(CATALOG, headers={"Cache-Control": "no-cache"})


DOCS = HERE.parent / "agenthive" / "tools" / "fixtures" / "docs"
EDITION_DOCS = HERE.parent / "agenthive" / "tools" / "fixtures" / "editions" / EDITION / "docs"


@app.get("/api/doc/{key}")
def sample_doc(key: str, request: Request):
    _user(request)
    if not re.fullmatch(r"[a-z0-9_]{1,80}", key):
        raise HTTPException(400, "bad key")
    p = EDITION_DOCS / f"{key}.md" if (EDITION_DOCS / f"{key}.md").is_file() else DOCS / f"{key}.md"
    if not p.is_file():
        raise HTTPException(404, "no such sample document")
    text = p.read_text()
    title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.strip()), key)
    return {"key": key, "title": title, "text": text}


@app.post("/api/warm/{realm}")
async def warm(realm: str, request: Request):
    _user(request)
    t0 = time.time()
    engine = await _engine_for(realm)
    await _query(engine, "async_list_sessions", {"user_id": "warmup"})
    return {"realm": realm, "engine": engine.rsplit("/", 1)[-1], "seconds": round(time.time() - t0, 1)}


@app.post("/api/session")
async def session(body: SessionIn, request: Request):
    a = AGENTS.get(body.agent_id)
    if not a:
        raise HTTPException(404, "unknown agent")
    email = _user(request)
    uid = _user_id(email)
    state: dict[str, Any] = {"hive_agent": a["adk_name"]}
    if SC:
        lim = await SC.limits()
        state["hive_token_limit"] = lim["session_tokens"]   # enforced by the engine (agents/factory.py)
    engine = await _engine_for(a["realm"])
    t0 = time.time()
    out = await _query(engine, "async_create_session", {"user_id": uid, "state": state})
    if SC:
        await SC.session_started(SC.current_user(request), out["id"], a)
    return {"session_id": out["id"], "engine": engine.rsplit("/", 1)[-1], "region": ENGINE_REGION,
            "seconds": round(time.time() - t0, 1), "token_limit": state.get("hive_token_limit")}


def _limit(email: str) -> None:
    q, now = _runs[email], time.time()
    while q and now - q[0] > RATE[1]:
        q.popleft()
    if len(q) >= RATE[0]:
        raise HTTPException(429, "Demo rate limit reached — try again in a few minutes")
    q.append(now)


def _simplify(ev: dict) -> list[dict]:
    """Agent Engine/ADK event -> small UI events."""
    out: list[dict] = []
    author = ev.get("author", "")
    if ev.get("error_code") or ev.get("error_message"):
        out.append({"type": "error", "author": author, "message": ev.get("error_message") or ev.get("error_code")})
    content = ev.get("content") or {}
    for p in content.get("parts") or []:
        if p.get("function_call"):
            fc = p["function_call"]
            out.append({"type": "call", "author": author, "name": fc.get("name"), "args": fc.get("args")})
        elif p.get("function_response"):
            fr = p["function_response"]
            resp = json.dumps(fr.get("response"), ensure_ascii=False, default=str)
            out.append({"type": "result", "author": author, "name": fr.get("name"),
                        "response": resp[:6000], "truncated": len(resp) > 6000})
        elif p.get("code_execution_result"):
            out.append({"type": "result", "author": author, "name": "code_execution",
                        "response": json.dumps(p["code_execution_result"])[:4000]})
        elif p.get("text"):
            if p.get("thought"):
                out.append({"type": "thought", "author": author, "text": p["text"][:4000]})
            elif not ev.get("partial"):
                out.append({"type": "text", "author": author, "text": p["text"]})
    gm = ev.get("grounding_metadata") or {}
    if gm:
        sources = []
        for ch in gm.get("grounding_chunks") or []:
            src = ch.get("web") or ch.get("retrieved_context") or {}
            if src:
                sources.append({"title": src.get("title") or src.get("uri", ""), "uri": src.get("uri", "")})
        out.append({"type": "grounding", "author": author, "sources": sources[:10],
                    "queries": (gm.get("web_search_queries") or [])[:5],
                    "kind": "kb" if any(c.get("retrieved_context") for c in gm.get("grounding_chunks") or [])
                    else "google_search"})
    um = ev.get("usage_metadata") or {}
    if um.get("total_token_count"):
        out.append({"type": "usage", "author": author, "prompt": um.get("prompt_token_count", 0),
                    "output": um.get("candidates_token_count", 0), "thoughts": um.get("thoughts_token_count", 0),
                    "model": ev.get("model_version") or ""})
    sd = (ev.get("actions") or {}).get("state_delta") or {}
    for k, v in sd.items():
        if (k.startswith(FILE_PREFIX) and isinstance(v, dict) and v.get("mime") in FILE_MIMES
                and isinstance(v.get("b64"), str) and 0 < len(v["b64"]) <= MAX_DELIVERABLE_B64):
            out.append({"type": "file", "author": author, "id": k[len(FILE_PREFIX):][:64],
                        "name": re.sub(r"[^\w .()-]", "_", str(v.get("name") or "deliverable"))[:120],
                        "mime": v["mime"], "size": int(v.get("size") or 0), "b64": v["b64"]})
    tok = {k: v for k, v in sd.items() if k.startswith(TOKENS_PREFIX) and isinstance(v, (int, float))}
    if tok:
        out.append({"type": "_tok", "values": tok})        # consumed by /api/run, not sent to the browser
    keys = sorted(k for k in sd if not k.startswith((FILE_PREFIX, TOKENS_PREFIX)))
    if keys:
        out.append({"type": "state", "author": author, "keys": keys[:10]})
    return out


async def _stream_events(engine: str, payload: dict) -> AsyncIterator[dict]:
    decoder = json.JSONDecoder()
    async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=20)) as c:
        async with c.stream("POST", f"{_api_for(engine)}/{engine}:streamQuery", headers=_headers(),
                            json={"class_method": "async_stream_query", "input": payload}) as r:
            if r.status_code >= 400:
                body = (await r.aread()).decode(errors="replace")
                yield {"type": "error", "message": f"Agent Engine error {r.status_code}: {body[:400]}"}
                return
            buf = ""
            async for chunk in r.aiter_text():
                buf += chunk
                while True:
                    s = buf.lstrip()
                    if s.startswith("data:"):
                        s = s[5:].lstrip()
                    if not s:
                        buf = ""
                        break
                    try:
                        obj, end = decoder.raw_decode(s)
                    except json.JSONDecodeError:
                        buf = s
                        break
                    buf = s[end:]
                    if isinstance(obj, dict):
                        for ui in _simplify(obj):
                            yield ui


@app.post("/api/run")
async def run(body: RunIn, request: Request):
    a = AGENTS.get(body.agent_id)
    if not a:
        raise HTTPException(404, "unknown agent")
    email = _user(request)
    _limit(email)
    user = SC.current_user(request) if SC else None
    lim = await SC.check_quota(user) if SC else {}
    engine = await _engine_for(a["realm"])
    message: Any = body.message
    if body.files:
        parts: list[dict] = [{"text": body.message}]
        for f in body.files:
            raw = base64.b64decode(f.data, validate=True)
            if len(raw) > MAX_FILE_BYTES:
                raise HTTPException(413, f"{f.name} is larger than 7 MB")
            if not (f.mime_type.startswith("image/") or f.mime_type in ("application/pdf", "text/plain")):
                raise HTTPException(415, f"{f.mime_type} not supported (images, PDF, text)")
            parts.append({"inline_data": {"mime_type": f.mime_type, "data": f.data}})
        message = {"role": "user", "parts": parts}
    payload = {"user_id": _user_id(email), "session_id": body.session_id, "message": message}
    if lim:
        payload["run_config"] = {"max_llm_calls": lim["max_llm_calls"]}
    tok_before = await SC.session_tok(body.session_id) if SC else {}

    async def sse():
        t0 = time.time()
        first = None
        tok = dict(tok_before)      # per-agent cumulative counters for this session
        usage = 0                   # fallback: usage events of the top-level agents
        status, error = "ok", ""
        try:
            async for ev in _stream_events(engine, payload):
                if ev["type"] == "_tok":
                    tok.update(ev["values"])
                    continue
                if ev["type"] == "usage":
                    usage += ev["prompt"] + ev["output"] + ev.get("thoughts", 0)
                if ev["type"] == "error":
                    status, error = "error", str(ev.get("message", ""))
                if first is None:
                    first = round(time.time() - t0, 1)
                    yield f"data: {json.dumps({'type': 'runtime', 'first_event_s': first})}\n\n"
                yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            status, error = "error", f"{type(e).__name__}: {e}"
            yield f"data: {json.dumps({'type': 'error', 'message': error[:300]})}\n\n"
        seconds = round(time.time() - t0, 1)
        total = sum(tok.values())
        run_tokens = max(total - sum(tok_before.values()), 0) or usage
        if SC:
            try:
                await SC.record_run(user, a, body.session_id, tokens=run_tokens, session_tok=tok, seconds=seconds,
                                    status=status, lang=body.lang, sample=body.sample, error=error)
            except Exception as e:  # noqa: BLE001 — logging must never break the demo
                print(f"usage logging failed: {e}", flush=True)
            yield f"data: {json.dumps({'type': 'budget', 'session_tokens': total or usage, 'limit': lim.get('session_tokens')})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'seconds': seconds, 'tokens': run_tokens})}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path in ("/", "/index.html") or request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/admin")
def admin_page(request: Request):
    if not SC:
        raise HTTPException(404, "not found")
    try:
        SC.require_admin(request)
    except HTTPException:
        from fastapi.responses import RedirectResponse

        return RedirectResponse("/")
    return FileResponse(STATIC / "admin.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")

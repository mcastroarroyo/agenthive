"""Showcase edition of the web app: Google sign-in for any Google account, usage limits, activity log, feedback
and the admin API. Imported by web/main.py only when HIVE_AUTH=google.

  Sign-in      Google Identity Services ID token -> verified server-side -> signed, HttpOnly session cookie
  Limits       per demo session (enforced inside the engine via session state), per user per day and app-wide per
               day (enforced here before each run); editable from the admin area; kill switch
  Activity     Firestore database HIVE_FIRESTORE_DB: users, logins, runs, feedback, daily usage
  Admin        /admin + /api/admin/* for the emails in HIVE_ADMINS

Nothing project-specific is hard-coded; the session key comes from Secret Manager through the environment.
"""
from __future__ import annotations

import asyncio
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

CLIENT_ID = os.environ.get("HIVE_GOOGLE_CLIENT_ID", "")
SECRET = os.environ.get("HIVE_SESSION_SECRET", "").encode()
ADMINS = {e.strip().lower() for e in os.environ.get("HIVE_ADMINS", "").split(",") if e.strip()}
DB = os.environ.get("HIVE_FIRESTORE_DB", "agenthive")
PROJECT = os.environ.get("HIVE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
COOKIE = "hive_s"
SESSION_HOURS = 12
DEFAULT_LIMITS = {
    "enabled": True,                     # kill switch: false stops every new run
    "session_tokens": 300_000,           # one demo conversation (enforced by the engine)
    "user_daily_tokens": 1_500_000,
    "user_daily_runs": 60,
    "app_daily_tokens": 30_000_000,      # everyone together, per UTC day
    "max_llm_calls": 50,                 # per turn (ADK RunConfig)
}

router = APIRouter()
AGENTS: dict[str, dict] = {}        # set by web.main
_db = None
_limits: tuple[dict, float] = ({}, 0.0)


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def uid_for(email: str) -> str:
    return "u-" + hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def db():
    global _db
    if _db is None:
        from google.cloud import firestore

        creds = None
        if os.environ.get("HIVE_DEV_GCLOUD") == "1":   # local development only: user credentials via gcloud
            import subprocess

            from google.oauth2.credentials import Credentials

            creds = Credentials(subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip())
        _db = firestore.AsyncClient(project=PROJECT or None, database=DB, credentials=creds)
    return _db


def _inc(n: int | float):
    from google.cloud import firestore

    return firestore.Increment(n)


# ------------------------------------------------------------------------------------------------ session cookie
def _sign(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    mac = base64.urlsafe_b64encode(hmac.new(SECRET, body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{body}.{mac}"


def _unsign(token: str) -> dict | None:
    try:
        body, mac = token.split(".", 1)
        good = base64.urlsafe_b64encode(hmac.new(SECRET, body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(mac, good):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return data if data.get("exp", 0) > time.time() else None
    except Exception:  # noqa: BLE001 — any malformed cookie is simply "not signed in"
        return None


def current_user(request: Request) -> dict:
    user = _unsign(request.cookies.get(COOKIE, "")) if SECRET else None
    if not user:
        raise HTTPException(401, "sign-in required")
    user["admin"] = user["email"] in ADMINS
    return user


def require_admin(request: Request) -> dict:
    user = current_user(request)
    if not user["admin"]:
        raise HTTPException(403, "admins only")
    return user


# ------------------------------------------------------------------------------------------------ limits
async def limits() -> dict:
    global _limits
    if time.time() - _limits[1] > 30:
        doc = await db().collection("config").document("limits").get()
        _limits = ({**DEFAULT_LIMITS, **(doc.to_dict() or {})}, time.time())
    return _limits[0]


async def check_quota(user: dict) -> dict:
    """Raise 429 when the app or this user is over today's limits; return the limits in force."""
    lim = await limits()
    if not lim["enabled"]:
        raise HTTPException(429, "The demos are paused right now. / Las demos están en pausa en este momento.")
    day = today()
    app_day = (await db().collection("usage_daily").document(day).get()).to_dict() or {}
    if app_day.get("tokens", 0) >= lim["app_daily_tokens"]:
        raise HTTPException(429, "Today's demo capacity is used up — please come back tomorrow. / "
                                 "La capacidad de demos de hoy se agotó; vuelve mañana.")
    mine = (await db().collection("users").document(user["uid"]).collection("days").document(day).get()).to_dict() or {}
    if mine.get("tokens", 0) >= lim["user_daily_tokens"] or mine.get("runs", 0) >= lim["user_daily_runs"]:
        raise HTTPException(429, "You reached today's demo limit — please come back tomorrow. / "
                                 "Alcanzaste el límite de demos de hoy; vuelve mañana.")
    return lim


async def session_started(user: dict, session_id: str, agent: dict) -> None:
    await db().collection("sessions").document(session_id).set({
        "uid": user["uid"], "email": user["email"], "agent_id": agent["id"], "segment": agent["realm"],
        "created": dt.datetime.now(dt.timezone.utc), "tokens": 0, "runs": 0}, merge=True)


async def session_tok(session_id: str) -> dict[str, int]:
    """Per-agent cumulative token counters last seen for this session (keys hive_tok:<agent>)."""
    doc = await db().collection("sessions").document(session_id).get()
    return {k: int(v) for k, v in ((doc.to_dict() or {}).get("tok") or {}).items()}


async def record_run(user: dict, agent: dict, session_id: str, *, tokens: int, session_tok: dict, seconds: float,
                     status: str, lang: str, sample: bool, error: str = "") -> None:
    now, day = dt.datetime.now(dt.timezone.utc), today()
    c = db()
    batch = c.batch()
    batch.set(c.collection("runs").document(), {
        "ts": now, "uid": user["uid"], "email": user["email"], "agent_id": agent["id"], "agent": agent["name"],
        "segment": agent["realm"], "session_id": session_id, "tokens": tokens, "seconds": seconds,
        "status": status, "lang": lang, "sample": sample, "error": error[:300]})
    batch.set(c.collection("sessions").document(session_id),
              {"tok": session_tok, "tokens": sum(session_tok.values()), "runs": _inc(1), "last": now}, merge=True)
    batch.set(c.collection("usage_daily").document(day), {"tokens": _inc(tokens), "runs": _inc(1)}, merge=True)
    batch.set(c.collection("users").document(user["uid"]),
              {"tokens": _inc(tokens), "runs": _inc(1), "last_seen": now,
               "agents": {agent["id"]: _inc(1)}}, merge=True)
    batch.set(c.collection("users").document(user["uid"]).collection("days").document(day),
              {"tokens": _inc(tokens), "runs": _inc(1)}, merge=True)
    await batch.commit()


# ------------------------------------------------------------------------------------------------ auth routes
class GoogleIn(BaseModel):
    credential: str = Field(max_length=4096)
    lang: str = Field(default="en", max_length=5)


@router.get("/api/auth/config")
def auth_config():
    return {"mode": "google", "client_id": CLIENT_ID}


@router.post("/api/auth/google")
async def auth_google(body: GoogleIn, request: Request, response: Response):
    if not (CLIENT_ID and SECRET):
        raise HTTPException(503, "sign-in is not configured")
    from google.auth.transport import requests as greq
    from google.oauth2 import id_token

    try:
        info = id_token.verify_oauth2_token(body.credential, greq.Request(), CLIENT_ID)
    except ValueError:
        raise HTTPException(401, "invalid Google credential") from None
    if not info.get("email_verified"):
        raise HTTPException(401, "this Google account's email is not verified")
    email = info["email"].lower()
    user = {"uid": uid_for(email), "email": email, "name": info.get("name", "")[:120],
            "picture": info.get("picture", "")[:500], "exp": int(time.time()) + SESSION_HOURS * 3600}
    response.set_cookie(COOKIE, _sign(user), max_age=SESSION_HOURS * 3600, httponly=True, secure=True,
                        samesite="lax", path="/")
    now = dt.datetime.now(dt.timezone.utc)
    ref = db().collection("users").document(user["uid"])
    first = not (await ref.get()).exists
    await ref.set({"email": email, "name": user["name"], "picture": user["picture"],
                   "domain": email.split("@")[1], "hd": info.get("hd", ""), "last_seen": now, "last_login": now,
                   "logins": _inc(1), "lang": body.lang[:5], **({"first_seen": now} if first else {})}, merge=True)
    await db().collection("logins").add({"ts": now, "uid": user["uid"], "email": email,
                                          "ua": request.headers.get("user-agent", "")[:200], "lang": body.lang[:5]})
    return {"email": email, "name": user["name"], "picture": user["picture"], "admin": email in ADMINS}


if os.environ.get("HIVE_DEV_GCLOUD") == "1" and os.environ.get("HIVE_DEV_LOGIN"):
    @router.post("/api/auth/dev")
    async def auth_dev(response: Response):
        """Local development only (never set on Cloud Run): sign in as HIVE_DEV_LOGIN without Google."""
        email = os.environ["HIVE_DEV_LOGIN"].lower()
        user = {"uid": uid_for(email), "email": email, "name": "Local developer", "picture": "",
                "exp": int(time.time()) + SESSION_HOURS * 3600}
        response.set_cookie(COOKIE, _sign(user), max_age=SESSION_HOURS * 3600, httponly=True, samesite="lax", path="/")
        return {"email": email}


@router.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/api/me")
async def me(request: Request):
    user = current_user(request)
    lim = await limits()
    mine = (await db().collection("users").document(user["uid"]).collection("days").document(today()).get()).to_dict() or {}
    return {"email": user["email"], "name": user["name"], "picture": user["picture"], "admin": user["admin"],
            "today": {"tokens": mine.get("tokens", 0), "runs": mine.get("runs", 0)},
            "limits": {k: lim[k] for k in ("session_tokens", "user_daily_tokens", "user_daily_runs")}}


class FeedbackIn(BaseModel):
    agent_id: str = Field(max_length=80)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)
    session_id: str = Field(default="", max_length=200)
    lang: str = Field(default="en", max_length=5)


@router.post("/api/feedback")
async def feedback(body: FeedbackIn, request: Request):
    user = current_user(request)
    a = AGENTS.get(body.agent_id)
    if not a:
        raise HTTPException(404, "unknown agent")
    await db().collection("feedback").add({
        "ts": dt.datetime.now(dt.timezone.utc), "uid": user["uid"], "email": user["email"], "agent_id": a["id"],
        "agent": a["name"], "segment": a["realm"], "rating": body.rating, "comment": body.comment.strip(),
        "session_id": body.session_id, "lang": body.lang})
    return {"ok": True}


# ------------------------------------------------------------------------------------------------ admin API
def _iso(v: Any) -> Any:
    return v.isoformat() if hasattr(v, "isoformat") else v


async def _docs(query, limit: int) -> list[dict]:
    return [{"id": d.id, **{k: _iso(v) for k, v in (d.to_dict() or {}).items()}} async for d in query.limit(limit).stream()]


@router.get("/api/admin/summary")
async def admin_summary(request: Request):
    from google.cloud import firestore

    require_admin(request)
    c = db()
    keys = [(dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=i)).isoformat() for i in range(14)]
    async def usage_days() -> dict:
        return {snap.id: snap.to_dict() or {}
                async for snap in c.get_all([c.collection("usage_daily").document(d) for d in keys])}

    by_day, users, fb = await asyncio.gather(
        usage_days(),
        _docs(c.collection("users").order_by("last_seen", direction=firestore.Query.DESCENDING), 500),
        _docs(c.collection("feedback").order_by("ts", direction=firestore.Query.DESCENDING), 1000))
    days = [{"day": d, "tokens": by_day.get(d, {}).get("tokens", 0), "runs": by_day.get(d, {}).get("runs", 0)} for d in keys]
    by_agent: dict[str, dict] = {}
    for f in fb:
        s = by_agent.setdefault(f["agent_id"], {"agent": f.get("agent", f["agent_id"]), "n": 0, "sum": 0})
        s["n"] += 1
        s["sum"] += f.get("rating", 0)
    ratings = sorted(({"agent_id": k, "agent": v["agent"], "count": v["n"], "avg": round(v["sum"] / v["n"], 2)}
                      for k, v in by_agent.items()), key=lambda r: (-r["count"], r["agent"]))
    return {"limits": await limits(), "days": days, "users": len(users),
            "users_today": sum(1 for u in users if str(u.get("last_seen", "")).startswith(today())),
            "feedback": len(fb), "avg_rating": round(sum(f.get("rating", 0) for f in fb) / len(fb), 2) if fb else None,
            "ratings_by_agent": ratings}


@router.get("/api/admin/users")
async def admin_users(request: Request):
    from google.cloud import firestore

    require_admin(request)
    users = await _docs(db().collection("users").order_by("last_seen", direction=firestore.Query.DESCENDING), 500)
    for u in users:
        u.pop("picture", None)
        agents = u.pop("agents", {}) or {}
        u["agents_tried"] = len(agents)
        u["top_agents"] = sorted(agents.items(), key=lambda kv: -kv[1])[:5]
    return {"users": users}


@router.get("/api/admin/runs")
async def admin_runs(request: Request, email: str = "", limit: int = 300):
    from google.cloud import firestore

    require_admin(request)
    q = db().collection("runs")
    if email:
        q = q.where("email", "==", email.lower())
    q = q.order_by("ts", direction=firestore.Query.DESCENDING)
    return {"runs": await _docs(q, max(1, min(limit, 1000)))}


@router.get("/api/admin/feedback")
async def admin_feedback(request: Request):
    from google.cloud import firestore

    require_admin(request)
    q = db().collection("feedback").order_by("ts", direction=firestore.Query.DESCENDING)
    return {"feedback": await _docs(q, 500)}


@router.get("/api/admin/logins")
async def admin_logins(request: Request):
    from google.cloud import firestore

    require_admin(request)
    q = db().collection("logins").order_by("ts", direction=firestore.Query.DESCENDING)
    return {"logins": await _docs(q, 500)}


class LimitsIn(BaseModel):
    enabled: bool
    session_tokens: int = Field(ge=10_000, le=5_000_000)
    user_daily_tokens: int = Field(ge=10_000, le=100_000_000)
    user_daily_runs: int = Field(ge=1, le=10_000)
    app_daily_tokens: int = Field(ge=100_000, le=2_000_000_000)
    max_llm_calls: int = Field(ge=5, le=500)


@router.put("/api/admin/limits")
async def admin_limits(body: LimitsIn, request: Request):
    global _limits
    admin = require_admin(request)
    data = {**body.model_dump(), "updated_by": admin["email"], "updated": dt.datetime.now(dt.timezone.utc)}
    await db().collection("config").document("limits").set(data)
    _limits = ({}, 0.0)
    return {"ok": True, "limits": await limits()}

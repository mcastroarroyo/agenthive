"""Showcase edition of the web app: Google sign-in for any Google account, usage limits, activity log, feedback
and the admin API. Imported by web/main.py only when HIVE_AUTH=google.

  Sign-in      Google Identity Services ID token -> verified server-side -> signed, HttpOnly session cookie
  Limits       per demo session (enforced inside the engine via session state), per user per day and app-wide per
               day (enforced here before each run); editable from the admin area; kill switch
  Activity     Firestore database HIVE_FIRESTORE_DB: users, logins, runs, feedback, daily usage
  Admin        /admin + /api/admin/* for the emails in HIVE_ADMINS
  Sessions     every sign-in is a revocable session (Firestore web_sessions); admins can close it or block the user
               from /admin or from the one-click links in the sign-in alert email (HIVE_MAIL_RELAY)

Nothing project-specific is hard-coded; the session key comes from Secret Manager through the environment.
"""
from __future__ import annotations

import asyncio
import base64
import secrets
import datetime as dt
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

CLIENT_ID = os.environ.get("HIVE_GOOGLE_CLIENT_ID", "")
SECRET = os.environ.get("HIVE_SESSION_SECRET", "").encode()
ADMINS = {e.strip().lower() for e in os.environ.get("HIVE_ADMINS", "").split(",") if e.strip()}
DB = os.environ.get("HIVE_FIRESTORE_DB", "agenthive")
PROJECT = os.environ.get("HIVE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
NOTIFY = [e.strip().lower() for e in (os.environ.get("HIVE_NOTIFY_EMAILS") or os.environ.get("HIVE_ADMINS", "")).split(",")
          if e.strip()]
MAIL_RELAY = os.environ.get("HIVE_MAIL_RELAY", "")      # Apps Script web app that sends mail (deploy/mail_relay.gs)
PUBLIC_URL = os.environ.get("HIVE_PUBLIC_URL", "").rstrip("/")
NOTIFY_TZ = dt.timezone(dt.timedelta(hours=float(os.environ.get("HIVE_NOTIFY_UTC_OFFSET", "-6"))))
COOKIE = "hive_s"
SESSION_HOURS = 12
ACTION_DAYS = 7                     # email action links stay valid this long
SESSION_CHECK_S = 15                # a closed session stops working within this many seconds
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
def _key(purpose: str) -> bytes:
    return hmac.new(SECRET, purpose.encode(), hashlib.sha256).digest()


def _sign(payload: dict, purpose: str = "session") -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    mac = base64.urlsafe_b64encode(hmac.new(_key(purpose), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{body}.{mac}"


def _unsign(token: str, purpose: str = "session") -> dict | None:
    try:
        body, mac = token.split(".", 1)
        good = base64.urlsafe_b64encode(hmac.new(_key(purpose), body.encode(), hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(mac, good.rstrip("=")):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return data if data.get("exp", 0) > time.time() else None
    except Exception:  # noqa: BLE001 — any malformed cookie is simply "not signed in"
        return None


def current_user(request: Request) -> dict:
    """The signed-in user, as checked by the session guard (signature, session still open, user not blocked)."""
    user = getattr(request.state, "hive_user", None)
    if not user:
        raise HTTPException(401, "sign-in required")
    return user


# ------------------------------------------------------------------------------------------------ revocable sessions
_session_ok: dict[str, tuple[bool, float]] = {}
_session_seen: dict[str, float] = {}


async def session_open(user: dict) -> bool:
    """True while the cookie's session is open and its user is not blocked (cached for SESSION_CHECK_S)."""
    sid = user.get("sid")
    if not sid:
        return False                                 # cookies from before revocable sessions: sign in again
    hit = _session_ok.get(sid)
    if hit and time.time() - hit[1] < SESSION_CHECK_S:
        ok = hit[0]
    else:
        snap, usnap = await asyncio.gather(db().collection("web_sessions").document(sid).get(),
                                           db().collection("users").document(user["uid"]).get())
        d = snap.to_dict() or {}
        ok = snap.exists and not d.get("revoked") and not (usnap.to_dict() or {}).get("blocked")
        _session_ok[sid] = (ok, time.time())
    if ok and time.time() - _session_seen.get(sid, 0) > 120:
        _session_seen[sid] = time.time()
        await db().collection("web_sessions").document(sid).set(
            {"last_seen": dt.datetime.now(dt.timezone.utc)}, merge=True)
    return ok


async def close_session(sid: str, by: str, block: bool = False) -> dict:
    """Close one sign-in session (and optionally block its user, which closes all their sessions)."""
    ref = db().collection("web_sessions").document(sid)
    snap = await ref.get()
    if not snap.exists:
        raise HTTPException(404, "no such session")
    d = snap.to_dict() or {}
    now = dt.datetime.now(dt.timezone.utc)
    await ref.set({"revoked": True, "revoked_at": now, "revoked_by": by}, merge=True)
    _session_ok[sid] = (False, time.time())
    if block:
        await set_blocked(d["uid"], True, by)
    return {"sid": sid, "email": d.get("email"), "closed": True, "blocked": block}


async def set_blocked(uid: str, blocked: bool, by: str) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    await db().collection("users").document(uid).set(
        {"blocked": blocked, "blocked_at" if blocked else "unblocked_at": now, "blocked_by": by}, merge=True)
    n = 0
    if blocked:
        q = db().collection("web_sessions").where("uid", "==", uid).where("revoked", "==", False)
        async for snap in q.stream():
            await snap.reference.set({"revoked": True, "revoked_at": now, "revoked_by": by}, merge=True)
            _session_ok[snap.id] = (False, time.time())
            n += 1
    return n


def install(app) -> None:
    """Session guard: every /api call (except sign-in) and /admin needs an open session of a non-blocked user."""
    @app.middleware("http")
    async def session_guard(request: Request, call_next):
        p = request.url.path
        if (p.startswith("/api/") and not p.startswith("/api/auth/")) or p == "/admin":
            user = _unsign(request.cookies.get(COOKIE, "")) if SECRET else None
            if user:
                if not await session_open(user):
                    resp = JSONResponse({"detail": "session closed — please sign in again"}, status_code=401)
                    resp.delete_cookie(COOKIE, path="/")
                    return resp
                user["admin"] = user["email"] in ADMINS
                request.state.hive_user = user
        return await call_next(request)


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
    uid = uid_for(email)
    ref = db().collection("users").document(uid)
    prev = (await ref.get()).to_dict()
    if (prev or {}).get("blocked"):
        raise HTTPException(403, "Access to this site has been disabled for this account. / "
                                 "El acceso a este sitio fue deshabilitado para esta cuenta.")
    now = dt.datetime.now(dt.timezone.utc)
    sid = secrets.token_urlsafe(18)
    ua = request.headers.get("user-agent", "")[:200]
    user = {"uid": uid, "sid": sid, "email": email, "name": info.get("name", "")[:120],
            "picture": info.get("picture", "")[:500], "exp": int(time.time()) + SESSION_HOURS * 3600}
    await db().collection("web_sessions").document(sid).set({
        "uid": uid, "email": email, "name": user["name"], "created": now, "last_seen": now,
        "expires": now + dt.timedelta(hours=SESSION_HOURS), "ua": ua, "lang": body.lang[:5], "revoked": False})
    response.set_cookie(COOKIE, _sign(user), max_age=SESSION_HOURS * 3600, httponly=True, secure=True,
                        samesite="lax", path="/")
    await ref.set({"email": email, "name": user["name"], "picture": user["picture"],
                   "domain": email.split("@")[1], "hd": info.get("hd", ""), "last_seen": now, "last_login": now,
                   "logins": _inc(1), "lang": body.lang[:5], **({} if prev else {"first_seen": now})}, merge=True)
    await db().collection("logins").add({"ts": now, "uid": uid, "email": email, "sid": sid, "ua": ua,
                                          "lang": body.lang[:5]})
    try:
        await asyncio.wait_for(notify_signin(user, first=not prev, logins=int((prev or {}).get("logins", 0)) + 1,
                                             ua=ua, base=PUBLIC_URL or str(request.base_url).rstrip("/")), 10)
    except Exception as e:  # noqa: BLE001 — the alert must never block a sign-in
        print(f"sign-in alert failed: {type(e).__name__}: {e}", flush=True)
    return {"email": email, "name": user["name"], "picture": user["picture"], "admin": email in ADMINS}


if os.environ.get("HIVE_DEV_GCLOUD") == "1" and os.environ.get("HIVE_DEV_LOGIN"):
    @router.post("/api/auth/dev")
    async def auth_dev(response: Response):
        """Local development only (never set on Cloud Run): sign in as HIVE_DEV_LOGIN without Google."""
        email = os.environ["HIVE_DEV_LOGIN"].lower()
        sid = secrets.token_urlsafe(18)
        now = dt.datetime.now(dt.timezone.utc)
        user = {"uid": uid_for(email), "sid": sid, "email": email, "name": "Local developer", "picture": "",
                "exp": int(time.time()) + SESSION_HOURS * 3600}
        await db().collection("web_sessions").document(sid).set({
            "uid": user["uid"], "email": email, "name": user["name"], "created": now, "last_seen": now,
            "expires": now + dt.timedelta(hours=SESSION_HOURS), "ua": "local dev", "revoked": False})
        response.set_cookie(COOKIE, _sign(user), max_age=SESSION_HOURS * 3600, httponly=True, samesite="lax", path="/")
        return {"email": email}


@router.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    user = _unsign(request.cookies.get(COOKIE, "")) if SECRET else None
    if user and user.get("sid"):
        await db().collection("web_sessions").document(user["sid"]).set(
            {"revoked": True, "revoked_at": dt.datetime.now(dt.timezone.utc), "revoked_by": "signed out"}, merge=True)
        _session_ok[user["sid"]] = (False, time.time())
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


# ------------------------------------------------------------------------------------------------ sign-in alerts
def _action_url(base: str, user: dict, op: str) -> str:
    tok = _sign({"sid": user["sid"], "uid": user["uid"], "email": user["email"], "op": op,
                 "exp": int(time.time()) + ACTION_DAYS * 86400}, purpose="session-action")
    return f"{base}/admin/session-action?t={tok}"


def _short_ua(ua: str) -> str:
    os_ = next((n for k, n in [("Windows", "Windows"), ("Mac OS X", "macOS"), ("Android", "Android"),
                               ("iPhone", "iPhone"), ("iPad", "iPad"), ("CrOS", "ChromeOS"), ("Linux", "Linux")]
                if k in ua), "")
    br = next((n for k, n in [("Edg/", "Edge"), ("OPR/", "Opera"), ("Chrome/", "Chrome"), ("Firefox/", "Firefox"),
                              ("Safari/", "Safari")] if k in ua), "")
    return " · ".join(x for x in (br, os_) if x) or "—"


async def notify_signin(user: dict, *, first: bool, logins: int, ua: str, base: str) -> None:
    """Email the admins (via the Apps Script relay) with one-click links to close the session or block the user."""
    if not (MAIL_RELAY and NOTIFY):
        return
    import html as H

    import httpx
    from google.auth.transport import requests as greq
    from google.oauth2 import id_token

    when = dt.datetime.now(NOTIFY_TZ)
    offset = when.utcoffset().total_seconds() / 3600
    who = H.escape(user["name"] or user["email"])
    btn = ('display:inline-block;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:700;'
           'margin:4px 8px 4px 0;font-size:14px')
    html = f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;color:#1c1c1a">
  <p style="font-size:13px;color:#6d6b65;margin:0 0 6px">The Wursta Agent Hive · ingreso / sign-in</p>
  <h2 style="margin:0 0 10px;font-size:20px">{who} inició sesión</h2>
  <table style="font-size:14px;border-collapse:collapse;margin:0 0 14px">
    <tr><td style="color:#6d6b65;padding:3px 14px 3px 0">Nombre</td><td>{H.escape(user["name"] or "—")}</td></tr>
    <tr><td style="color:#6d6b65;padding:3px 14px 3px 0">Correo</td><td><b>{H.escape(user["email"])}</b></td></tr>
    <tr><td style="color:#6d6b65;padding:3px 14px 3px 0">Cuándo</td><td>{when:%Y-%m-%d %H:%M} (UTC{offset:+g})</td></tr>
    <tr><td style="color:#6d6b65;padding:3px 14px 3px 0">Ingresos</td><td>{"primera vez" if first else f"ingreso n.º {logins}"}</td></tr>
    <tr><td style="color:#6d6b65;padding:3px 14px 3px 0">Navegador</td><td>{H.escape(_short_ua(ua))}</td></tr>
  </table>
  <a href="{_action_url(base, user, "close")}" style="{btn};background:#1c1c1a;color:#fff">Cerrar esta sesión</a>
  <a href="{_action_url(base, user, "block")}" style="{btn};background:#c2412d;color:#fff">Cerrar y bloquear acceso</a>
  <a href="{base}/admin" style="{btn};background:#eef3f0;color:#13906a">Abrir Admin</a>
  <p style="font-size:12px;color:#6d6b65;margin-top:14px">Los enlaces piden confirmación antes de actuar y vencen en
  {ACTION_DAYS} días. La sesión dura {SESSION_HOURS} horas si no se cierra antes.</p>
</div>"""
    subject = f"Ingreso al Agent Hive: {user['name'] or user['email']} ({user['email']})"
    token = await asyncio.to_thread(id_token.fetch_id_token, greq.Request(), MAIL_RELAY)
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
        r = await c.post(MAIL_RELAY, json={"id_token": token, "to": NOTIFY, "subject": subject[:200], "html": html})
    if r.status_code >= 400 or '"ok":true' not in r.text.replace(" ", ""):
        print(f"sign-in alert not sent: {r.status_code} {r.text[:200]}", flush=True)


# ------------------------------------------------------------------------------------------------ email action links
_ACTION_PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width, initial-scale=1"><title>Agent Hive · sesión</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f6f5f1;color:#1c1c1a;margin:0;
display:grid;place-items:center;min-height:100vh;padding:16px}}.c{{background:#fff;border:1px solid #e3e0d8;
border-radius:16px;padding:26px;max-width:460px;width:100%}}h1{{font-size:20px;margin:0 0 8px}}p{{color:#3a3936}}
button{{font:inherit;font-weight:700;border:0;border-radius:999px;padding:10px 18px;margin:6px 8px 0 0;cursor:pointer}}
.k{{background:#1c1c1a;color:#fff}}.b{{background:#c2412d;color:#fff}}.m{{color:#6d6b65;font-size:13px}}
a{{color:#13906a}}</style></head><body><div class="c">{body}</div></body></html>"""


async def _action_target(t: str) -> tuple[dict, dict]:
    tok = _unsign(t, purpose="session-action")
    if not tok:
        raise HTTPException(400, "This link is invalid or has expired. / Este enlace no es válido o ya venció.")
    snap = await db().collection("web_sessions").document(tok["sid"]).get()
    if not snap.exists:
        raise HTTPException(404, "no such session")
    return tok, snap.to_dict() or {}


@router.get("/admin/session-action")
async def session_action_page(t: str):
    """Confirmation page for a link in the sign-in email (a GET never changes anything: mail scanners follow links)."""
    import html as H

    tok, d = await _action_target(t)
    blocked = bool(((await db().collection("users").document(tok["uid"]).get()).to_dict() or {}).get("blocked"))
    state = ("bloqueado" if blocked else "cerrada") if d.get("revoked") else "abierta"
    started = d.get("created").astimezone(NOTIFY_TZ).strftime("%Y-%m-%d %H:%M") if d.get("created") else "—"
    q = H.escape(t, quote=True)
    buttons = "" if d.get("revoked") and blocked else (
        f'<form method="post" action="/admin/session-action?t={q}&amp;op=close" style="display:inline">'
        f'<button class="k">Cerrar esta sesión</button></form>' if not d.get("revoked") else "") + (
        f'<form method="post" action="/admin/session-action?t={q}&amp;op=block" style="display:inline">'
        f'<button class="b">Cerrar y bloquear acceso</button></form>' if not blocked else "")
    body = (f"<h1>Sesión de {H.escape(d.get('name') or d.get('email', ''))}</h1>"
            f"<p><b>{H.escape(d.get('email', ''))}</b><br>Inicio: {started} · Estado: <b>{state}</b></p>{buttons}"
            f'<p class="m">Cerrar la sesión la desconecta en unos segundos; bloquear impide además que esa cuenta vuelva '
            f'a entrar (se puede desbloquear en <a href="/admin">Admin</a>).</p>')
    return HTMLResponse(_ACTION_PAGE.format(body=body), headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


@router.post("/admin/session-action")
async def session_action(t: str, op: str):
    import html as H

    tok, d = await _action_target(t)
    if op not in ("close", "block"):
        raise HTTPException(400, "unknown action")
    res = await close_session(tok["sid"], by="email link", block=op == "block")
    what = "Sesión cerrada y cuenta bloqueada" if res["blocked"] else "Sesión cerrada"
    body = (f"<h1>{what}</h1><p><b>{H.escape(d.get('email', ''))}</b> ya no puede usar esa sesión"
            f"{' ni volver a entrar' if res['blocked'] else ''}.</p><p class='m'><a href='/admin'>Abrir Admin</a></p>")
    return HTMLResponse(_ACTION_PAGE.format(body=body), headers={"Cache-Control": "no-store"})


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


@router.get("/api/admin/sessions")
async def admin_sessions(request: Request):
    from google.cloud import firestore

    require_admin(request)
    rows = await _docs(db().collection("web_sessions").order_by("created", direction=firestore.Query.DESCENDING), 300)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    for r in rows:
        r["state"] = "closed" if r.get("revoked") else ("expired" if str(r.get("expires", "")) < now else "open")
        r["browser"] = _short_ua(r.pop("ua", "") or "")
    return {"sessions": rows}


@router.post("/api/admin/sessions/{sid}/close")
async def admin_close_session(sid: str, request: Request, block: bool = False):
    admin = require_admin(request)
    return await close_session(sid, by=admin["email"], block=block)


@router.post("/api/admin/users/{uid}/block")
async def admin_block_user(uid: str, request: Request, blocked: bool = True):
    admin = require_admin(request)
    if blocked and uid == admin["uid"]:
        raise HTTPException(400, "you cannot block yourself")
    closed = await set_blocked(uid, blocked, by=admin["email"])
    return {"uid": uid, "blocked": blocked, "sessions_closed": closed}


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

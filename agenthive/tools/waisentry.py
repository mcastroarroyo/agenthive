"""WAISentry tools (SMB realm) — Wursta's managed 24/7 security operations, prototyped on synthetic telemetry.

Demo world: the fictional client Kitewing Software (kitewing.example, 62 people, Google Workspace, macOS / Windows /
ChromeOS laptops, a legacy on-prem footprint at the Millbrook office and the SaaS security tools KnowBe4, Mimecast and
DNSFilter). WAISentry went live on 2026-10-07, so telemetry covers 2026-10-08 to 2026-11-06.

Zero-PII: telemetry in fixtures/sentry_*.json is already tokenised (USR-/EXT-/FIL-/MSG-/DEV- tokens, deterministic
HMAC-SHA256). Re-identification happens only "inside the tenant" (explicit in_tenant flag, simulated). Triage scoring is
deterministic and stands in for Gemini triage; containment playbooks are simulated and return fixed timestamps.
Every time is Kitewing local time (UTC-6); the demo's "now" is 2026-11-06 09:30.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import functools
import hashlib
import hmac
import math
import re
from collections import Counter

from ._base import doc_text, err, fixture, hive_tool, ok

TODAY = dt.date(2026, 11, 6)
NOW = dt.datetime(2026, 11, 6, 9, 30, tzinfo=dt.timezone(dt.timedelta(hours=-6)))
DOMAIN = "kitewing.example"
_KEY = b"waisentry-demo/kitewing.example/tokeniser-v1"   # demo constant; in the service the key stays in the client's tenant
_PREFIX = {"user": "USR", "external": "EXT", "file": "FIL", "message": "MSG", "device": "DEV", "phone": "PHN",
           "account": "ACC"}
_TOKEN_RX = re.compile(r"\b(?:USR|EXT|FIL|MSG|DEV|PHN|ACC)-[0-9A-F]{4}\b")
_SEV_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_NOTE = "Synthetic demo: deterministic scoring stands in for Gemini triage; actions are simulated."


# --- helpers ------------------------------------------------------------------------------------------------------


def token(kind: str, value: str) -> str:
    """Deterministic zero-PII token: HMAC-SHA256(tenant key, kind:value) truncated to 4 hex characters."""
    v = re.sub(r"\s+", " ", str(value).strip().lower())
    return f"{_PREFIX[kind]}-{hmac.new(_KEY, f'{kind}:{v}'.encode(), hashlib.sha256).hexdigest()[:4].upper()}"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _dt(s: str | None) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        return None


def _hms(s: str | None) -> str | None:
    d = _dt(s)
    return d.strftime("%H:%M:%S") if d else None


def _secs(a: str | None, b: str | None) -> int | None:
    x, y = _dt(a), _dt(b)
    return int((y - x).total_seconds()) if x and y else None


def _human(s: int | None) -> str | None:
    if s is None:
        return None
    if s < 120:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{s // 3600} h {(s % 3600) // 60:02d} min"


def _sid(prefix: str, *parts: object) -> str:
    h = int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)
    return f"{prefix}-{4000 + h % 5000}"


def _scoring() -> dict:
    return fixture("sentry_telemetry")["scoring"]


def _score(signals: list[str]) -> int:
    sc = _scoring()
    return max(0, min(99, sc["base"] + sum(sc["weights"].get(s, 0) for s in signals)))


def _severity(score: int) -> str:
    return next(name for floor, name in _scoring()["bands"] if score >= floor)


def _confidence(score: int) -> float:
    return round(min(0.99, 0.40 + 0.006 * score), 2)


def _tech(tid: str | None) -> str | None:
    if not tid:
        return None
    name, tactic = _scoring()["techniques"].get(tid, ["", ""])
    return f"{tid} {name} ({tactic})" if name else tid


def _why(signals: list[str], n: int = 3) -> list[str]:
    sc = _scoring()
    pos = sorted((s for s in signals if sc["weights"].get(s, 0) > 0), key=lambda s: -sc["weights"][s])
    return [sc["phrases"].get(s, s) for s in pos[:n]]


def _incidents() -> list[dict]:
    return fixture("sentry_incidents")["incidents"]


def _incident(q: str) -> dict | None:
    k = str(q or "").strip().upper()
    for inc in _incidents():
        if k == inc["id"] or (len(k) >= 4 and k in inc["id"]):
            return inc
    return None


def _incident_events(inc: dict) -> list[dict]:
    if inc.get("batch"):
        evs = [e for e in fixture("sentry_telemetry")["batches"][inc["batch"]]["events"] if e.get("incident") == inc["id"]]
    else:
        evs = list(inc.get("events", []))
    return sorted(evs, key=lambda e: e["ts"])


@functools.lru_cache(maxsize=1)
def _vocab() -> dict[str, dict]:
    """In-tenant reverse map token -> identity (directory, devices, external contacts, files, message subjects)."""
    t = fixture("sentry_tenant")
    out: dict[str, dict] = {}
    for d in t["directory"]:
        out[token("user", d["email"])] = {"type": "user", "value": d["email"], "label": d["name"],
                                          "detail": f"{d['name']} <{d['email']}> — {d['title']}"}
        if d.get("device"):
            out[token("device", d["device"])] = {"type": "device", "value": d["device"], "label": d["device"],
                                                 "detail": f"{d['device']} ({d['name']}'s {d['device_os']} laptop)"}
    for c in t["external_contacts"]:
        out[token("external", c["email"])] = {"type": "external", "value": c["email"], "label": c["email"],
                                              "detail": f"{c['email']} — {c['org']}"}
    for f in t["files"]:
        out[token("file", f["name"])] = {"type": "file", "value": f["name"], "label": f["name"],
                                         "detail": f"{f['name']} ({f['folder']}, {f['label']})"}
    for m in t["messages"]:
        out[token("message", m)] = {"type": "message", "value": m, "label": f"'{m}'", "detail": f"subject '{m}'"}
    return out


def _resolve_user(q: str) -> str | None:
    """A USR token from a token, an email or a directory name — the name itself never appears in tool output."""
    s = str(q or "").strip()
    if not s:
        return None
    if re.fullmatch(r"USR-[0-9A-Fa-f]{4}", s):
        return s.upper()
    t = fixture("sentry_tenant")
    for d in t["directory"]:
        if _norm(s) in (_norm(d["email"]), _norm(d["name"]), _norm(d["email"].split("@")[0])):
            return token("user", d["email"])
    return None


def _reidentify_text(text: str) -> str:
    v = _vocab()
    return _TOKEN_RX.sub(lambda m: v[m.group(0)]["label"] if m.group(0) in v else m.group(0), text)


def _short(text: str, n: int = 220) -> str:
    text = str(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _after_hours(d: dt.datetime) -> bool:
    return d.weekday() >= 5 or not (7 <= d.hour < 19)


# --- Phase 1: AI triage ---------------------------------------------------------------------------------------------

_BATCH_WORDS = {"TB-1101-0200": ["sunday", "1101", "11 01", "nov 1", "november 1", "sun0200", "0200", "consent", "02 00"],
                "TB-1028-1400": ["wednesday", "1028", "10 28", "oct 28", "october 28", "1400", "laptop"],
                "TB-1106-0900": ["friday", "1106", "11 06", "today", "this morning", "morning", "0900", "nov 6"]}


def _batch(q: str) -> tuple[str | None, dict | None]:
    batches = fixture("sentry_telemetry")["batches"]
    k = str(q or "").strip().upper()
    if k in batches:
        return k, batches[k]
    for bid, b in batches.items():
        if b.get("doc") and b["doc"].upper() == k:
            return bid, b
    n = _norm(q)
    for bid, words in _BATCH_WORDS.items():
        if any(w in n for w in words):
            return bid, batches[bid]
    return None, None


@hive_tool("smb")
def sentry_triage_batch(batch_id: str = "TB-1101-0200") -> dict:
    """Score a batch of tokenised telemetry (Phase 1 AI triage): drop normal noise, return prioritised alerts with ATT&CK.

    Args:
        batch_id: Telemetry batch id — 'TB-1101-0200' (Sunday 2026-11-01 01:30-02:30), 'TB-1028-1400' (Wednesday
            2026-10-28 14:00-15:00) or 'TB-1106-0900' (this morning, 2026-11-06 09:00-09:30). The sample document key
            'sentry_alert_batch_sun0200' or words such as 'sunday' / 'this morning' also work.

    Returns:
        Raw records and events scored, how many were dropped as noise (grouped by reason), the alerts (score 0-99,
        severity, MITRE ATT&CK technique, confidence, why, triage latency) and the incidents they correlate into, with
        the lower-score context events that led up to them.
    """
    bid, b = _batch(batch_id)
    if not b:
        batches = fixture("sentry_telemetry")["batches"]
        return err(f"no telemetry batch matching {batch_id!r}", batches={k: v["label"] for k, v in batches.items()})
    thr = _scoring()["alert_threshold"]
    alerts, noise, by_inc = [], Counter(), {}
    for e in b["events"]:
        s = _score(e["signals"])
        if s < thr:
            noise[e.get("noise") or "Routine activity"] += 1
            continue
        a = {"alert": "AL-" + e["id"][3:], "event": e["id"], "time": _hms(e["ts"]), "source": e["src"],
             "actor": e["actor"], "what": _short(e["detail"], 260), "score": s, "severity": _severity(s),
             "technique": _tech(e.get("technique")), "also": [_tech(t) for t in e.get("also", [])] or None,
             "confidence": _confidence(s), "why": _why(e["signals"]), "triaged_in_s": e.get("triaged_s"),
             "incident": e.get("incident")}
        alerts.append({k: v for k, v in a.items() if v is not None})
        if e.get("incident"):
            by_inc.setdefault(e["incident"], []).append(a)
    incidents = []
    for iid, als in by_inc.items():
        inc = _incident(iid)
        ctx = [f"{_hms(e['ts'])} {e['src']}: {_short(e['detail'], 120)} (score {_score(e['signals'])})"
               for e in b["events"] if e.get("incident") == iid and _score(e["signals"]) < thr]
        incidents.append({"incident": iid, "title": inc["title"] if inc else None, "alerts": len(als),
                          "max_severity": max((a["severity"] for a in als), key=_SEV_RANK.get),
                          "actors": sorted({a["actor"] for a in als}), "first": als[0]["time"], "last": als[-1]["time"],
                          "techniques": list(dict.fromkeys(a["technique"] for a in als if a.get("technique"))),
                          "context_events": ctx or None, "status": inc["status"] if inc else None})
    raw = b["raw_records"]
    return ok(batch=bid, window=b["label"], raw_records=raw, raw_by_source=b["raw_by_source"],
              events_scored=len(b["events"]), dropped_as_noise=len(b["events"]) - len(alerts),
              alerts_raised=len(alerts), filtered_pct_of_raw=round(100 * (1 - len(alerts) / raw), 2),
              noise_by_reason=dict(noise.most_common()), alerts=alerts, incidents=incidents,
              next_step=(f"Investigate {incidents[0]['incident']} with sentry_investigate" if incidents
                         else "No incident — nothing to investigate"),
              note=_NOTE + " Identities are tokens (zero-PII); IPs, domains and app names stay in clear.")


# --- Phase 2: investigation (prepares the certified analyst's case) -----------------------------------------------


@hive_tool("smb")
def sentry_investigate(incident_id: str) -> dict:
    """Prepare the certified analyst's case for one incident: attack path, timeline, blast radius, IOCs and playbooks.

    Args:
        incident_id: Incident id, e.g. 'INC-1101-01' (the triage result names it).

    Returns:
        Incident header, ATT&CK attack path, timeline of events and SOC milestones, blast radius (users, apps, mail
        rules, files, devices, money at risk), IOCs, the analyst's verification checklist with answers, recommended
        pre-approved playbooks with targets, actions that must be escalated, and phase timings.
    """
    inc = _incident(incident_id)
    if not inc:
        return err(f"no incident {incident_id!r}", incidents=[i["id"] for i in _incidents()])
    tl = [f"{e['ts'][:10]} {_hms(e['ts'])} · {e['src']} · {e.get('technique') or '—'} · "
          f"{_short(e['detail'], 170)} (score {_score(e['signals'])})" for e in _incident_events(inc)]
    for label, key in (("first alert (AI triage)", "first_alert"), ("incident opened", "opened"),
                       ("analyst acknowledged", "analyst_ack"), ("analyst confirmed — true positive", "confirmed")):
        if inc.get(key):
            tl.append(f"{inc[key][:10]} {_hms(inc[key])} · SOC · {label}")
    tl.sort()
    path = [{"technique": _tech(t), "step": s} for t, s in inc["attack_path"]]
    return ok(
        incident=inc["id"], title=inc["title"], severity=inc["severity"], incident_status=inc["status"],
        category=inc["category"], primary_actor=inc["primary_actor"], actor_role=inc["actor_role"],
        analyst=inc["analyst"], attack_path=path, timeline=tl, blast_radius=inc["blast_radius"],
        iocs=inc.get("iocs") or None,
        analyst_checklist=[f"{q} -> {a}" for q, a in inc["analyst_checklist"]],
        recommended_playbooks=inc["recommended_playbooks"] or "none — no pre-approved playbook applies",
        escalate=inc["escalate"],
        phases={"triage_s": _secs(inc["first_malicious"], inc["first_alert"]),
                "investigation": _human(_secs(inc["opened"], inc["confirmed"]))},
        human_verification=(f"In the live service the certified analyst ({inc['analyst']}) verifies this case before "
                            "any containment; in this demo the case is prepared for that analyst and the checklist "
                            "answers come from the synthetic case file."),
        note="Tokens only — re-identification happens inside the client's tenant (Zero-PII Tokenizer).")


@hive_tool("smb")
def sentry_incident_list(status: str = "", min_severity: str = "low") -> dict:
    """List WAISentry incidents since go-live (2026-10-08) with severity, status, time to contain and outcome.

    Args:
        status: Optional filter: 'open', 'contained' or 'resolved' (empty = all).
        min_severity: Lowest severity to include: low, medium, high or critical.

    Returns:
        One row per incident (newest first): id, opened, title, severity, status, primary actor token, playbooks used,
        total time from first malicious event to containment, funds at risk / lost and the outcome.
    """
    floor = _SEV_RANK.get(min_severity.lower().strip(), 1)
    rows = []
    for inc in sorted(_incidents(), key=lambda i: i["opened"], reverse=True):
        if _SEV_RANK[inc["severity"]] < floor or (status and not inc["status"].startswith(status.lower().strip())):
            continue
        rows.append({"incident": inc["id"], "opened": inc["opened"][:16].replace("T", " "), "title": inc["title"],
                     "severity": inc["severity"], "status": inc["status"], "actor": inc["primary_actor"],
                     "playbooks": [c["playbook"] for c in inc.get("containment", [])] or None,
                     "time_to_contain": _human(_secs(inc["first_malicious"], inc.get("contained_at"))),
                     "funds_at_risk_usd": inc["funds_at_risk_usd"], "funds_lost_usd": inc["funds_lost_usd"],
                     "outcome": inc["outcome"]})
    return ok(as_of="2026-11-06 09:30", count=len(rows), incidents=rows,
              by_severity=dict(Counter(r["severity"] for r in rows)), note="Synthetic incidents (fictional client).")


@hive_tool("smb")
def sentry_response_timeline(incident_id: str) -> dict:
    """Measure an incident against WAISentry's phase targets and the traditional emailed-alert gap.

    Args:
        incident_id: Incident id, e.g. 'INC-1101-01'.

    Returns:
        Phase durations (AI triage vs 0-15 s, human investigation vs 1-3 min, active containment vs under 60 s,
        first malicious event to contained vs under 5 min) with met/not met, client-side escalation times, money at
        risk and lost, and the counterfactual gap if the alert had been emailed and read the next business morning.
    """
    inc = _incident(incident_id)
    if not inc:
        return err(f"no incident {incident_id!r}", incidents=[i["id"] for i in _incidents()])
    rows = inc.get("containment") or inc.get("planned_containment") or []
    end = max((r["end"] for r in rows), default=None) or inc.get("contained_at")
    planned = bool(inc.get("planned_containment"))
    triage = _secs(inc["first_malicious"], inc["first_alert"])
    invest = _secs(inc["opened"], inc["confirmed"])
    active = _secs(inc["authorised"], end) if inc.get("authorised") and rows else None
    total = _secs(inc["first_malicious"], end) if end else None
    phases = [
        {"phase": "1 · AI triage", "measured": _human(triage), "target": "0-15 s", "met": triage is not None and triage <= 15},
        {"phase": "2 · Human investigation (opened -> confirmed)", "measured": _human(invest), "target": "1-3 min",
         "met": invest is not None and invest <= 180},
        {"phase": "3 · Active containment (pre-approved playbooks)", "measured": _human(active), "target": "< 60 s",
         "met": active is not None and active < 60} if active is not None else
        {"phase": "3 · Active containment", "measured": "no pre-approved playbook applied", "target": "< 60 s", "met": None},
        {"phase": "First malicious event -> contained", "measured": _human(total), "target": "< 5 min (coordinated containment)",
         "met": total is not None and total < 300} if total is not None else
        {"phase": "First malicious event -> contained", "measured": "not contained yet", "target": "< 5 min", "met": None},
    ]
    first = _dt(inc["first_malicious"])
    gap = None
    if _after_hours(first):
        d = first.date() + dt.timedelta(days=1)
        if first.weekday() < 5 and first.hour < 7:
            d = first.date()
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        read = dt.datetime.combine(d, dt.time(8, 0), tzinfo=first.tzinfo)
        gap = {"alert_emailed": first.strftime("%A %Y-%m-%d %H:%M"), "first_read": read.strftime("%A %Y-%m-%d %H:%M"),
               "attacker_dwell_time": _human(int((read - first).total_seconds())),
               "waisentry_dwell_time": _human(total) if total else "contained by escalation (see client_actions)"}
    return ok(incident=inc["id"], title=inc["title"], severity=inc["severity"],
              first_malicious=inc["first_malicious"], contained_at=end, contained_by=inc.get("contained_by"),
              incident_status="planned (simulated)" if planned else inc["status"], phases=phases,
              playbooks=[{"playbook": r["playbook"], "start": _hms(r["start"]), "end": _hms(r["end"])} for r in rows] or None,
              client_actions=[f"{t[:16].replace('T', ' ')} — {a}" for t, a in inc.get("client_actions", [])] or None,
              funds_at_risk_usd=inc["funds_at_risk_usd"], funds_lost_usd=inc["funds_lost_usd"],
              traditional_gap=gap or "Business-hours event: an emailed alert is likely read the same day — the gap "
                                     "is in containment (ticket vs pre-approved playbook).",
              outcome=inc["outcome"])


# --- Zero-PII tokenisation ------------------------------------------------------------------------------------------

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")
_ACCT = re.compile(r"(?i)\b(account|acct|routing|iban|aba)\b([^\d\n]{0,25})((?:\d[ -]?){5,30}\d)")
_FILE = re.compile(r"(?:\"([^\"\n]{1,80}\.(?:xlsx|xls|csv|docx|doc|pdf|pptx|zip|exe|gsheet))\")|"
                   r"(?:'([^'\n]{1,80}\.(?:xlsx|xls|csv|docx|doc|pdf|pptx|zip|exe|gsheet))')|"
                   r"\b([\w-]+\.(?:xlsx|xls|csv|docx|doc|pdf|pptx|zip|exe))\b", re.I)
_HEADER = re.compile(r"^\s*\**\s*(From|To|Cc|Reply-To|Date|Subject|Sent|Attachment|Attachments)\s*:\s*\**\s*(.*)$", re.I)
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOM = re.compile(r"\b(?:[a-z0-9-]+\.)+example\b", re.I)


def _known_names() -> list[tuple[str, str]]:
    t = fixture("sentry_tenant")
    pairs = [(d["name"], token("user", d["email"])) for d in t["directory"] if d["type"] in ("employee", "contractor")]
    pairs += [(c["name"], token("external", c["email"])) for c in t["external_contacts"]
              if " " in c["name"] and "(" not in c["name"]]
    return sorted(pairs, key=lambda p: -len(p[0]))


def _tokenise_inline(text: str, found: Counter) -> str:
    t = fixture("sentry_tenant")
    internal = {d["email"].lower() for d in t["directory"]}
    for f in sorted(t["files"], key=lambda f: -len(f["name"])):
        if f["name"].lower() in text.lower():
            tk = token("file", f["name"])
            text = re.sub(re.escape(f["name"]), tk, text, flags=re.I)
            found[(tk, "file")] += 1

    def email(m):
        e = m.group(0)
        tk = token("user" if e.lower() in internal else "external", e)
        found[(tk, "user" if e.lower() in internal else "external")] += 1
        return tk
    text = _EMAIL.sub(email, text)

    def phone(m):
        tk = token("phone", re.sub(r"\D", "", m.group(0)))
        found[(tk, "phone")] += 1
        return tk
    text = _PHONE.sub(phone, text)

    def acct(m):
        tk = token("account", re.sub(r"\D", "", m.group(3)))
        found[(tk, "account")] += 1
        return f"{m.group(1)}{m.group(2)}{tk}"
    text = _ACCT.sub(acct, text)

    def file_(m):
        name = next(g for g in m.groups() if g)
        tk = token("file", name)
        found[(tk, "file")] += 1
        return m.group(0).replace(name, tk)
    text = _FILE.sub(file_, text)
    for name, tk in _known_names():
        if re.search(rf"\b{re.escape(name)}\b", text):
            found[(tk, "user" if tk.startswith("USR") else "external")] += len(re.findall(rf"\b{re.escape(name)}\b", text))
            text = re.sub(rf"\b{re.escape(name)}\b", tk, text)
    for d in t["directory"]:
        if d.get("device") and d["device"] in text:
            tk = token("device", d["device"])
            found[(tk, "device")] += 1
            text = text.replace(d["device"], tk)
    return text


@hive_tool("smb")
def sentry_tokenize(text: str = "", doc_key: str = "") -> dict:
    """Tokenise text the way WAISentry does inside the client's tenant before any alert leaves it (zero-PII).

    Args:
        text: Free text to tokenise — an email (with From/To/Subject headers), an alert or a log excerpt.
        doc_key: Alternatively a sample document key, e.g. 'sentry_email_vendor_bank_change'.

    Returns:
        The tokenised text (names, email addresses, file names, phone and account numbers, device names and message
        subjects/bodies replaced by deterministic HMAC tokens such as USR-xxxx), the list of tokens by type (never the
        original values), what stays in clear (IPs, domains), the detection signals extracted in-tenant from the
        message body, and how much was removed.
    """
    if doc_key and not text:
        text = doc_text(doc_key) or ""
        if not text:
            return err(f"no sample document {doc_key!r}")
    if not text.strip():
        return err("give text or doc_key")
    found: Counter = Counter()
    lines, out, body, in_headers, seen_header = text.splitlines(), [], [], False, False
    subject_tokens = []
    for ln in lines:
        m = _HEADER.match(ln)
        if m:
            seen_header, in_headers = True, True
            field, value = m.group(1).title(), m.group(2).strip().strip("*").strip()
            if field == "Subject" and value:
                tk = token("message", value)
                found[(tk, "message")] += 1
                subject_tokens.append(tk)
                out.append(f"Subject: {tk}")
            else:
                out.append(f"{field}: {_tokenise_inline(value, found)}")
            continue
        if seen_header and (in_headers and not ln.strip()):
            in_headers = False
            continue
        if seen_header and not in_headers and not ln.lstrip().startswith(("#", ">", "_")):
            body.append(ln)
            continue
        out.append(_tokenise_inline(ln, found))
    signals = None
    if body:
        btxt = "\n".join(body).strip()
        low = btxt.lower()
        signals = {
            "words": len(btxt.split()), "links": len(re.findall(r"https?://", low)),
            "asks_to_change_bank_details": any(w in low for w in ("bank", "account number", "routing", "remittance details", "iban")),
            "urgency": any(w in low for w in ("urgent", "today", "immediately", "asap", "before friday", "end of day")),
            "amount_mentioned": bool(re.search(r"\$\s?\d", btxt)),
            "asks_to_avoid_phone": any(w in low for w in ("do not call", "don't call", "not reachable by phone", "email only")),
            "invoice_reference": re.findall(r"\b[A-Z]{2,4}-\d{4}-\d{3,5}\b", btxt)[:3] or None,
            "domains": sorted(set(d.lower() for d in _DOM.findall(btxt))) or None,
        }
        tk = token("message", btxt)
        found[(tk, "message")] += 1
        out.append(f"[message body -> {tk}: {signals['words']} words]")
    tokenised = "\n".join(out)
    tokens = [{"token": tk, "type": kind, "occurrences": n} for (tk, kind), n in found.items()]
    return ok(tokenised_text=_short(tokenised, 3000), tokens=tokens,
              replaced=sum(found.values()), by_type=dict(Counter(t["type"] for t in tokens)),
              kept_in_clear={"ips": sorted(set(_IP.findall(text))) or None,
                             "domains": sorted(set(d.lower() for d in _DOM.findall(text))) or None},
              body_signals_extracted_in_tenant=signals, chars_before=len(text), chars_after=len(tokenised),
              method="HMAC-SHA256(tenant key, type:value) -> 4 hex chars; the same value always maps to the same "
                     "token, so the SOC can correlate without knowing who or what it is.",
              key_location="Tenant key stays in the client's Google Cloud tenant (this demo uses a fixed constant).")


@hive_tool("smb")
def sentry_reidentify(tokens: list[str], in_tenant: bool = False, requester: str = "", reason: str = "") -> dict:
    """Map tokens back to people, files and messages — only allowed inside the client's tenant, with a logged reason.

    Args:
        tokens: Tokens to resolve, e.g. ['USR-CFA4', 'FIL-1234'].
        in_tenant: True only when acting as the client's administrator inside the tenant (simulated). From the SOC
            side this must stay False and the request is refused.
        requester: Who asks (e.g. 'Noah Kim, IT & Security Administrator').
        reason: Why — normally an incident id; required and logged.

    Returns:
        Refused with the policy explanation when in_tenant is false or no reason is given; otherwise each token's
        type and identity, tokens not found in the tenant vocabulary, and a simulated audit-log entry id.
    """
    toks = [str(t).strip().upper() for t in (tokens or []) if str(t).strip()]
    if not toks:
        return err("give at least one token")
    if not in_tenant:
        return ok(refused=True, tokens_checked=len(toks),
                  explanation="Re-identification runs only inside the client's Google Cloud tenant, where the "
                              "tokenisation key lives. The Wursta SOC works on tokens only (Alarm Panel Model). Re-run "
                              "with in_tenant=true as the client's administrator (simulated).")
    if not reason.strip():
        return ok(refused=True, tokens_checked=len(toks),
                  explanation="Give a reason (normally the incident id) — every re-identification is logged.")
    v = _vocab()
    resolved = [{"token": t, "type": v[t]["type"], "identity": v[t]["detail"]} for t in toks if t in v]
    missing = [t for t in toks if t not in v]
    return ok(refused=False, resolved=resolved, not_found=missing or None,
              audit_entry=_sid("AUD", *toks, requester, reason), requester=requester or "unspecified", reason=reason,
              where="Rendered inside the kitewing.example tenant (simulated) — never sent to the SOC.", simulated=True)


@hive_tool("smb")
def sentry_soc_view(incident_id: str, in_tenant: bool = False) -> dict:
    """Show exactly what leaves the tenant for an incident (the SOC's 'alarm panel') and what stays behind.

    Args:
        incident_id: Incident id, e.g. 'INC-1101-01'.
        in_tenant: True to also render the client-side view with identities resolved (simulated, inside the tenant).

    Returns:
        The tokenised alert payload the Wursta SOC receives (actor and file tokens, techniques, IPs, timestamps),
        payload size, the fields withheld in the tenant, the Alarm Panel Model explanation, and — only when in_tenant
        is true — the same events with identities resolved for the client's administrator.
    """
    inc = _incident(incident_id)
    if not inc:
        return err(f"no incident {incident_id!r}", incidents=[i["id"] for i in _incidents()])
    evs = [e for e in _incident_events(inc) if _score(e["signals"]) >= _scoring()["alert_threshold"]] or _incident_events(inc)
    payload = {"incident": inc["id"], "severity": inc["severity"], "actor": inc["primary_actor"],
               "techniques": list(dict.fromkeys(t for t, _ in inc["attack_path"])),
               "events": [f"{_hms(e['ts'])} {e['src']} {e.get('technique') or ''}: {_short(e['detail'], 150)}" for e in evs[:6]]}
    res = ok(soc_payload=payload, payload_bytes=inc.get("soc_payload", {}).get("egress_bytes"),
             fields_sent=inc.get("soc_payload", {}).get("fields"),
             withheld_in_tenant=["people's names and email addresses", "file names and contents", "message subjects and bodies",
                                 "attachments", "device names", "phone and account numbers"],
             alarm_panel_model="Like a monitored home alarm: the monitoring centre sees 'zone 3 door opened at 02:05' and "
                               "acts on it, but never sees inside the house. WAISentry analysts see tokens, signals and "
                               "techniques; only the client can open the camera feed (re-identify) inside its own tenant.")
    if in_tenant:
        res["tenant_view"] = {"actor": _reidentify_text(payload["actor"]),
                              "events": [_reidentify_text(x) for x in payload["events"]],
                              "where": "Rendered inside the kitewing.example tenant (simulated) — never sent to the SOC."}
    return res


# --- Identity threat detection --------------------------------------------------------------------------------------


def _km(a: list[float], b: list[float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


@hive_tool("smb")
def sentry_identity_signals(user: str = "", detection_type: str = "", days: int = 30) -> dict:
    """Workspace identity detections: impossible travel, MFA fatigue, session hijack, risky consent, BEC, suspicious logins.

    Args:
        user: Optional user token (USR-xxxx); a name or email is tokenised in-tenant first and only the token is shown.
        detection_type: Optional filter word, e.g. 'travel', 'mfa', 'session', 'forwarding', 'bec', 'oauth', 'stuffing'.
        days: Look-back window in days (1-30; telemetry starts 2026-10-08).

    Returns:
        Counts by severity and type, and each detection (time, type, user token, ATT&CK technique, severity, status,
        incident, evidence) — travel detections include distance, minutes between sign-ins, implied speed and an
        impossible/possible verdict computed from the two locations.
    """
    data = fixture("sentry_identity")
    tok = _resolve_user(user) if user else None
    if user and not tok:
        return err(f"no user matching {user!r} in the tenant directory")
    since = NOW - dt.timedelta(days=max(1, min(int(days or 30), 30)))
    want = _norm(detection_type)
    rows = []
    for d in data["detections"]:
        if _dt(d["ts"]) < since:
            continue
        if tok and d["user"] != tok and tok not in d.get("users", []):
            continue
        if want and want not in _norm(d["type"]) and want not in _norm(d.get("evidence", "")):
            continue
        r = {"id": d["id"], "time": d["ts"][:16].replace("T", " "), "type": d["type"], "user": d["user"],
             "severity": d["severity"], "technique": _tech(d.get("technique")), "status": d["status"],
             "incident": d.get("incident"), "evidence": d["evidence"], "users": d.get("users")}
        tr = d.get("travel")
        if tr:
            a, b = data["geo"].get(tr["from"]), data["geo"].get(tr["to"])
            mins = _secs(tr["from_ts"], tr["to_ts"]) / 60
            km = _km(a, b) if a and b else None
            kmh = km / (mins / 60) if km and mins > 0 else None
            r["travel"] = {"from": tr["from"], "to": tr["to"], "to_ip": tr.get("to_ip"), "km": round(km) if km else None,
                           "minutes": round(mins, 1), "speed_kmh": round(kmh) if kmh else None,
                           "verdict": "impossible (> 900 km/h)" if kmh and kmh > 900 else "possible",
                           "concurrent_sessions": tr.get("concurrent") or None}
        rows.append({k: v for k, v in r.items() if v is not None})
    return ok(window=f"last {min(int(days or 30), 30)} days to 2026-11-06 09:30", user=tok, count=len(rows),
              by_severity=dict(Counter(r["severity"] for r in rows)), by_type=dict(Counter(r["type"] for r in rows)),
              detections=rows, note="Identities are tokens; names are resolved only inside the tenant.")


@hive_tool("smb")
def sentry_mail_rules(scope: str = "risky") -> dict:
    """Scan every mailbox for forwarding addresses and filters — hidden or external rules are classic BEC persistence.

    Args:
        scope: 'risky' (default: external or mail-hiding rules with any risk), 'external', 'hidden', 'all', or a user
            token / name to see one mailbox.

    Returns:
        The domain forwarding policy, counts, and each rule (mailbox token, kind, forward-to token, external, hides
        mail, criteria, who/what created it, status, risk, incident) with a recommended action.
    """
    data = fixture("sentry_identity")
    s = (scope or "risky").strip()
    tok = _resolve_user(s) if s.lower() not in ("risky", "external", "hidden", "all") else None
    if tok is None and s.lower() not in ("risky", "external", "hidden", "all"):
        return err(f"unknown scope {scope!r}", scopes=["risky", "external", "hidden", "all", "<user token or name>"])
    rows = []
    for r in data["mail_rules"]:
        if tok:
            keep = r["mailbox"] == tok
        elif s.lower() == "external":
            keep = r["external"]
        elif s.lower() == "hidden":
            keep = r["hides_mail"]
        elif s.lower() == "all":
            keep = True
        else:
            keep = (r["external"] or r["hides_mail"]) and r["risk"] != "none"
        if not keep:
            continue
        st = r["status"].lower()
        if r["risk"] == "critical":
            act = "Confirm removal, list what was forwarded, check the mailbox for other changes"
        elif "allowlisted" in st:
            act = "Keep (approved exception); review quarterly"
        elif r["external"]:
            act = "Delete the rule — the domain policy already blocks it; remind the user of the policy"
        elif r["hides_mail"]:
            act = "Benign hiding rule without forwarding — no action"
        else:
            act = "No action"
        rows.append({**r, "recommended_action": act})
    return ok(scanned_mailboxes=65, domain_policy=data["domain_policy"], count=len(rows),
              by_risk=dict(Counter(r["risk"] for r in rows)), rules=rows,
              note="Mailbox and recipient identities are tokens (zero-PII).")


_BANK = ("bank", "account number", "routing", "remittance details", "iban", "swift", "new account", "updated account")
_URGENT = ("urgent", "today", "immediately", "asap", "before friday", "end of day", "as soon as possible", "this week")
_SECRET = ("do not call", "don't call", "not reachable by phone", "email only", "only by email", "travelling", "traveling")


@hive_tool("smb")
def sentry_bec_check(email_text: str = "", doc_key: str = "") -> dict:
    """Check an email for business email compromise / payment diversion: lookalike vendor, bank change, real invoice.

    Args:
        email_text: The email with its headers (From, Reply-To, To, Date, Subject) and body.
        doc_key: Alternatively a sample document key, e.g. 'sentry_email_vendor_bank_change'.

    Returns:
        Risk score 0-99 and verdict, each indicator found (lookalike domain with edit distance and age, reply-to
        mismatch, bank-change and urgency language, a real open invoice and the amount at risk, after-hours send),
        the vendor master record to verify against, a linked incident when the sender is a known IOC, and the steps
        accounts payable must take.
    """
    if doc_key and not email_text:
        email_text = doc_text(doc_key) or ""
        if not email_text:
            return err(f"no sample document {doc_key!r}")
    if not email_text.strip():
        return err("give email_text or doc_key")
    data = fixture("sentry_identity")
    hdr = {}
    body_lines = []
    for ln in email_text.splitlines():
        m = _HEADER.match(ln)
        if m:
            hdr[m.group(1).lower()] = m.group(2).strip().strip("*").strip()
        else:
            body_lines.append(ln)
    body = "\n".join(body_lines)
    low = email_text.lower()
    sender = (_EMAIL.findall(hdr.get("from", "")) or [""])[0].lower()
    reply = (_EMAIL.findall(hdr.get("reply-to", "")) or [""])[0].lower()
    sdom = sender.split("@")[-1] if sender else ""
    rdom = reply.split("@")[-1] if reply else ""
    if not sdom:
        return err("could not find a From: address in the email")
    vendors = data["vendors"]
    best = min(vendors, key=lambda v: _lev(sdom, v["domain"]))
    dist = _lev(sdom, best["domain"])
    named = next((v for v in vendors if v["vendor"].split()[0].lower() in low), None)
    vendor = best if dist <= 3 else named
    ind, score = [], 5

    def add(name: str, pts: int, detail: str):
        nonlocal score
        score += pts
        ind.append({"indicator": name, "points": pts, "detail": detail})
    lv = _lev(sdom, vendor["domain"]) if vendor else 99
    if vendor and sdom != vendor["domain"] and (lv <= 3 or vendor["vendor"].split()[0].lower() in sdom):
        add("lookalike_domain", 30, f"{sdom} imitates {vendor['domain']} (edit distance {lv})")
    intel = data["domain_intel"].get(sdom)
    sent = None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            sent = dt.datetime.strptime(hdr.get("date", "")[:16], fmt)
            break
        except ValueError:
            continue
    if sent is None and hdr.get("date"):
        try:
            sent = email.utils.parsedate_to_datetime(hdr["date"]).replace(tzinfo=None)
        except (TypeError, ValueError, IndexError):
            sent = None
    ref = sent.date() if sent else TODAY
    if intel:
        age = (ref - dt.date.fromisoformat(intel["registered"])).days
        if age <= 30:
            add("newly_registered_domain", 15, f"{sdom} registered {intel['registered']} ({age} days before the email)")
    if rdom and rdom != sdom:
        add("reply_to_mismatch", 10, f"replies go to {rdom}, not {sdom}")
    if any(w in low for w in _BANK):
        add("bank_change_language", 20, "asks to change or confirm bank / remittance details")
    if any(w in low for w in _URGENT):
        add("urgency", 10, "time pressure")
    if any(w in low for w in _SECRET):
        add("avoids_verification", 10, "discourages phone verification")
    at_risk = None
    if vendor:
        for inv in vendor["open_invoices"]:
            if inv["invoice"].lower() in low:
                at_risk = inv
                add("references_real_invoice", 15, f"quotes open invoice {inv['invoice']} (${inv['amount_usd']:,}, due {inv['due']}) — "
                                                   "the sender knew internal details: check for a compromised mailbox")
    if sent and (sent.weekday() >= 5 or not (7 <= sent.hour < 19)):
        add("after_hours", 5, f"sent {sent.strftime('%A %H:%M')}")
    score = max(0, min(99, score))
    verdict = ("BEC / payment-diversion attempt — do not act on it" if score >= 75 else
               "Suspicious — verify before acting" if score >= 40 else "Low risk")
    linked = next((i["id"] for i in _incidents() if sdom in " ".join(i.get("iocs", {}).get("domains", []))), None)
    steps = ["Do not reply, click or change any bank details from this email",
             (f"Call {vendor['vendor']} on the number in the vendor master ({vendor['phone_on_file']}), not a number in the email"
              if vendor else "Verify with the vendor through a known channel"),
             "Hold any payment to this vendor until the call-back is done" + (f" ({at_risk['invoice']}, ${at_risk['amount_usd']:,})" if at_risk else ""),
             "Report it with the Phish Alert Button so Mimecast and WAISentry block the sender",
             "Ask IT to check the finance mailboxes for forwarding rules and risky app grants"]
    return ok(score=score, verdict=verdict, sender_domain=sdom, reply_to_domain=rdom or None, indicators=ind,
              vendor_master=({"vendor": vendor["vendor"], "domain": vendor["domain"], "phone_on_file": vendor["phone_on_file"],
                              "bank_on_file": vendor["bank_on_file"]} if vendor else None),
              amount_at_risk_usd=at_risk["amount_usd"] if at_risk else None, linked_incident=linked,
              steps_for_accounts_payable=steps)


# --- OAuth & SaaS governance ----------------------------------------------------------------------------------------

_TIER_PTS = {"critical": 40, "high": 30, "medium": 15, "low": 5, "none": 0}
_LOOKALIKE = ("secure", "viewer", "docs", "pdf", "google", "drive", "mail", "sign")


def _app_risk(a: dict, scope_risk: dict) -> tuple[int, list[str]]:
    tiers = [scope_risk.get(s, "medium") for s in a["scopes"]]
    top = max(tiers, key=lambda t: _TIER_PTS[t]) if tiers else "none"
    score, flags = 5 + _TIER_PTS[top], []
    if top in ("high", "critical"):
        flags.append(f"{top}-risk scopes")
    if not a["verified"]:
        score += 25
        flags.append("unverified publisher")
        if any(w in a["app"].lower() for w in _LOOKALIKE):
            score += 10
            flags.append("name imitates a document/mail tool")
    if a.get("publisher_domain_age_days", 9999) < 30:
        score += 15
        flags.append(f"publisher domain {a['publisher_domain_age_days']} days old")
    if "email" in a.get("grant_origin", ""):
        score += 15
        flags.append("granted from a link in an email")
    if a["users"] >= 5 and top in ("high", "critical") and not a["verified"]:
        score += 5
    if a.get("allowlisted"):
        score -= 30
    return max(0, min(99, score)), flags


@hive_tool("smb")
def sentry_oauth_inventory(view: str = "risky", app: str = "") -> dict:
    """Inventory third-party OAuth grants in Workspace: scopes, publisher verification, users, consent-phishing flags.

    Args:
        view: 'risky' (default), 'unverified', 'sanctioned' or 'all'.
        app: Optional app name or client id to show one app.

    Returns:
        The tenant's app-access policy, counts (apps, unverified, risky, users with risky grants), and each app with
        scopes and their risk tier, users (tokens), first grant, a risk score with band, consent-phishing indicators,
        status and a recommendation (revoke, review, keep).
    """
    data = fixture("sentry_saas")
    rows = []
    for a in data["oauth_apps"]:
        if app and _norm(app) not in _norm(a["app"] + " " + a["client_id"]):
            continue
        score, flags = _app_risk(a, data["scope_risk"])
        band = "critical" if score >= 90 else "high" if score >= 60 else "medium" if score >= 35 else "low"
        phishy = sum(f.startswith(("unverified", "name imitates", "publisher domain", "granted from")) for f in flags)
        st = a["status"].lower()
        if "revoked" in st:
            rec = "Already revoked — keep the client id blocked"
        elif a.get("allowlisted"):
            rec = "Keep (allowlisted); review scopes yearly"
        elif band in ("critical", "high"):
            rec = "Revoke now (PB-02 if part of an incident; otherwise a client-approved cleanup)"
        else:
            rec = "Review with the users; revoke if unused"
        rows.append({"app": a["app"], "client_id": a["client_id"], "verified": a["verified"],
                     "scopes": [f"{s} ({data['scope_risk'].get(s, 'medium')})" for s in a["scopes"]],
                     "users": a["users"], "user_tokens": a["user_tokens"] or None, "first_grant": a["first_grant"],
                     "risk_score": score, "risk": band, "consent_phishing_indicators": phishy, "flags": flags or None,
                     "status": a["status"], "incident": a.get("incident"), "recommendation": rec})
    v = (view or "risky").lower()
    if not app:
        if v == "risky":
            rows = [r for r in rows if r["risk"] in ("critical", "high") or ("revoked" in r["status"].lower())]
        elif v == "unverified":
            rows = [r for r in rows if not r["verified"]]
        elif v == "sanctioned":
            rows = [r for r in rows if r["verified"] and r["risk"] == "low"]
    if app and not rows:
        return err(f"no OAuth app matching {app!r}", apps=[a["app"] for a in data["oauth_apps"]])
    rows.sort(key=lambda r: -r["risk_score"])
    allapps = data["oauth_apps"]
    risky_users = sum(r["users"] for r in rows if r["risk"] in ("critical", "high") and "revoked" not in r["status"].lower())
    return ok(policy=data["app_policy"], apps_total=len(allapps), unverified_total=sum(not a["verified"] for a in allapps),
              shown=len(rows), users_with_active_risky_grants=risky_users,
              apps=[{k: val for k, val in r.items() if val is not None} for r in rows])


@hive_tool("smb")
def sentry_shadow_it(min_risk: str = "low") -> dict:
    """Discover shadow IT from DNSFilter and web-proxy logs: unsanctioned SaaS, users, data uploaded and alternatives.

    Args:
        min_risk: Lowest risk to include: low, medium, high or critical.

    Returns:
        Totals (services, MB uploaded) and each unsanctioned service with category, users, uploads, MB
        uploaded, first seen, risk, why it matters and the sanctioned alternative.
    """
    floor = _SEV_RANK.get((min_risk or "low").lower(), 1)
    rows = [s for s in fixture("sentry_saas")["shadow_it"] if _SEV_RANK[s["risk"]] >= floor]
    return ok(window="2026-10-08 to 2026-11-06", services=len(rows), uploaded_mb=sum(s["uploaded_mb"] for s in rows),
              shadow_it=rows,
              note="Users are counted per service (one person can use several services, so do not add them up); "
                   "per-user detail stays in the tenant.")


@hive_tool("smb")
def sentry_saas_alerts(days: int = 7, source: str = "") -> dict:
    """Summarise alerts from the client's SaaS security tools — KnowBe4, Mimecast, DNSFilter and the web proxy.

    Args:
        days: 7 (default) or 30 — the summary period (ending 2026-11-06).
        source: Optional single source: 'knowbe4', 'mimecast', 'dnsfilter' or 'web_proxy'.

    Returns:
        Per source: volumes, blocks and notable items (phish-prone %, impersonation hits, newly registered domains,
        uploads to unsanctioned SaaS) for the period, with the notable findings WAISentry correlated.
    """
    al = fixture("sentry_saas")["alerts"]
    key = "30" if int(days or 7) > 7 else "7"
    block = dict(al[key])
    if source:
        s = _norm(source).replace(" ", "_")
        s = {"web": "web_proxy", "proxy": "web_proxy", "kb4": "knowbe4"}.get(s, s)
        if s not in block:
            return err(f"unknown source {source!r}", sources=["knowbe4", "mimecast", "dnsfilter", "web_proxy"])
        block = {"period": block["period"], s: block[s]}
    return ok(days=int(key), **block)


# --- Fleet & hybrid -------------------------------------------------------------------------------------------------


@hive_tool("smb")
def sentry_fleet_posture(os_name: str = "", only_issues: bool = True) -> dict:
    """Posture of remote laptops and office PCs (macOS, Windows, ChromeOS): EDR, encryption, patches, risky networks.

    Args:
        os_name: Optional filter: 'macOS', 'Windows' or 'ChromeOS'.
        only_issues: True (default) lists only devices with issues; False lists every device (64 rows — only when
            the user asks for the full inventory).

    Returns:
        Totals by OS, compliance rate, EDR coverage on EDR-capable devices, encryption, devices more than 30 days
        behind on patches, devices that joined open or untrusted networks in the last 7 days, and the device list
        (device and owner tokens, OS, update status, EDR, issues).
    """
    fl = fixture("sentry_fleet")
    devs = [d for d in fl["devices"] if not os_name or _norm(os_name) in _norm(d["os"])]
    if not devs:
        return err(f"no devices for {os_name!r}", os=["macOS", "Windows", "ChromeOS"])
    capable = [d for d in devs if not d["edr"].startswith("n/a")]
    healthy = [d for d in capable if d["edr"].startswith("healthy")]
    risky_net = [d for d in devs if "open" in d["network_7d"] or "hotel" in d["network_7d"]]
    listed = [d for d in devs if d["issues"]] if only_issues else devs
    return ok(as_of=fl["as_of"], devices=len(devs), by_os=dict(Counter(d["os"].split(" (")[0] for d in devs)),
              compliant=sum(d["compliant"] for d in devs),
              compliance_pct=round(100 * sum(d["compliant"] for d in devs) / len(devs), 1),
              edr_coverage=f"{len(healthy)} of {len(capable)} EDR-capable devices healthy",
              unencrypted=[d["device"] for d in devs if not d["encryption"]] or None,
              patch_over_30_days=[d["device"] for d in devs if (d["patch_age_days"] or 0) > 30] or None,
              risky_networks_7d=[{"device": d["device"], "network": d["network_7d"]} for d in risky_net] or None,
              servers_edr="3 of 3 Millbrook servers healthy (see sentry_onprem_events)",
              listed=[{k: d[k] for k in ("device", "owner", "os", "office", "update_status", "edr", "compliant", "issues")}
                      for d in listed[:40]])


@hive_tool("smb")
def sentry_edr_alerts(days: int = 30, device: str = "") -> dict:
    """EDR alerts from laptops and servers with severity, ATT&CK technique, status and linked incident.

    Args:
        days: Look-back window in days (1-30).
        device: Optional device token (DEV-xxxx) or server name (e.g. 'MB-FS01').

    Returns:
        Counts by severity and the alerts (id, time, device, severity, technique, what, status, incident).
    """
    since = NOW - dt.timedelta(days=max(1, min(int(days or 30), 30)))
    rows = [a for a in fixture("sentry_fleet")["edr_alerts"] if _dt(a["ts"]) >= since
            and (not device or device.strip().upper() == a["device"].upper())]
    rows = [{**a, "technique": _tech(a.get("technique"))} for a in sorted(rows, key=lambda a: a["ts"], reverse=True)]
    return ok(window_days=min(int(days or 30), 30), count=len(rows), by_severity=dict(Counter(a["severity"] for a in rows)),
              alerts=[{k: v for k, v in a.items() if v is not None} for a in rows])


@hive_tool("smb")
def sentry_onprem_events(asset: str = "", min_severity: str = "info") -> dict:
    """On-prem hybrid view: firewall/IDS and syslog from the domain controller and file server, plus asset health.

    Args:
        asset: Optional asset: 'MB-DC01' (domain controller), 'MB-FS01' (file server), 'MB-SYSLOG01' (forwarder) or
            'MB-FW01' (firewall/IDS).
        min_severity: Lowest severity of events to include: info, low, medium, high or critical.

    Returns:
        The Millbrook site's assets (role, OS, EDR, log path, health) and notable events since go-live (type, count,
        severity, note, linked incident), including benign look-alikes that were ruled out.
    """
    op = fixture("sentry_fleet")["onprem"]
    floor = _SEV_RANK.get((min_severity or "info").lower(), 0)
    a = (asset or "").strip().upper()
    assets = [x for x in op["assets"] if not a or x["asset"] == a]
    events = [e for e in op["events"] if _SEV_RANK[e["severity"]] >= floor and (not a or a in e["asset"].upper())]
    if a and not assets:
        return err(f"unknown asset {asset!r}", assets=[x["asset"] for x in op["assets"]])
    return ok(site=op["site"], assets=assets, events=events, count=len(events),
              note="Windows events reach the in-tenant pipeline through MB-SYSLOG01; the firewall sends syslog directly to it.")


# --- Phase 3: active containment (pre-approved playbooks, simulated) ----------------------------------------------


def _pb(pid: str) -> dict:
    return next(p for p in fixture("sentry_playbooks")["playbooks"] if p["id"] == pid)


def _refuse(pid: str, inc: dict | None, reason: str) -> dict:
    return ok(executed=False, refused=True, playbook=pid, incident=inc["id"] if inc else None, reason=reason,
              next_step="Escalate to the on-call analyst with sentry_escalate", simulated=True)


def _gate(pid: str, incident_id: str) -> tuple[dict | None, dict | None]:
    inc = _incident(incident_id)
    if not inc:
        return None, err(f"no incident {incident_id!r} — playbooks run only against a confirmed incident",
                         incidents=[i["id"] for i in _incidents()])
    pb = _pb(pid)
    if _SEV_RANK[inc["severity"]] < _SEV_RANK[pb["min_severity"]]:
        return inc, _refuse(pid, inc, f"{inc['id']} is {inc['severity']}; {pid} needs {pb['min_severity']} or higher")
    if inc["status"] == "resolved":
        return inc, _refuse(pid, inc, f"{inc['id']} is already resolved")
    return inc, None


def _run(pid: str, inc: dict, target, units: int = 1) -> dict:
    pb = _pb(pid)
    auth = inc.get("authorised") or inc["confirmed"]
    dur = pb["duration_s"] if isinstance(pb["duration_s"], int) else 2 + 12 * max(1, units)
    start = _dt(auth) + dt.timedelta(seconds=pb["offset_s"])
    end = start + dt.timedelta(seconds=dur)
    return ok(executed=True, simulated=True, playbook=pid, name=pb["name"], incident=inc["id"],
              mode="replay of the original run" if inc["status"].startswith("contained") else "live (simulated)",
              target=target, action=pb["action"], api=pb["api"], authorised_at=_hms(auth),
              started=start.strftime("%H:%M:%S"), completed=end.strftime("%H:%M:%S"), duration_s=dur,
              time_to_contain_s=int((end - _dt(auth)).total_seconds()),
              since_first_malicious=_human(int((end - _dt(inc["first_malicious"])).total_seconds())),
              rollback=pb["rollback"], notify=pb["notify"])


@hive_tool("smb", kind="action")
def sentry_end_sessions(incident_id: str, user: str) -> dict:
    """PB-01 Instant web session termination: sign a user out everywhere and revoke their tokens (simulated).

    Args:
        incident_id: Confirmed incident id (severity high or critical), e.g. 'INC-1101-01'.
        user: User token (USR-xxxx) in the incident's blast radius; a name is tokenised in-tenant first.

    Returns:
        Executed or refused (with the reason), the target token, API used, start/end time, duration, time to contain
        from authorisation and from the first malicious event, rollback and who is notified.
    """
    inc, refusal = _gate("PB-01", incident_id)
    if refusal:
        return refusal
    tok = _resolve_user(user)
    if not tok:
        return err(f"no user matching {user!r}")
    if tok not in inc["blast_radius"].get("users", []):
        return _refuse("PB-01", inc, f"{tok} is not in {inc['id']}'s blast radius")
    return _run("PB-01", inc, tok)


@hive_tool("smb", kind="action")
def sentry_revoke_oauth_app(incident_id: str, app: str) -> dict:
    """PB-02 OAuth application revocation: revoke an app for every user and block its client id (simulated).

    Args:
        incident_id: Confirmed incident id (severity high or critical).
        app: App name or client id from the incident, e.g. 'PDF Secure Viewer'.

    Returns:
        Executed or refused (allowlisted apps and apps outside the incident are refused), users affected, timings,
        time to contain, rollback and notifications.
    """
    inc, refusal = _gate("PB-02", incident_id)
    if refusal:
        return refusal
    known = next((a for a in fixture("sentry_saas")["oauth_apps"] if _norm(app) and _norm(app) in _norm(a["app"] + " " + a["client_id"])), None)
    if known and known.get("allowlisted"):
        return _refuse("PB-02", inc, f"'{known['app']}' is allowlisted (sanctioned) — revoking it needs client approval")
    hit = next((a for a in inc["blast_radius"].get("apps", []) if _norm(app) and _norm(app) in _norm(a["app"] + " " + a["client_id"])), None)
    if not hit:
        return _refuse("PB-02", inc, f"'{app}' is not in {inc['id']}'s blast radius")
    res = _run("PB-02", inc, f"{hit['app']} ({hit['client_id']})")
    res["users_revoked"] = hit["users"]
    return res


@hive_tool("smb", kind="action")
def sentry_suspend_account(incident_id: str, user: str, hours: int = 4) -> dict:
    """PB-03 Targeted account suspension for up to 4 hours while the password is reset (simulated).

    Args:
        incident_id: Confirmed incident id (severity high or critical).
        user: User token (USR-xxxx) in the incident's blast radius; a name is tokenised in-tenant first.
        hours: Suspension window, 1-4 hours (the pre-approval maximum).

    Returns:
        Executed or refused (super admins, break-glass, users outside the incident or more than 4 hours are refused),
        auto-unsuspend time, timings, time to contain, rollback and notifications.
    """
    inc, refusal = _gate("PB-03", incident_id)
    if refusal:
        return refusal
    tok = _resolve_user(user)
    if not tok:
        return err(f"no user matching {user!r}")
    protected = {token("user", e) for e in fixture("sentry_playbooks")["protected_accounts"]}
    if tok in protected:
        return _refuse("PB-03", inc, f"{tok} is a super admin / break-glass account — suspension needs client approval")
    if not 1 <= int(hours) <= 4:
        return _refuse("PB-03", inc, f"{hours} h is outside the pre-approved 1-4 hour window")
    if tok not in inc["blast_radius"].get("users", []):
        return _refuse("PB-03", inc, f"{tok} is not in {inc['id']}'s blast radius")
    res = _run("PB-03", inc, tok)
    res["auto_unsuspend_at"] = (_dt(inc.get("authorised") or inc["confirmed"]) + dt.timedelta(hours=int(hours))).strftime("%Y-%m-%d %H:%M")
    return res


@hive_tool("smb", kind="action")
def sentry_quarantine_drive(incident_id: str, files: list[str] | None = None) -> dict:
    """PB-04 Drive access quarantine: remove public links and external shares from the incident's files (simulated).

    Args:
        incident_id: Confirmed incident id (severity medium or higher).
        files: Optional file tokens (FIL-xxxx); empty = every externally exposed file in the incident.

    Returns:
        Executed or refused, files quarantined (tokens), permissions removed, internal access untouched, timings, time
        to contain, rollback (recorded permissions) and notifications. Files are never deleted.
    """
    inc, refusal = _gate("PB-04", incident_id)
    if refusal:
        return refusal
    exposed = inc["blast_radius"].get("files_public") or []
    want = [f.strip().upper() for f in (files or []) if f.strip()] or exposed
    outside = [f for f in want if f not in exposed]
    if not exposed or outside:
        return _refuse("PB-04", inc, f"not externally exposed files of {inc['id']}: {outside or 'none in scope'}")
    res = _run("PB-04", inc, want, units=len(want))
    ext = inc["blast_radius"].get("external_recipients") or []
    res["permissions_removed"] = [f"'anyone with the link' on {f}" for f in want] + [f"external share to {e}" for e in ext]
    res["internal_access"] = "unchanged"
    return res


def _classify(action: str) -> dict:
    pb = fixture("sentry_playbooks")
    low = f" {action.lower()} "
    for x in pb["not_pre_approved"]:
        if x["id"] in ("X-WIPE", "X-ISOLATE") and any(k in low for k in x["keywords"]):
            return {"action": action, "verdict": "not pre-approved — escalate", "what": x["action"], "owner": x["owner"]}
    kws = pb["pre_approved_keywords"]
    verbs = ("revoke", "remove", "block", "disable", "kill", "end", "terminate", "quarantine", "unshare", "restrict",
             "sign", "log", "cut", "stop", "suspend", "lock")
    if any(v in low for v in verbs):
        if any(k in low for k in kws["PB-03"]):
            pid = "PB-03"
        elif (any(k in low for k in kws["PB-01"]) or re.search(r"\b(sign|log)(ged)?\b.{0,20}\bout\b", low)) \
                and not any(w in low for w in ("app ", "oauth", "application")):
            pid = "PB-01"
        elif any(k in low for k in kws["PB-02"]) and not any(w in low for w in ("file", "drive", "link", "folder")):
            pid = "PB-02"
        elif any(k in low for k in kws["PB-04"]) and not any(w in low for w in ("delete the file", "delete file")):
            pid = "PB-04"
        else:
            pid = None
        if pid and not any(w in low for w in ("forward", "filter", "password", "firewall", " ip ", "dns", "domain", "purge")):
            p = _pb(pid)
            return {"action": action, "verdict": "pre-approved", "playbook": pid, "name": p["name"], "tool": p["tool"],
                    "conditions": f"confirmed incident with severity {p['min_severity']}+; {p['limits']}"}
    for x in pb["not_pre_approved"]:
        if any(k in low for k in x["keywords"]):
            return {"action": action, "verdict": "not pre-approved — escalate", "what": x["action"], "owner": x["owner"]}
    return {"action": action, "verdict": "unclear — escalate", "owner": "on-call analyst decides with the client"}


@hive_tool("smb")
def sentry_playbook_check(actions: list[str]) -> dict:
    """Check requested response actions against the four pre-approved playbooks before acting.

    Args:
        actions: Plain-language actions, e.g. ['end her sessions', 'wipe the laptop', 'block the IP on the firewall'].

    Returns:
        For each action: pre-approved (with playbook id, tool and conditions) or not pre-approved / unclear (with who
        must do it), plus the pre-approval rules signed by the client.
    """
    acts = [a for a in (actions or []) if str(a).strip()]
    if not acts:
        return err("give at least one action")
    pb = fixture("sentry_playbooks")
    return ok(checks=[_classify(a) for a in acts], pre_approval={"signed": pb["pre_approval"]["signed"],
              "by": pb["pre_approval"]["by"], "rules": pb["pre_approval"]["rules"]})


@hive_tool("smb", kind="action")
def sentry_escalate(incident_id: str, actions: list[str], reason: str = "") -> dict:
    """Escalate actions outside the pre-approved playbooks to the on-call analyst and client contact (simulated page).

    Args:
        incident_id: Incident id, e.g. 'INC-1101-01'.
        actions: The actions that need a human decision, e.g. ['remove the forwarding filter', 'hold the payment'].
        reason: One-line context for the person paged.

    Returns:
        Escalation ticket id, priority (P1-P4 from the runbook), who was paged (analyst handle, client on-call,
        finance when money is involved), each action with its owner, and the runbook response target.
    """
    inc = _incident(incident_id)
    if not inc:
        return err(f"no incident {incident_id!r}", incidents=[i["id"] for i in _incidents()])
    acts = [a for a in (actions or []) if str(a).strip()]
    if not acts:
        return err("give at least one action to escalate")
    pb = fixture("sentry_playbooks")
    rows = [_classify(a) for a in acts]
    paged = [f"On-call analyst {inc['analyst'].split(' (')[0]} (certified Wursta SOC analyst)", pb["on_call"]["client"]]
    if any("payment" in r.get("what", "").lower() for r in rows) or inc.get("funds_at_risk_usd"):
        paged.append(pb["on_call"]["finance"])
    if any(w in inc.get("category", "") for w in ("on-prem", "endpoint")):
        paged.append(pb["on_call"]["millbrook"])
    return ok(ticket=_sid("ESC", inc["id"], *acts), incident=inc["id"], priority=pb["escalation_matrix"][inc["severity"]],
              paged=paged, actions=rows, reason=reason or None, escalation_status="awaiting a human decision",
              note="Pre-approved items found here should run as playbooks instead.", simulated=True)


# --- Compliance & cyber-insurance -----------------------------------------------------------------------------------

_FW_ALIASES = {"cyber_insurance": ["insurance", "cyber", "carrier", "underwrit", "mdr"],
               "ftc_safeguards": ["ftc", "safeguards", "314", "glba"],
               "hipaa": ["hipaa", "164", "ephi", "health"],
               "soc2": ["soc 2", "soc2", "trust services", "cc7", "aicpa"],
               "cmmc": ["cmmc", "800-171", "800 171", "cui", "dod", "defense"]}


@hive_tool("smb")
def sentry_control_map(framework: str = "all") -> dict:
    """Map WAISentry controls and evidence to a framework: cyber insurance, FTC Safeguards, HIPAA, SOC 2 or CMMC.

    Args:
        framework: 'cyber_insurance', 'ftc_safeguards' (16 CFR Part 314), 'hipaa' (e.g. 164.312(b)), 'soc2', 'cmmc'
            — free words like 'FTC Safeguards Rule' or 'HIPAA audit controls' work — or 'all' for a summary.

    Returns:
        For one framework: who it applies to, each requirement (reference, requirement, how WAISentry helps,
        status supports / partial / client, evidence ids with titles, gap) and counts. For 'all': counts per framework.
        Always includes the disclaimer that WAISentry supports compliance but does not confer it.
    """
    cm = fixture("sentry_compliance")
    ev = {e["id"]: e for e in cm["evidence"]}
    f = (framework or "all").lower()
    key = f if f in cm["frameworks"] else next((k for k, ws in _FW_ALIASES.items() if any(w in f for w in ws)), None)
    if not key:
        return ok(frameworks={k: {"name": v["name"], **dict(Counter(c["status"] for c in v["controls"]))}
                              for k, v in cm["frameworks"].items()}, disclaimer=cm["disclaimer"])
    fw = cm["frameworks"][key]
    controls = [{**c, "evidence": [f"{e} {ev[e]['title']} ({ev[e]['date']})" for e in c["evidence"]]} for c in fw["controls"]]
    return ok(framework=key, name=fw["name"], applies=fw["applies"], controls=controls,
              counts=dict(Counter(c["status"] for c in fw["controls"])), disclaimer=cm["disclaimer"])


def _questions_from_doc(text: str) -> list[str]:
    qs = []
    for ln in text.splitlines():
        m = re.match(r"^\s*(?:[-*]\s*)?\**\s*Q?\s*(\d{1,2})[.):]\s*\**\s*(.+)$", ln)
        if m and len(m.group(2)) > 12:
            qs.append(m.group(2).strip().strip("*").strip())
    return qs


@hive_tool("smb")
def sentry_answer_questionnaire(questions: list[str] | None = None, doc_key: str = "") -> dict:
    """Draft security-questionnaire answers (e.g. cyber-insurance renewal) from WAISentry's approved answers + evidence.

    Args:
        questions: The questions, one string each.
        doc_key: Alternatively a sample questionnaire key, e.g. 'sentry_insurance_questionnaire' (questions numbered
            'Q1.' ...).

    Returns:
        For each question: the drafted answer, status (Yes / Partial / Client to answer / no approved answer), the
        evidence references with titles and dates, and any gap to fix before submitting; counts by status.
    """
    if doc_key and not questions:
        text = doc_text(doc_key)
        if not text:
            return err(f"no sample document {doc_key!r}")
        questions = _questions_from_doc(text)
    qs = [q for q in (questions or []) if str(q).strip()]
    if not qs:
        return err("give questions or a doc_key with numbered questions (Q1. ...)")
    cm = fixture("sentry_compliance")
    ev = {e["id"]: e for e in cm["evidence"]}
    gaps = {c["ref"]: c.get("gap") for fw in cm["frameworks"].values() for c in fw["controls"]}
    out = []
    for i, q in enumerate(qs, 1):
        low = q.lower()
        best, hits = None, 0
        for a in cm["questionnaire_bank"]:
            n = sum(1 for k in a["keywords"] if k in low)
            if n > hits:
                best, hits = a, n
        if not best:
            out.append({"n": i, "question": _short(q, 160), "status": "No approved answer — escalate to the client (Noah Kim)",
                        "answer": None})
            continue
        out.append({"n": i, "question": _short(q, 160), "answer": best["answer"], "status": best["status"],
                    "evidence": [f"{e} {ev[e]['title']} ({ev[e]['date']})" for e in best["evidence"]] or None,
                    "gap": gaps.get(best["control"]), "answer_id": best["id"]})
    return ok(answers=[{k: v for k, v in a.items() if v is not None} for a in out], count=len(out),
              by_status=dict(Counter(a["status"] for a in out)),
              review="Draft for the client to review with its broker before submitting.", disclaimer=cm["disclaimer"])


# --- Posture & onboarding -------------------------------------------------------------------------------------------


def _posture_score(snap: str) -> int:
    p = fixture("sentry_posture")
    pts = p["status_points"]
    tot = sum(c["weight"] for c in p["checks"])
    return round(100 * sum(c["weight"] * pts[c[snap]["status"]] for c in p["checks"]) / tot)


@hive_tool("smb")
def sentry_posture_review(snapshot: str = "current") -> dict:
    """Run the complimentary 30-minute Security Posture & Application Review of the Google Workspace tenant.

    Args:
        snapshot: 'current' (2026-11-06), 'baseline' (the first review on 2026-10-01) or 'compare' (both, with what
            changed).

    Returns:
        The posture score 0-100 with band, each check (MFA coverage, super admins, external sharing defaults,
        auto-forwarding, legacy protocols, unverified OAuth apps, dormant accounts, DMARC, audit-log review, EDR and
        end-of-life systems, login challenges, mobile management) with status, finding, why it matters, fix, effort
        and owner, the top fixes by weight and the quick wins (<= 20 minutes).
    """
    p = fixture("sentry_posture")
    snap = (snapshot or "current").lower().strip()
    if snap not in ("current", "baseline", "compare"):
        return err("snapshot must be current, baseline or compare")

    def band(s: int) -> str:
        return "strong" if s >= 80 else "fair" if s >= 60 else "weak"
    if snap == "compare":
        rows = [{"id": c["id"], "check": c["check"], "baseline": c["baseline"]["status"], "current": c["current"]["status"],
                 "now": c["current"]["value"], "fix": c["fix"] if c["current"]["status"] != "pass" else None}
                for c in p["checks"]]
        b, c_ = _posture_score("baseline"), _posture_score("current")
        return ok(review=p["review"], baseline_score=b, current_score=c_, improvement=c_ - b,
                  improved=[r["check"] for r in rows if r["baseline"] != r["current"]],
                  still_open=[r["check"] for r in rows if r["current"] != "pass"],
                  checks=[{k: v for k, v in r.items() if v is not None} for r in rows])
    rows = [{"id": c["id"], "check": c["check"], "status": c[snap]["status"], "finding": c[snap]["value"],
             "why": c["why"], "fix": c["fix"] if c[snap]["status"] != "pass" else None,
             "effort_min": c["effort_min"] if c[snap]["status"] != "pass" else None,
             "owner": c["owner"], "weight": c["weight"]} for c in p["checks"]]
    open_ = sorted([r for r in rows if r["status"] != "pass"], key=lambda r: (-r["weight"], r["effort_min"] or 0))
    s = _posture_score(snap)
    return ok(review=p["review"], snapshot=snap, date=p["review"][f"{snap}_date"], score=s, band=band(s),
              passed=sum(r["status"] == "pass" for r in rows), partial=sum(r["status"] == "partial" for r in rows),
              failed=sum(r["status"] == "fail" for r in rows),
              checks=[{k: v for k, v in r.items() if v is not None and k != "weight"} for r in rows],
              top_fixes=[f"{r['id']} {r['check']}: {r['fix']} ({r['effort_min']} min, {r['owner']})" for r in open_[:5]],
              quick_wins=[r["id"] for r in open_ if (r["effort_min"] or 99) <= 20] or None)


@hive_tool("smb")
def sentry_onboarding_plan(start_date: str = "", hybrid_assets: list[str] | None = None,
                           saas_tools: list[str] | None = None) -> dict:
    """Lay out the 48-hour WAISentry onboarding: Day 1 connect, Day 2 baseline + hybrid, Day 3 active defence.

    Args:
        start_date: Day 1, YYYY-MM-DD (default: the next Monday after 2026-11-06). Weekends move to Monday.
        hybrid_assets: On-prem assets to connect on Day 2 (e.g. ['domain controller', 'file server', 'firewall/IDS']);
            empty = cloud-only, the hybrid step is skipped.
        saas_tools: SaaS security tools to connect on Day 1 (e.g. ['KnowBe4', 'Mimecast', 'DNSFilter']).

    Returns:
        Dated Day 1-3 plan with tasks and the client inputs needed each day, the go-live time, prerequisites, and the
        Kitewing onboarding as a worked example.
    """
    p = fixture("sentry_posture")["onboarding"]
    if start_date:
        try:
            d1 = dt.date.fromisoformat(start_date[:10])
        except ValueError:
            return err("start_date must be YYYY-MM-DD")
    else:
        d1 = TODAY + dt.timedelta(days=(7 - TODAY.weekday()) % 7 or 7)
    notes = []
    if d1 < TODAY:
        return err(f"start_date {d1} is in the past (today is {TODAY})")
    if d1.weekday() >= 5:
        notes.append(f"{d1} is a weekend — Day 1 moved to Monday")
        while d1.weekday() >= 5:
            d1 += dt.timedelta(days=1)
    days, d = [], d1
    for i, tpl in enumerate(p["days"]):
        if i:
            d += dt.timedelta(days=1)
            while d.weekday() >= 5:
                d += dt.timedelta(days=1)
        tasks = list(tpl["tasks"])
        inputs = list(tpl["client_inputs"])
        if tpl["day"] == 1 and saas_tools:
            tasks[3] = f"Connect SaaS security tools by API: {', '.join(saas_tools)}"
        if tpl["day"] == 2:
            if hybrid_assets:
                tasks[1] = f"Hybrid: ship events from {', '.join(hybrid_assets)} through a syslog forwarder to the in-tenant pipeline"
            else:
                tasks = [t for t in tasks if not t.startswith("Hybrid")]
                inputs = [x for x in inputs if "syslog" not in x.lower() and "firewall" not in x.lower()]
                notes.append("Cloud-only: no on-prem assets given, so the hybrid step is skipped")
        days.append({"day": tpl["day"], "date": d.isoformat(), "weekday": d.strftime("%A"), "name": tpl["name"],
                     "tasks": tasks, "client_inputs": inputs})
    return ok(promise=p["promise"], day_1=days[0]["date"], go_live=f"{days[-1]['date']} 18:00 (end of Day 3)",
              plan=days, notes=notes or None,
              prerequisites=["Google Workspace super admin available on Day 1", "A Google Cloud project in the client's "
                             "organisation for the in-tenant pipeline", "Signed pre-approval for PB-01 to PB-04 by Day 3"],
              example=p["kitewing_example"])


@hive_tool("smb")
def sentry_cost_compare(people: int = 62) -> dict:
    """Compare an internal 24/7 SOC, a traditional MSSP and WAISentry on staffing, tooling, ramp time and cost floor.

    Args:
        people: Company size, for context only (WAISentry pricing is quoted by Wursta — never estimated here).

    Returns:
        The three options from the WAISentry brief (staffing, tooling, ramp, annual cost floor, who does level 2/3),
        3-year cost floors for the two alternatives, an illustrative staffing calculation for 24/7 coverage, the
        threat and breach-cost facts with their sources, and a reminder that WAISentry's fee comes from a Wursta quote.
    """
    if not 5 <= int(people) <= 5000:
        return err("people must be between 5 and 5000")
    p = fixture("sentry_posture")
    opts = p["options"]
    floors = {o["option"]: (o["annual_floor_usd"] * 3 if o["annual_floor_usd"] else None) for o in opts}
    return ok(company_size=int(people), options=opts,
              three_year_floor_usd={k: v for k, v in floors.items() if v},
              staffing_illustration="24/7/365 = 8,760 hours a year; at roughly 1,800 working hours per analyst that is "
                                    "about 4.9 people before holidays and sick cover — hence 5+ FTE (illustrative).",
              waisentry_price="Predictable monthly fee — ask Wursta for a quote; this agent never estimates it.",
              facts=p["facts"],
              note="Figures come from the WAISentry brief; the 3-year floors simply multiply the brief's annual minimums.")

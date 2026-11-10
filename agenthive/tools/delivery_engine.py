"""Delivery Engine tools — realm `delivery`, clusters *delivery_engine* (dlv_) and *atlas* (atlas_).

Everything is deterministic over synthetic fixtures frozen at the demo date 2026-11-06:
  dlv_*    SOW estimation and pricing, LATAM localisation, scope control and change orders, VDR template checks,
           enablement plans and quizzes, certification tracking, migration readiness, change management,
           migration reporting and demo scripting.
  atlas_*  the Atlas Workspace-migration suite over ONE fictional legacy tenant — Kestrel Manufacturing Inc.,
           1,200 users on Microsoft 365 + Windows file shares (project KES-WS-2026, SOW-2026-0412): pre-flight,
           wave planning, user comms, bulk transfer, delta sync, post-migration validation and status.
Side effects (emails, change orders, retries, syncs) are simulated and say so.
"""
from __future__ import annotations

import datetime as dt
import functools
import hashlib
import math
import re

from ._base import doc_text, err, fixture, hive_tool, ok

DEMO_TODAY = dt.date(2026, 11, 6)
DEMO_NOW = dt.datetime(2026, 11, 6, 9, 0)


# --- shared helpers ------------------------------------------------------------------------------------------------


def _text(text_or_key: str) -> str:
    """Accept raw text or the key of a sample document (e.g. 'dlv_discovery_harborline')."""
    key = (text_or_key or "").strip()
    if re.fullmatch(r"[a-z0-9_]+", key) and (d := doc_text(key)):
        return d
    return text_or_key or ""


def _date(s: str, default: dt.date | None = None) -> dt.date | None:
    if not s:
        return default
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _dtm(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(s)[:16])
    except ValueError:
        return None


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _sid(*parts: object) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:6].upper()


def _add_business_days(d: dt.date, n: int) -> dt.date:
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _guard(fn):
    """Tools must never raise: malformed model input (wrong types, missing keys) becomes an err() result."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (TypeError, ValueError, KeyError, AttributeError, IndexError, ZeroDivisionError) as e:
            return err(f"invalid input for {fn.__name__}: {type(e).__name__}: {e}"[:300])

    return wrapper



# =====================================================================================================================
# ATLAS — shared tenant model and wave planner
# =====================================================================================================================

_INT_FIELDS = ("users", "mailbox_items", "onedrive_files", "share_files", "unique_acl_folders", "lit_hold_users",
               "delegates", "shared_mailboxes", "mobile_devices", "pst_files", "oversized_mailboxes")
_FLOAT_FIELDS = ("mailbox_gb", "onedrive_gb", "share_gb", "pst_gb")


def _dept_metrics(d: dict) -> dict:
    users = max(1, d["users"])
    score = (1.0 + min(d["mailbox_gb"] / users / 10, 2.0) + 4 * d["lit_hold_users"] / users
             + 1.5 * d["delegates"] / users + 0.5 * min(d["unique_acl_folders"] / 1000, 2.0)
             + 0.1 * d["oversized_mailboxes"] + (0.5 if d["share_files"] > 400000 else 0.0))
    return {**d, "data_gb": d["mailbox_gb"] + d["onedrive_gb"] + d["share_gb"],
            "avg_mailbox_gb": round(d["mailbox_gb"] / users, 1), "complexity_score": round(score, 2),
            "complexity": "low" if score < 2 else "medium" if score < 3 else "high"}


def _split(d: dict, parts: int) -> list[dict]:
    out = []
    for i in range(parts):
        u = dict(d)
        for f in _INT_FIELDS:
            u[f] = d[f] // parts + (1 if i < d[f] % parts else 0)
        for f in _FLOAT_FIELDS:
            u[f] = round(d[f] / parts, 1)
        u["data_gb"] = round(u["mailbox_gb"] + u["onedrive_gb"] + u["share_gb"], 1)
        u["part"] = f"{i + 1}/{parts}" if parts > 1 else ""
        out.append(u)
    return out


def _plan(max_users: int = 260, max_data_gb: float = 7500.0, first_cutover: str = "2026-10-10",
          cadence_days: int = 7, pilot: str = "it", executives_last: bool = True) -> list[dict]:
    t = fixture("atlas_tenant")
    c = t["constraints"]
    units: list[dict] = []
    for d in map(_dept_metrics, t["departments"]):
        parts = max(1, math.ceil(d["users"] / max_users), math.ceil(d["data_gb"] / max_data_gb))
        units += _split(d, parts)
    pilot_u = [u for u in units if u["id"] == pilot]
    exec_u = [u for u in units if executives_last and u["id"] == "executive" and u["id"] != pilot]
    rest = sorted((u for u in units if u["id"] != pilot and not (executives_last and u["id"] == "executive")),
                  key=lambda u: (u["complexity_score"], u["id"], u["part"]))
    groups: list[list[dict]] = [pilot_u] if pilot_u else []
    cur: list[dict] = []
    for u in rest:
        if cur and (sum(x["users"] for x in cur) + u["users"] > max_users
                    or sum(x["data_gb"] for x in cur) + u["data_gb"] > max_data_gb):
            groups.append(cur)
            cur = []
        cur.append(u)
    if cur:
        groups.append(cur)
    if exec_u:
        groups.append(exec_u)

    blackouts = set(c["global_blackouts"])
    date = dt.date.fromisoformat(first_cutover)
    waves = []
    for i, g in enumerate(groups):
        notes = []
        while date.isoformat() in blackouts or any(date.isoformat() in u["blackouts"] for u in g):
            why = c["blackout_reasons"].get(date.isoformat()) or "department blackout (" + ", ".join(
                u["name"] for u in g if date.isoformat() in u["blackouts"]) + ")"
            notes.append(f"moved from {date.isoformat()}: {why}")
            date += dt.timedelta(days=cadence_days)
        gb = {"mail": round(sum(u["mailbox_gb"] for u in g), 1), "drive": round(sum(u["onedrive_gb"] for u in g), 1),
              "shares": round(sum(u["share_gb"] for u in g), 1)}
        gb["total"] = round(sum(gb.values()), 1)
        lead = max(c["min_bulk_lead_days"], math.ceil(gb["total"] / c["daily_bulk_throughput_gb"]) + 3)
        users = sum(u["users"] for u in g)
        is_pilot = bool(pilot_u) and g is groups[0]
        is_exec = bool(exec_u) and g is groups[-1]
        label = ("Pilot" if is_pilot else "White-glove" if is_exec else f"Wave {i}") + " · " + ", ".join(
            u["name"] + (f" ({u['part']})" if u["part"] else "") for u in g)
        waves.append({
            "wave_id": f"W{i}", "label": label, "cutover_date": date.isoformat(), "cutover_day": date.strftime("%A"),
            "bulk_start": (date - dt.timedelta(days=lead)).isoformat(),
            "delta_sync_start": (date - dt.timedelta(days=1)).isoformat() + "T18:00",
            "departments": [{"id": u["id"], "name": u["name"], "users": u["users"], "part": u["part"],
                             "complexity": u["complexity"]} for u in g],
            "users": users, "data_gb": gb,
            "items": {"mail": sum(u["mailbox_items"] for u in g), "drive": sum(u["onedrive_files"] for u in g),
                      "shares": sum(u["share_files"] for u in g)},
            "complexity": max((u["complexity"] for u in g), key=["low", "medium", "high"].index),
            "complexity_score": round(sum(u["complexity_score"] * u["users"] for u in g) / max(users, 1), 2),
            "flags": {"lit_hold_users": sum(u["lit_hold_users"] for u in g),
                      "delegates": sum(u["delegates"] for u in g),
                      "oversized_mailboxes": sum(u["oversized_mailboxes"] for u in g),
                      "pst_files": sum(u["pst_files"] for u in g),
                      "shared_mailboxes": sum(u["shared_mailboxes"] for u in g),
                      "mobile_devices": sum(u["mobile_devices"] for u in g),
                      "spanish_speakers": round(sum(u["users"] * u["spanish_pct"] for u in g)),
                      "unique_acl_folders": sum(u["unique_acl_folders"] for u in g)},
            "notes": notes + (["pilot wave: IT validates runbook and tooling"] if is_pilot else [])
                     + (["white-glove: desk-side support, delegates migrated together"] if is_exec else []),
        })
        date += dt.timedelta(days=cadence_days)
    return waves


def _baseline() -> list[dict]:
    return _plan()


def _wave(wave_id: str) -> tuple[dict | None, dict]:
    wid = (wave_id or "").strip().upper()
    w = next((w for w in _baseline() if w["wave_id"] == wid), None)
    return w, fixture("atlas_run_state")["waves"].get(wid, {"status": "scheduled", "jobs": {}})


def _wave_ids() -> list[str]:
    return [w["wave_id"] for w in _baseline()]


# --- Atlas 1 · Pre-Flight Auditor ----------------------------------------------------------------------------------


@hive_tool("delivery")
@_guard
def atlas_tenant_inventory(department: str = "") -> dict:
    """Inventory the legacy Kestrel Manufacturing tenant (Microsoft 365 + file shares): users, mailboxes, data, risk.

    Args:
        department: Optional department id or name (e.g. 'engineering', 'Finance'). Empty returns every department.

    Returns:
        Tenant facts, totals (users, mailbox/OneDrive/share GB and item counts) and per-department metrics with a
        complexity score (low / medium / high) used by the wave planner.
    """
    t = fixture("atlas_tenant")
    rows = [_dept_metrics(d) for d in t["departments"]]
    if department:
        q = department.lower()
        rows = [r for r in rows if q in (r["id"], r["name"].lower()) or q in r["name"].lower()]
        if not rows:
            return err(f"unknown department {department!r}", available=[d["id"] for d in t["departments"]])
    keep = ("id", "name", "site", "users", "avg_mailbox_gb", "mailbox_gb", "mailbox_items", "onedrive_gb",
            "onedrive_files", "share", "share_gb", "share_files", "data_gb", "lit_hold_users", "delegates",
            "shared_mailboxes", "mobile_devices", "pst_files", "oversized_mailboxes", "unique_acl_folders",
            "spanish_pct", "complexity_score", "complexity")
    depts = [{k: r[k] for k in keep} for r in rows]
    totals = {k: round(sum(r[k] for r in rows), 1) for k in ("users", "mailbox_gb", "onedrive_gb", "share_gb",
                                                                 "data_gb", "mailbox_items", "onedrive_files",
                                                                 "share_files", "pst_files", "mobile_devices")}
    totals["data_tb"] = round(totals["data_gb"] / 1000, 2)
    return ok(tenant=t["tenant"], totals=totals, departments=depts, scanned_at=t["tenant"]["scanned_at"])


@hive_tool("delivery")
@_guard
def atlas_preflight_scan(check: str = "all", only_open: bool = False) -> dict:
    """Run the pre-flight blocker scan on the legacy tenant: holds, oversized mailboxes, PSTs, paths, ACLs, relays.

    Args:
        check: 'all' or one check id, e.g. 'litigation_hold', 'long_paths', 'shared_drive_item_limit',
            'broken_inheritance', 'smtp_relay_apps', 'public_folders', 'pst_files'.
        only_open: If True, return only findings that are still open or in progress.

    Returns:
        Findings sorted by severity (critical, high, medium, low) with counts, affected departments, remediation,
        owner and status, plus computed shared-drive item-limit checks and a blocker summary.
    """
    t = fixture("atlas_tenant")
    limit = t["constraints"]["max_items_per_shared_drive"]
    partner = t["tenant"].get("delivery_partner", "Wursta")   # the delivery firm (editions name their own)
    findings = [dict(f) for f in t["findings"]]
    for d in t["departments"]:   # computed: Shared drives hold at most `limit` items each
        if d["share_files"] > limit:
            n = math.ceil(d["share_files"] / limit)
            findings.append({
                "id": f"PF-SD-{d['id']}", "check": "shared_drive_item_limit", "severity": "high",
                "departments": [d["id"]], "count": d["share_files"],
                "title": f"{d['share']} has {d['share_files']:,} items — over the {limit:,}-item shared drive limit",
                "detail": f"Needs at least {n} shared drives (split by top-level folder).",
                "remediation": f"Split into {n}+ shared drives before the bulk pass; map each top-level folder.",
                "owner": f"{partner} solutions architect", "status": "in_progress", "computed": True})
    if check and check != "all":
        findings = [f for f in findings if f["check"] == check]
        if not findings:
            return err(f"unknown check {check!r}",
                       available=sorted({f["check"] for f in t["findings"]} | {"shared_drive_item_limit"}))
    if only_open:
        findings = [f for f in findings if f["status"] in ("open", "in_progress")]
    sev = ["critical", "high", "medium", "low"]
    findings.sort(key=lambda f: (sev.index(f["severity"]), f["id"]))
    open_ = [f for f in findings if f["status"] in ("open", "in_progress")]
    blockers = [f["id"] for f in open_ if f["severity"] in ("critical", "high")]
    return ok(tenant=t["tenant"]["client"], scanned_at=t["tenant"]["scanned_at"], findings=findings,
              summary={"total": len(findings), "open_or_in_progress": len(open_), "blockers_open": blockers,
                       "by_severity": {s: sum(1 for f in findings if f["severity"] == s) for s in sev}},
              verdict="blockers open — resolve before the affected waves" if blockers else "no open blockers")


# --- Atlas 2 · Batch Planner -----------------------------------------------------------------------------------------


@hive_tool("delivery")
@_guard
def atlas_plan_waves(max_users_per_wave: int = 260, max_data_gb_per_wave: float = 7500.0,
                     first_cutover: str = "2026-10-10", cadence_days: int = 7, pilot_department: str = "it",
                     executives_last: bool = True) -> dict:
    """Group Kestrel users into migration waves by department and data complexity, with cutover and bulk dates.

    Called with the defaults it returns the APPROVED BASELINE plan (W0-W7) that every other Atlas agent uses; change
    any parameter for a what-if plan and the result is compared with the baseline.

    Args:
        max_users_per_wave: Maximum users per wave (25-1200). Larger departments are split into parts.
        max_data_gb_per_wave: Maximum source data per wave in GB (bulk-copy capacity before cutover).
        first_cutover: Cutover date of the pilot wave (YYYY-MM-DD, a Saturday).
        cadence_days: Days between wave cutovers (3-28).
        pilot_department: Department id that goes first as pilot (e.g. 'it'); '' for no pilot.
        executives_last: Keep the Executive office in a final white-glove wave.

    Returns:
        Waves with cutover date, bulk-start date, delta-sync start, departments, users, data GB by workload,
        complexity and flags (holds, delegates, oversized mailboxes, Spanish speakers), plus a summary and the
        difference versus the baseline.
    """
    if not 25 <= max_users_per_wave <= 1200 or not 3 <= cadence_days <= 28 or max_data_gb_per_wave < 500:
        return err("max_users_per_wave must be 25-1200, cadence_days 3-28, max_data_gb_per_wave >= 500")
    if _date(first_cutover) is None:
        return err("first_cutover must be YYYY-MM-DD")
    waves = _plan(max_users_per_wave, max_data_gb_per_wave, first_cutover, cadence_days, pilot_department,
                  executives_last)
    base = _baseline()
    is_base = (max_users_per_wave, max_data_gb_per_wave, first_cutover, cadence_days, pilot_department,
               executives_last) == (260, 7500.0, "2026-10-10", 7, "it", True)
    summary = {"waves": len(waves), "users": sum(w["users"] for w in waves),
               "data_tb": round(sum(w["data_gb"]["total"] for w in waves) / 1000, 2),
               "first_cutover": waves[0]["cutover_date"], "last_cutover": waves[-1]["cutover_date"],
               "rules": "pilot first, then ascending complexity, executives last; waves capped by users and GB; "
                        "global and department blackouts respected; bulk lead = max(10 d, data/800 GB per day + 3 d)"}
    diff = None if is_base else {
        "baseline_waves": len(base), "baseline_last_cutover": base[-1]["cutover_date"],
        "delta_days": (dt.date.fromisoformat(waves[-1]["cutover_date"])
                       - dt.date.fromisoformat(base[-1]["cutover_date"])).days}
    return ok(plan="baseline (approved 2026-09-25)" if is_base else "what-if", summary=summary, waves=waves,
              vs_baseline=diff)


# --- Atlas 3 · User Comms ------------------------------------------------------------------------------------------


@hive_tool("delivery")
@_guard
def atlas_wave_comms_brief(wave_id: str, as_of: str = "2026-11-06") -> dict:
    """Return everything needed to personalise a wave's email sequence: dates, touchpoints, segments, sample users.

    Args:
        wave_id: Wave id from the baseline plan, e.g. 'W4'.
        as_of: Date (YYYY-MM-DD) used to mark touchpoints as sent / due / upcoming.

    Returns:
        Wave dates and departments, the standard touchpoint sequence with calendar dates and status, audience
        segments with recipient counts (Spanish speakers, mobile users, PST owners, holds, delegates...), named
        sample users for personalisation and the allowed merge fields.
    """
    w, state = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    rb = fixture("atlas_runbook")
    today = _date(as_of, DEMO_TODAY) or DEMO_TODAY
    cut = dt.date.fromisoformat(w["cutover_date"])
    tps = []
    for tp in rb["comms_touchpoints"]:
        d = cut + dt.timedelta(days=tp["offset_days"])
        tps.append({**tp, "date": d.isoformat(), "weekday": d.strftime("%a"),
                    "status": "sent" if d < today else "due today" if d == today else "upcoming"})
    f = w["flags"]
    counts = {"all": w["users"], "spanish": f["spanish_speakers"], "mobile": f["mobile_devices"],
              "oversized_mailbox": f["oversized_mailboxes"], "pst_owners": f["pst_files"],
              "delegates": f["delegates"], "lit_hold": f["lit_hold_users"],
              "shared_mailbox_members": f["shared_mailboxes"] * 6}
    segments = [{**s, "recipients": counts.get(s["id"], 0)} for s in rb["segments"] if counts.get(s["id"], 0)]
    dept_ids = {d["id"] for d in w["departments"]}
    sample = [u for u in fixture("atlas_tenant")["users_sample"] if u["dept"] in dept_ids]
    return ok(wave={k: w[k] for k in ("wave_id", "label", "cutover_date", "cutover_day", "delta_sync_start",
                                      "users", "departments")},
              wave_status=state.get("status"), touchpoints=tps, segments=segments, sample_users=sample,
              merge_fields=rb["merge_fields"], sender="Kestrel IT · Workspace Move <workspace-move@kestrelmfg.example>",
              support=rb["support"])


@hive_tool("delivery", kind="action")
@_guard
def atlas_schedule_emails(wave_id: str, touchpoint: str, segment: str, subject: str, body: str,
                          language: str = "en", send_at: str = "") -> dict:
    """Schedule one personalised email of a wave's sequence to a segment (simulated — nothing is sent).

    Args:
        wave_id: Wave id, e.g. 'W5'.
        touchpoint: Touchpoint id from atlas_wave_comms_brief (e.g. 'T-7', 'T-1', 'DAY1').
        segment: Segment id (e.g. 'all', 'spanish', 'mobile', 'pst_owners', 'lit_hold').
        subject: Subject line.
        body: Email body; may use merge fields in square brackets such as [first_name] or [cutover_date].
        language: 'en' or 'es'.
        send_at: ISO datetime; default is 08:00 on the touchpoint date.

    Returns:
        Schedule id, recipient count, resolved send time, unknown merge fields and a rendered preview for the
        first sample user (simulated).
    """
    w, _ = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    brief = atlas_wave_comms_brief(wave_id)
    tp = next((t for t in brief["touchpoints"] if t["id"].lower() == touchpoint.lower()), None)
    if not tp:
        return err(f"unknown touchpoint {touchpoint!r}", available=[t["id"] for t in brief["touchpoints"]])
    seg = next((s for s in brief["segments"] if s["id"] == segment), None)
    if not seg:
        return err(f"segment {segment!r} has no recipients in {w['wave_id']}",
                   available=[s["id"] for s in brief["segments"]])
    if not subject.strip() or len(body.strip()) < 40:
        return err("subject and a body of at least 40 characters are required")
    allowed = set(fixture("atlas_runbook")["merge_fields"])
    used = set(re.findall(r"\[([a-z_]+)\]", subject + " " + body))
    unknown = sorted(used - allowed)
    if unknown:
        return err("unknown merge fields", unknown=unknown, allowed=sorted(allowed))
    first = next((u for u in brief["sample_users"] if language != "es" or u["language"] == "es"),
                 brief["sample_users"][0] if brief["sample_users"] else None)
    preview = body
    if first:
        vals = {"first_name": first["name"].split()[0], "full_name": first["name"], "department": first["dept"],
                "manager": first["manager"], "cutover_date": w["cutover_date"], "wave_id": w["wave_id"],
                "mailbox_gb": str(first["mailbox_gb"]), "training_link": "https://learn.kestrelmfg.example/workspace",
                "support_link": "https://help.kestrelmfg.example/workspace", "new_email": first["email"]}
        preview = re.sub(r"\[([a-z_]+)\]", lambda m: vals.get(m.group(1), m.group(0)), body)
    when = send_at or f"{tp['date']}T08:00"
    return ok(schedule_id=f"COM-{w['wave_id']}-{tp['id']}-{_sid(segment, subject)}", wave_id=w["wave_id"],
              touchpoint=tp["id"], segment=segment, language=language, recipients=seg["recipients"],
              send_at=when, preview_for=first["name"] if first else None, preview=preview[:600],
              result="scheduled (simulated — no email sent)", simulated=True)


# --- Atlas 4 · Core Data Mover --------------------------------------------------------------------------------------


def _jobs(w: dict, state: dict) -> list[dict]:
    rb = fixture("atlas_runbook")
    th = rb["thresholds"]
    out = []
    for wl in ("mail", "drive", "shares"):
        j = state.get("jobs", {}).get(wl)
        items, gb = w["items"][wl], w["data_gb"][wl]
        if not j:
            out.append({"workload": wl, "state": "not started", "items_total": items, "gb_total": gb,
                        "pct_complete": 0.0})
            continue
        done = round(items * j["pct"])
        errs = j.get("errors", {})
        actionable = {k: v for k, v in errs.items() if rb["error_classes"][k]["category"] in ("transient", "fixable")}
        skipped = {k: v for k, v in errs.items() if k not in actionable}
        rate = round(sum(actionable.values()) / max(done, 1) * 100, 3)
        remaining_gb = round(gb * (1 - j["pct"]), 1)
        tp = j.get("throughput_gb_h") or 0
        eta_h = round(remaining_gb / tp, 1) if tp and remaining_gb else 0.0
        health = "red" if rate >= th["error_rate_red_pct"] else "amber" if rate >= th["error_rate_amber_pct"] \
            else "green"
        out.append({"workload": wl, "state": j.get("state", "running" if j["pct"] < 1 else "complete"),
                    "items_total": items, "items_done": done, "pct_complete": round(j["pct"] * 100, 1),
                    "gb_total": gb, "gb_done": round(gb * j["pct"], 1), "remaining_gb": remaining_gb,
                    "throughput_gb_h": tp, "eta_hours": eta_h,
                    "eta_at": (DEMO_NOW + dt.timedelta(hours=eta_h)).isoformat(timespec="minutes") if eta_h else None,
                    "actionable_errors": actionable, "policy_skips": skipped, "error_rate_pct": rate, "health": health,
                    "started_at": j.get("started_at"), "last_pass_completed": j.get("last_pass_completed"),
                    "retries_done": j.get("retries_done", 0)})
    return out


@hive_tool("delivery")
@_guard
def atlas_transfer_status(wave_id: str = "") -> dict:
    """Monitor bulk-transfer jobs (mail, OneDrive->Drive, file shares->Shared drives): progress, errors, ETA.

    Args:
        wave_id: Wave id (e.g. 'W5'). Empty returns a summary of every wave with active or finished jobs.

    Returns:
        Per-workload items and GB done, throughput, ETA, actionable errors by class (transient / fixable) versus
        policy skips, error rate with health (green / amber / red per runbook thresholds) and recommended actions.
    """
    rb = fixture("atlas_runbook")
    if not wave_id:
        rows = []
        for w in _baseline():
            _, st = _wave(w["wave_id"])
            jobs = _jobs(w, st)
            pct = sum(j["pct_complete"] * j["gb_total"] for j in jobs) / max(w["data_gb"]["total"], 1)
            rows.append({"wave_id": w["wave_id"], "label": w["label"], "status": st.get("status"),
                         "cutover_date": w["cutover_date"], "pct_complete_by_gb": round(pct, 1),
                         "worst_health": max((j.get("health", "green") for j in jobs),
                                             key=["green", "amber", "red"].index)})
        return ok(as_of=DEMO_NOW.isoformat(timespec="minutes"), waves=rows)
    w, st = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    jobs = _jobs(w, st)
    actions = []
    for j in jobs:
        for cls, n in (j.get("actionable_errors") or {}).items():
            ec = rb["error_classes"][cls]
            actions.append({"workload": j["workload"], "error_class": cls, "count": n, "category": ec["category"],
                            "action": ec["action"]})
    deadline = _dtm(w["delta_sync_start"])
    late = [j["workload"] for j in jobs if j.get("eta_at") and deadline and _dtm(j["eta_at"]) > deadline]
    return ok(as_of=DEMO_NOW.isoformat(timespec="minutes"), wave_id=w["wave_id"], label=w["label"],
              wave_status=st.get("status"), bulk_start=w["bulk_start"], delta_sync_start=w["delta_sync_start"],
              jobs=jobs, recommended_actions=actions, at_risk_of_missing_delta_window=late)


@hive_tool("delivery", kind="action")
@_guard
def atlas_retry_failed(wave_id: str, error_class: str = "transient", source_fixed: bool = False) -> dict:
    """Retry failed transfer items for a wave by error class (simulated job; expected recovery from the runbook).

    Args:
        wave_id: Wave id, e.g. 'W5'.
        error_class: 'transient' (all throttling/timeouts), or a class such as 'permission_denied_source',
            'path_too_long', 'throttled_429', 'network_timeout'.
        source_fixed: Set True only when the source problem was fixed (ACLs corrected, paths shortened); fixable
            classes recover only then.

    Returns:
        Retry job id, items retried and expected to recover per class, items still failing and next steps.
    """
    w, st = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    rb = fixture("atlas_runbook")["error_classes"]
    if error_class != "transient" and error_class not in rb:
        return err(f"unknown error class {error_class!r}", available=["transient", *rb])
    rows = []
    for wl, j in st.get("jobs", {}).items():
        for cls, n in j.get("errors", {}).items():
            ec = rb[cls]
            if (error_class == "transient" and ec["category"] != "transient") or \
                    (error_class != "transient" and cls != error_class):
                continue
            if ec["category"] in ("policy_skip", "permanent"):
                rows.append({"workload": wl, "error_class": cls, "retried": 0, "expected_recovered": 0,
                             "still_failing": n, "note": ec["action"]})
                continue
            rate = ec["success_rate"] if ec["category"] == "transient" or source_fixed else 0.0
            rec = round(n * rate)
            rows.append({"workload": wl, "error_class": cls, "retried": n, "expected_recovered": rec,
                         "still_failing": n - rec,
                         "note": ec["action"] if rate == 0 else f"expected success rate {int(rate * 100)}%"})
    if not rows:
        return err(f"no {error_class} errors to retry in {w['wave_id']}")
    return ok(job_id=f"RTY-{w['wave_id']}-{_sid(error_class, source_fixed)}", wave_id=w["wave_id"], retries=rows,
              totals={"retried": sum(r["retried"] for r in rows),
                      "expected_recovered": sum(r["expected_recovered"] for r in rows),
                      "still_failing": sum(r["still_failing"] for r in rows)},
              result="retry job queued (simulated)", simulated=True)


# --- Atlas 5 · Delta Sync ------------------------------------------------------------------------------------------


def _delta(w: dict, st: dict, start: dt.datetime) -> dict:
    p = fixture("atlas_runbook")["delta_profile"]
    jobs = st.get("jobs", {})
    passes = [_dtm(j["last_pass_completed"]) for j in jobs.values() if j.get("last_pass_completed")]
    last = min(passes) if passes else _dtm(w["bulk_start"] + "T00:00")
    hours = max(0.0, (start - last).total_seconds() / 3600)
    days = hours / 24
    users = w["users"] + st.get("deferred_in", 0)
    mail_items = round(users * p["mail_items_per_user_day"] * days)
    files = {wl: round(w["items"][wl] * p["file_change_rate_day"] * days) for wl in ("drive", "shares")}
    delta_gb = mail_items * p["avg_mail_kb"] / 1048576 + sum(files.values()) * p["avg_file_mb"] / 1024
    backlog_gb = sum(w["data_gb"][wl] * (1 - jobs.get(wl, {}).get("pct", 0)) for wl in ("mail", "drive", "shares"))
    scan_h = users * p["scan_minutes_per_mailbox"] / p["parallel_mailbox_scans"] / 60 + \
        (w["items"]["drive"] + w["items"]["shares"]) / p["file_scan_per_hour"]
    xfer_h = (delta_gb + backlog_gb) / p["delta_throughput_gb_h"]
    return {"last_bulk_pass": last.isoformat(timespec="minutes"), "delta_start": start.isoformat(timespec="minutes"),
            "hours_since_last_pass": round(hours, 1), "users_in_scope": users,
            "delta": {"mail_items": mail_items, "drive_files": files["drive"], "share_files": files["shares"],
                      "delta_gb": round(delta_gb, 1), "unfinished_bulk_gb": round(backlog_gb, 1)},
            "estimate_hours": {"scan": round(scan_h, 1), "transfer": round(xfer_h, 1),
                               "total": round(scan_h + xfer_h, 1)}}


@hive_tool("delivery")
@_guard
def atlas_delta_scan(wave_id: str, delta_start: str = "") -> dict:
    """Estimate the final incremental (delta) sync for a wave: new/changed items since the last bulk pass.

    Args:
        wave_id: Wave id, e.g. 'W4'.
        delta_start: ISO datetime when the delta sync starts; default is the wave's planned start (Friday 18:00).

    Returns:
        Last bulk pass time, new mail items and changed files by workload, delta GB plus unfinished bulk GB,
        estimated scan/transfer hours and whether it fits the 12-hour cutover window.
    """
    w, st = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    if st.get("status") in ("complete", "hypercare"):
        return err(f"{w['wave_id']} already cut over on {st.get('cutover_actual')}; nothing left to sync")
    if not st.get("jobs"):
        return err(f"{w['wave_id']} bulk transfer has not started (bulk start {w['bulk_start']})")
    start = _dtm(delta_start) if delta_start else _dtm(w["delta_sync_start"])
    if not start:
        return err("delta_start must be an ISO datetime, e.g. 2026-11-06T18:00")
    d = _delta(w, st, start)
    window = fixture("atlas_tenant")["constraints"]["cutover_window_hours"]
    d["fits_window"] = d["estimate_hours"]["total"] <= window
    d["window_hours"] = window
    d["projected_finish"] = (start + dt.timedelta(hours=d["estimate_hours"]["total"])).isoformat(timespec="minutes")
    return ok(wave_id=w["wave_id"], label=w["label"], cutover_date=w["cutover_date"], **d,
              deferred_users_included=st.get("deferred_in", 0))


@hive_tool("delivery")
@_guard
def atlas_cutover_readiness(wave_id: str) -> dict:
    """Evaluate go/no-go for a wave's cutover: bulk completion, error rate, delta fit and the cutover checklist.

    Args:
        wave_id: Wave id, e.g. 'W4'.

    Returns:
        Verdict (GO / CONDITIONAL GO / NO-GO), metric gates with thresholds, checklist items with status and
        owner, the critical items still open and the conditions to clear before the delta starts.
    """
    w, st = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    if st.get("status") in ("complete", "hypercare"):
        return err(f"{w['wave_id']} already cut over on {st.get('cutover_actual')}")
    rb = fixture("atlas_runbook")
    th = rb["thresholds"]
    jobs = _jobs(w, st)
    pct = sum(j["pct_complete"] * j["gb_total"] for j in jobs) / max(w["data_gb"]["total"], 1)
    rate = max((j.get("error_rate_pct", 0) for j in jobs), default=0)
    gates = [{"gate": "Bulk copy complete (by GB)", "value": round(pct, 1), "threshold": f">= {th['bulk_complete_pct_min']}%",
              "pass": pct >= th["bulk_complete_pct_min"]},
             {"gate": "Actionable error rate (worst workload)", "value": rate,
              "threshold": f"< {th['error_rate_red_pct']}%", "pass": rate < th["error_rate_red_pct"]}]
    if st.get("jobs"):
        d = _delta(w, st, _dtm(w["delta_sync_start"]))
        win = fixture("atlas_tenant")["constraints"]["cutover_window_hours"]
        gates.append({"gate": "Delta fits cutover window", "value": d["estimate_hours"]["total"],
                      "threshold": f"<= {win} h", "pass": d["estimate_hours"]["total"] <= win})
    overrides = fixture("atlas_run_state")["checklists"].get(w["wave_id"], {})
    items = []
    for c in rb["checklist"]:
        o = overrides.get(c["id"], {})
        crit = c["critical"] or (c.get("critical_if") == "lit_hold" and w["flags"]["lit_hold_users"] > 0)
        status = o.get("status", "pending")
        if c.get("critical_if") == "lit_hold" and not w["flags"]["lit_hold_users"]:
            status = "n/a"
        items.append({"id": c["id"], "when": c["when"], "item": c["item"], "owner": o.get("owner", c["owner_role"]),
                      "critical": crit, "status": status, "note": o.get("note", ""), "eta": o.get("eta", "")})
    open_crit = [i for i in items if i["critical"] and i["status"] not in ("done", "n/a") and i["id"] != "C09"]
    failed = [g for g in gates if not g["pass"]]
    if failed or len(open_crit) > 1 or any(not i["eta"] for i in open_crit):
        verdict = "NO-GO"
    elif open_crit:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "GO"
    return ok(wave_id=w["wave_id"], label=w["label"], cutover_date=w["cutover_date"],
              delta_sync_start=w["delta_sync_start"], verdict=verdict, gates=gates, checklist=items,
              open_critical=open_crit,
              conditions=[f"{i['id']} {i['item']} — {i['owner']} (ETA {i['eta'] or 'none'})" for i in open_crit],
              decision_meeting="C09 go/no-go call — this tool's verdict is the input, the approver decides")


@hive_tool("delivery", kind="action")
@_guard
def atlas_run_delta_sync(wave_id: str, approved_by: str) -> dict:
    """Start the final delta sync and cutover sequence for a wave after go/no-go approval (simulated).

    Args:
        wave_id: Wave id, e.g. 'W4'.
        approved_by: Name and role of the person who approved go/no-go (recorded in the cutover log).

    Returns:
        Sync job id, start and projected finish, the ordered cutover steps (delta, MX switch, verification) and
        rollback point (simulated — nothing runs).
    """
    if not approved_by.strip():
        return err("approved_by is required — the go/no-go approver must be recorded")
    ready = atlas_cutover_readiness(wave_id)
    if ready["status"] != "ok":
        return ready
    if ready["verdict"] == "NO-GO":
        return err("readiness verdict is NO-GO; clear the failed gates first", gates=ready["gates"],
                   open_critical=ready["open_critical"])
    scan = atlas_delta_scan(wave_id)
    start = _dtm(scan["delta_start"])
    finish = start + dt.timedelta(hours=scan["estimate_hours"]["total"])
    steps = [
        {"at": start.isoformat(timespec="minutes"), "step": "Final delta sync starts (mail, Drive, Shared drives)"},
        {"at": finish.isoformat(timespec="minutes"), "step": "Delta complete — verify counts on 10-user sample"},
        {"at": f"{ready['cutover_date']}T06:00", "step": "Switch MX to Google; enable Gmail for the wave's users"},
        {"at": f"{ready['cutover_date']}T07:00", "step": "Smoke tests: send/receive, calendar, shared drive access"},
        {"at": f"{ready['cutover_date']}T09:00", "step": "Rollback point expires — after this, fix forward"},
    ]
    return ok(job_id=f"DLT-{scan['wave_id']}-{_sid(approved_by)}", wave_id=scan["wave_id"], approved_by=approved_by,
              verdict_at_start=ready["verdict"], conditions=ready["conditions"], projected_finish=finish.isoformat(
                  timespec="minutes"), steps=steps, result="delta sync scheduled (simulated)", simulated=True)


# --- Atlas 6 · Post-Migration Validator ----------------------------------------------------------------------------


@hive_tool("delivery")
@_guard
def atlas_validate_wave(wave_id: str, check: str = "all") -> dict:
    """Validate a migrated wave: item counts source vs target, checksum sample and permission/delegation audit.

    Args:
        wave_id: A wave that has cut over (e.g. 'W3'; W0-W3 are migrated in the demo).
        check: 'all', 'counts', 'checksums' or 'permissions'.

    Returns:
        Per-workload source vs target counts with explained skips and unexplained variance (pass/fail against the
        0.1% tolerance), checksum sample results, ACL mapping and delegation audit, open discrepancies and an
        overall verdict (PASS / PASS WITH EXCEPTIONS / FAIL).
    """
    w, st = _wave(wave_id)
    if not w:
        return err(f"unknown wave {wave_id!r}", available=_wave_ids())
    if st.get("status") not in ("complete", "hypercare"):
        return err(f"{w['wave_id']} has not cut over yet (status {st.get('status')}, cutover {w['cutover_date']})",
                   hint="use atlas_transfer_status or atlas_cutover_readiness for waves in flight")
    if check not in ("all", "counts", "checksums", "permissions"):
        return err("check must be all, counts, checksums or permissions")
    th = fixture("atlas_runbook")["thresholds"]
    v = st["validation"]
    out: dict = {"wave_id": w["wave_id"], "label": w["label"], "cutover_actual": st.get("cutover_actual"),
                 "users_migrated": st.get("users_migrated"), "deferred_users": st.get("deferred", [])}
    fails, exceptions = [], []
    if check in ("all", "counts"):
        rows = []
        for wl in ("mail", "drive", "shares"):
            src = w["items"][wl]
            skipped = v["skipped"].get(wl, {})
            unexplained = v["unexplained"].get(wl, 0)
            target = src - sum(skipped.values()) - unexplained
            var = round(unexplained / max(src, 1) * 100, 4)
            passed = var <= th["unexplained_variance_max_pct"]
            rows.append({"workload": wl, "source_items": src, "target_items": target, "explained_skips": skipped,
                         "unexplained_missing": unexplained, "unexplained_variance_pct": var, "pass": passed})
            if not passed:
                fails.append(f"{wl} variance {var}%")
            elif unexplained:
                exceptions.append(f"{wl}: {unexplained} unexplained items (within tolerance)")
        out["counts"] = rows
    if check in ("all", "checksums"):
        cs = v["checksum"]
        pct = round(len(cs["mismatches"]) / max(cs["sampled"], 1) * 100, 3)
        passed = pct <= th["checksum_mismatch_max_pct"]
        out["checksums"] = {**cs, "mismatch_pct": pct, "threshold_pct": th["checksum_mismatch_max_pct"],
                            "pass": passed}
        if not passed:
            fails.append(f"checksum mismatches {pct}% over tolerance")
        elif cs["mismatches"]:
            exceptions.append(f"{len(cs['mismatches'])} checksum mismatch(es) within tolerance")
    if check in ("all", "permissions"):
        p = v["permissions"]
        deleg_pct = round(p["delegations_recreated"] / p["delegations_expected"] * 100, 1) \
            if p["delegations_expected"] else 100.0
        groups_pct = round(p["groups_created"] / p["groups_expected"] * 100, 1) if p["groups_expected"] else 100.0
        out["permissions"] = {**p, "acl_mapped_pct": round(p["acl_mapped"] / max(p["acl_source"], 1) * 100, 2),
                              "delegations_recreated_pct": deleg_pct, "groups_created_pct": groups_pct,
                              "pass": deleg_pct >= th["delegations_recreated_min_pct"] and groups_pct >= 100}
        if deleg_pct < th["delegations_recreated_min_pct"]:
            exceptions.append(f"delegations {p['delegations_recreated']}/{p['delegations_expected']} recreated")
        if p.get("external_shares_found"):
            exceptions.append(f"{p['external_shares_found']} external shares need owner review")
    out["open_discrepancies"] = v.get("open_discrepancies", [])
    out["verdict"] = "FAIL" if fails else "PASS WITH EXCEPTIONS" if (exceptions or out["open_discrepancies"]) \
        else "PASS"
    out["failures"], out["exceptions"] = fails, exceptions
    out["tolerances"] = {k: th[k] for k in ("unexplained_variance_max_pct", "checksum_mismatch_max_pct",
                                            "delegations_recreated_min_pct")}
    return ok(**out)


# --- Atlas 7 · Status Reporter -------------------------------------------------------------------------------------


@hive_tool("delivery")
@_guard
def atlas_status_snapshot(as_of: str = "2026-11-06", audience: str = "project_team") -> dict:
    """Daily status snapshot of the Kestrel migration: waves, users and data migrated, issues, next milestones, RAG.

    Args:
        as_of: Report date (YYYY-MM-DD).
        audience: 'project_team' (all open issues and actions) or 'client_exec' (headline view: Sev1/Sev2 only).

    Returns:
        Overall RAG with reasons, progress (users, waves, TB moved), per-wave status, open issues with owners and
        due dates, milestones in the next 7 days and hypercare ticket trends.
    """
    today = _date(as_of)
    if today is None:
        return err("as_of must be YYYY-MM-DD")
    rs = fixture("atlas_run_state")
    waves, migrated, moved_gb = [], 0, 0.0
    for w in _baseline():
        st = rs["waves"].get(w["wave_id"], {"status": "scheduled"})
        done = st.get("users_migrated", 0) if st["status"] in ("complete", "hypercare") else 0
        migrated += done
        moved = sum(w["data_gb"][wl] * st.get("jobs", {}).get(wl, {}).get("pct", 0) for wl in ("mail", "drive", "shares"))
        moved_gb += moved
        waves.append({"wave_id": w["wave_id"], "label": w["label"], "cutover_date": w["cutover_date"],
                      "status": st["status"], "users_planned": w["users"], "users_migrated": done,
                      "data_moved_pct": round(moved / max(w["data_gb"]["total"], 1) * 100, 1)})
    total_users = sum(w["users"] for w in _baseline())
    total_gb = sum(w["data_gb"]["total"] for w in _baseline())
    sev_rank = {"Sev1": 0, "Sev2": 1, "Sev3": 2, "Sev4": 3}
    issues = sorted([i for i in rs["issues"] if i["status"] != "closed"],
                    key=lambda i: (sev_rank[i["severity"]], i["due"]))
    if audience == "client_exec":
        issues = [i for i in issues if i["severity"] in ("Sev1", "Sev2")]
    horizon = today + dt.timedelta(days=7)
    miles = []
    for w in _baseline():
        for name, d in (("Bulk transfer starts", w["bulk_start"]), ("Delta sync starts", w["delta_sync_start"][:10]),
                        ("Cutover", w["cutover_date"])):
            dd = dt.date.fromisoformat(d)
            if today <= dd <= horizon:
                miles.append({"date": d, "wave_id": w["wave_id"], "milestone": name})
    miles.sort(key=lambda m: m["date"])
    reasons = []
    open_all = [i for i in rs["issues"] if i["status"] != "closed"]
    if any(i["severity"] == "Sev1" for i in open_all):
        rag = "red"
        reasons.append("open Sev1 issue")
    else:
        near = [i for i in open_all if i["severity"] == "Sev2"
                and (dt.date.fromisoformat(i["due"]) - today).days <= 14]
        rag = "amber" if near else "green"
        reasons += [f"{i['id']} ({i['wave']}) {i['title']}" for i in near]
    return ok(project=fixture("atlas_tenant")["tenant"]["project_id"], as_of=today.isoformat(), audience=audience,
              rag=rag, rag_reasons=reasons,
              progress={"users_migrated": migrated, "users_total": total_users,
                        "users_pct": round(migrated / total_users * 100, 1),
                        "waves_complete": sum(1 for w in waves if w["status"] in ("complete", "hypercare")),
                        "waves_total": len(waves), "data_moved_tb": round(moved_gb / 1000, 2),
                        "data_total_tb": round(total_gb / 1000, 2)},
              waves=waves, open_issues=issues, next_7_days=miles, hypercare=rs["hypercare"])


# =====================================================================================================================
# DELIVERY ENGINE — SOW Builder, LATAM SOW, Scope Creep
# =====================================================================================================================


@hive_tool("delivery")
@_guard
def dlv_estimate_effort(deliverables: list[dict]) -> dict:
    """Estimate effort by role for SOW deliverables using the reference estimation model.

    Args:
        deliverables: List of {"type": str, "quantity": number, "complexity": "low"|"medium"|"high", "name": str}.
            quantity is in the type's natural unit. Types: discovery_assessment (engagements),
            workspace_migration (users), file_share_migration (TB), identity_sso (integrations),
            change_management (users), training_session (sessions), gemini_rollout (seats),
            landing_zone (environments), data_pipeline (pipelines), dashboard (dashboards), ml_model (models),
            ai_agent (agents), integration_api (integrations), hypercare (weeks).

    Returns:
        Hours by role per deliverable, governance (project management, engagement director) added as a percentage,
        totals by role ready for dlv_price_sow, unknown types and the model assumptions.
    """
    m = fixture("dlv_estimation_model")
    types, mult = m["deliverable_types"], m["complexity_multipliers"]
    if not deliverables:
        return err("deliverables must not be empty", types=sorted(types))
    lines, unknown, totals = [], [], {}
    for dl in deliverables:
        t = _key(dl.get("type", ""))
        if t not in types:
            unknown.append(dl.get("type"))
            continue
        spec = types[t]
        try:
            qty = float(dl.get("quantity", 1) or 1)
        except (TypeError, ValueError):
            return err(f"quantity must be a number: {dl}")
        cx = str(dl.get("complexity", "medium")).lower()
        f = mult.get(cx, 1.0)
        units = qty / spec["unit_divisor"]
        hours = {}
        for role in set(spec.get("base", {})) | set(spec.get("per_unit", {})):
            h = (spec.get("base", {}).get(role, 0) + spec.get("per_unit", {}).get(role, 0) * units) * f
            hours[role] = round(h)
            totals[role] = totals.get(role, 0) + round(h)
        lines.append({"name": dl.get("name") or spec["label"], "type": t, "quantity": qty, "unit": spec["unit"],
                      "complexity": cx, "hours_by_role": dict(sorted(hours.items())), "hours": sum(hours.values())})
    if not lines:
        return err("no known deliverable types", unknown=unknown, types=sorted(types))
    delivery = sum(totals.values())
    gov = {r: round(delivery * p) for r, p in m["governance_pct"].items()}
    for r, h in gov.items():
        totals[r] = totals.get(r, 0) + h
    role_hours = [{"role": r, "hours": h} for r, h in sorted(totals.items(), key=lambda x: -x[1])]
    worst = max((ln["complexity"] for ln in lines), key=lambda c: list(mult).index(c) if c in mult else 1)
    return ok(lines=lines, governance_hours=gov, role_hours=role_hours, total_hours=sum(totals.values()),
              delivery_hours=delivery, overall_complexity=worst,
              indicative_duration_weeks=math.ceil(sum(totals.values()) / m["team_hours_per_week"]),
              unknown_types=unknown, assumptions=m["assumptions"])


def _rates(region: str) -> tuple[dict, dict]:
    rc = fixture("dlv_rate_card")
    rates, costs = {}, {}
    for role, r in rc["roles"].items():
        if region == "latam_nearshore" or (region == "blended" and role not in rc["blended_onshore_roles"]):
            rates[role], costs[role] = r["latam_nearshore"], r["cost_latam"]
        else:
            rates[role], costs[role] = r["us_onshore"], r["cost_us"]
    return rates, costs


def _role(name: str, roles: dict) -> str | None:
    k = _key(name)
    if k in roles:
        return k
    return next((r for r, v in roles.items() if _key(v["title"]) == k or k in _key(v["title"])), None)


@hive_tool("delivery")
@_guard
def dlv_price_sow(role_hours: list[dict], pricing_model: str = "fixed", delivery_region: str = "us_onshore",
                  discount_pct: float = 0.0, risk_level: str = "medium") -> dict:
    """Price an estimate with the illustrative services rate card: T&M or fixed fee, margin, discount approvals.

    Args:
        role_hours: List of {"role": str, "hours": number} (e.g. the role_hours from dlv_estimate_effort).
        pricing_model: 'fixed' (fixed fee incl. risk premium) or 'tm' (time & materials with a not-to-exceed cap).
        delivery_region: 'us_onshore', 'latam_nearshore' or 'blended' (leadership onshore, delivery nearshore).
        discount_pct: Commercial discount on list rates (0-30).
        risk_level: 'low', 'medium' or 'high' — sets the fixed-fee risk premium.

    Returns:
        Line items (role, hours, rate, amount), list total, discount, price (fixed fee or T&M estimate + NTE),
        blended rate, delivery cost, gross margin vs target/floor, required approver and warnings. USD.
    """
    rc = fixture("dlv_rate_card")
    pol = rc["policy"]
    if pricing_model not in ("fixed", "tm"):
        return err("pricing_model must be 'fixed' or 'tm'")
    if delivery_region not in ("us_onshore", "latam_nearshore", "blended"):
        return err("delivery_region must be us_onshore, latam_nearshore or blended")
    if not 0 <= discount_pct <= 30:
        return err("discount_pct must be between 0 and 30")
    rates, costs = _rates(delivery_region)
    lines, unknown = [], []
    for rh in role_hours:
        r = _role(str(rh.get("role", "")), rc["roles"])
        try:
            h = float(rh.get("hours", 0))
        except (TypeError, ValueError):
            return err(f"hours must be a number: {rh}")
        if not r:
            unknown.append(rh.get("role"))
            continue
        lines.append({"role": r, "title": rc["roles"][r]["title"], "hours": h, "rate_usd": rates[r],
                      "amount_usd": round(h * rates[r], 2), "cost_usd": round(h * costs[r], 2)})
    if not lines:
        return err("no known roles", unknown=unknown, roles=sorted(rc["roles"]))
    hours = sum(ln["hours"] for ln in lines)
    list_total = round(sum(ln["amount_usd"] for ln in lines), 2)
    cost = round(sum(ln["cost_usd"] for ln in lines), 2)
    discount = round(list_total * discount_pct / 100, 2)
    net = list_total - discount
    out = {"pricing_model": pricing_model, "delivery_region": delivery_region, "currency": "USD",
           "rate_card": rc["name"], "lines": [{k: v for k, v in ln.items() if k != "cost_usd"} for ln in lines],
           "total_hours": hours, "list_total_usd": list_total, "discount_pct": discount_pct, "discount_usd": discount}
    if pricing_model == "fixed":
        prem = pol["fixed_risk_premium_pct"].get(risk_level, pol["fixed_risk_premium_pct"]["medium"])
        price = round(net * (1 + prem / 100), -2)
        out.update(risk_level=risk_level, risk_premium_pct=prem, fixed_fee_usd=price)
    else:
        price = round(net, 2)
        out.update(tm_estimate_usd=price, not_to_exceed_usd=round(net * (1 + pol["tm_nte_buffer_pct"] / 100), -2),
                   burn_alert_at_pct=pol["tm_burn_alert_pct"])
    margin = round((price - cost) / price * 100, 1) if price else 0.0
    approver = next(a["approver"] for a in pol["discount_approvals"] if discount_pct <= a["max_pct"])
    warnings = []
    if margin < pol["floor_margin_pct"]:
        warnings.append(f"gross margin {margin}% below the {pol['floor_margin_pct']}% floor — needs VP Services "
                        "and Finance exception")
        approver = "VP Services + Finance (margin exception)"
    elif margin < pol["target_margin_pct"]:
        warnings.append(f"gross margin {margin}% below the {pol['target_margin_pct']}% target")
    if unknown:
        warnings.append(f"unpriced roles: {unknown}")
    out.update(blended_rate_usd=round(price / hours, 2) if hours else 0, delivery_cost_usd=cost,
               gross_margin_pct=margin, target_margin_pct=pol["target_margin_pct"],
               floor_margin_pct=pol["floor_margin_pct"], approval_required=approver, warnings=warnings,
               disclaimer="Illustrative rate card for demos (effective " + rc["effective"] + ").")
    return ok(**out)


@hive_tool("delivery")
@_guard
def dlv_payment_schedule(total_price_usd: float, pricing_model: str, milestones: list[dict]) -> dict:
    """Build the SOW payment schedule from milestones following the billing policy.

    Args:
        total_price_usd: Fixed fee, or the T&M estimate for 'tm'.
        pricing_model: 'fixed' or 'tm'.
        milestones: List of {"name": str, "date": "YYYY-MM-DD", "weight_pct": number (optional)} in delivery order
            (dates e.g. from critical_path).

    Returns:
        Fixed: mobilisation on signature, milestone payments by weight and the final-acceptance holdback, each with
        amount and invoice date. T&M: monthly invoicing in arrears with the burn-alert rule. Plus policy notes.
    """
    pol = fixture("dlv_rate_card")["policy"]["billing"]
    if total_price_usd <= 0 or not milestones:
        return err("total_price_usd must be > 0 and milestones must not be empty")
    dates = [_date(m.get("date", "")) for m in milestones]
    if None in dates:
        return err("every milestone needs a date as YYYY-MM-DD")
    if dates != sorted(dates):
        return err("milestone dates must be in ascending order")
    if pricing_model == "tm":
        first, last = dates[0], dates[-1]
        months = max(1, (last.year - first.year) * 12 + last.month - first.month + 1)
        rows = []
        for i in range(months):
            y, mth = first.year + (first.month - 1 + i) // 12, (first.month - 1 + i) % 12 + 1
            rows.append({"invoice": f"{y}-{mth:02d}", "basis": "hours worked in month, billed in arrears",
                         "indicative_usd": round(total_price_usd / months, 2)})
        return ok(pricing_model="tm", schedule=rows, terms=pol["terms"],
                  notes=[pol["tm_note"], f"Client notified at {fixture('dlv_rate_card')['policy']['tm_burn_alert_pct']}% "
                                         "of the not-to-exceed amount."])
    mob, hold = pol["mobilisation_pct"], pol["holdback_pct"]
    weights = [float(m.get("weight_pct") or 0) for m in milestones]
    if not any(weights):
        weights = [1.0] * len(milestones)
    wsum = sum(weights)
    pool = 100 - mob - hold
    rows = [{"payment": "Mobilisation (on signature)", "date": "on signature", "pct": mob,
             "amount_usd": round(total_price_usd * mob / 100, 2)}]
    for m, wgt in zip(milestones, weights):
        pct = round(pool * wgt / wsum, 2)
        rows.append({"payment": f"Milestone: {m['name']}", "date": m["date"], "pct": pct,
                     "amount_usd": round(total_price_usd * pct / 100, 2)})
    rows.append({"payment": "Final acceptance holdback", "date": _add_business_days(dates[-1], 10).isoformat(),
                 "pct": hold, "amount_usd": round(total_price_usd * hold / 100, 2)})
    drift = round(total_price_usd - sum(r["amount_usd"] for r in rows), 2)
    rows[-1]["amount_usd"] = round(rows[-1]["amount_usd"] + drift, 2)
    return ok(pricing_model="fixed", schedule=rows, total_usd=total_price_usd,
              pct_total=round(sum(r["pct"] for r in rows), 2), terms=pol["terms"],
              notes=["Milestone invoices are issued on milestone acceptance (see acceptance clause CL-ACC-01).",
                     f"Holdback released {pol['holdback_release']}."])


@hive_tool("delivery")
@_guard
def dlv_sow_clause_library(topic: str = "", language: str = "en", country: str = "") -> dict:
    """Return approved SOW clauses (acceptance, change control, assumptions, payment, warranty...) in EN/ES/PT.

    Args:
        topic: Optional topic filter, e.g. 'acceptance', 'change_control', 'assumptions', 'out_of_scope',
            'payment_fixed', 'payment_tm', 'client_responsibilities', 'governance', 'warranty', 'data_protection'.
        language: 'en', 'es' or 'pt'.
        country: Optional LATAM country code (MX, CO, BR, CL, PE, SV) to add country-specific clauses
            (governing law, e-invoicing, withholding gross-up, data protection).

    Returns:
        Clause id, topic, title and approved text in the requested language, plus the available topics.
    """
    lib = fixture("dlv_clause_library")
    lang = language.lower()[:2]
    if lang not in ("en", "es", "pt"):
        return err("language must be en, es or pt")
    rows = [c for c in lib["clauses"] if not topic or c["topic"] == topic]
    out = [{"id": c["id"], "topic": c["topic"], "title": c["title"].get(lang, c["title"]["en"]),
            "text": c["text"].get(lang, c["text"]["en"])} for c in rows]
    cc: list = []   # US/CA/UK engagements use the base clauses only
    if country and country.upper() not in ("US", "USA", "CA", "UK", "GB", ""):
        cc = lib["country_clauses"].get(country.upper())
        if cc is None:
            return err(f"no country clauses for {country!r}", available=sorted(lib["country_clauses"]))
        cc = [c for c in cc if not topic or c["topic"] == topic]
    if not out and not cc:
        return err(f"no clauses for topic {topic!r}", topics=sorted({c["topic"] for c in lib["clauses"]}))
    return ok(language=lang, clauses=out, country_clauses=cc, topics=sorted({c["topic"] for c in lib["clauses"]}),
              note="Approved clause text — do not edit wording without Legal review (see SOW standards).")


_SECTIONS = {
    "en": {"scope": r"(?<!out of )\bscope\b|objectives", "deliverables": r"deliverables",
           "assumptions": r"assumptions", "out_of_scope": r"out of scope|exclusions",
           "client_responsibilities": r"client responsibilities|customer responsibilities",
           "milestones": r"milestones|timeline|schedule", "pricing": r"pricing|fees|investment|commercials",
           "acceptance": r"acceptance", "change_control": r"change control|change request|change management process",
           "governance": r"governance"},
    "es": {"scope": r"(?<!fuera de )\balcance|objetivos", "deliverables": r"entregables",
           "assumptions": r"supuestos|premisas", "out_of_scope": r"fuera de alcance|exclusiones",
           "client_responsibilities": r"responsabilidades del cliente", "milestones": r"hitos|cronograma|calendario",
           "pricing": r"precio|honorarios|inversi[oó]n|propuesta econ[oó]mica", "acceptance": r"aceptaci[oó]n",
           "change_control": r"control de cambios", "governance": r"gobierno|gobernanza"},
    "pt": {"scope": r"(?<!fora do )\bescopo|objetivos", "deliverables": r"entreg[aá]veis",
           "assumptions": r"premissas", "out_of_scope": r"fora do escopo|exclus[oõ]es",
           "client_responsibilities": r"responsabilidades d[oa] (cliente|contratante)",
           "milestones": r"marcos|cronograma", "pricing": r"pre[cç]o|honor[aá]rios|investimento",
           "acceptance": r"aceite|aceita[cç][aã]o", "change_control": r"controle de mudan[cç]as|gest[aã]o de mudan[cç]as",
           "governance": r"governan[cç]a"},
}
_VAGUE = {
    "en": [r"\betc\b\.?", r"as needed", r"as required", r"best effort", r"unlimited", r"any and all", r"and so on",
           r"ongoing support", r"seamless", r"if time permits", r"where possible", r"all data\b"],
    "es": [r"\betc\b\.?", r"seg[uú]n sea necesario", r"ilimitad[oa]s?", r"mejor esfuerzo", r"entre otros",
           r"todo tipo de", r"sin l[ií]mite", r"soporte continuo"],
    "pt": [r"\betc\b\.?", r"conforme necess[aá]rio", r"ilimitad[oa]s?", r"melhor esfor[cç]o", r"entre outros",
           r"todo tipo de", r"sem limite", r"suporte cont[ií]nuo"],
}
_PLACEHOLDER = r"\bTBD\b|\bTBC\b|\bTODO\b|\bXXX+\b|\[insert[^\]]*\]|lorem ipsum|\$X\b|<client>|<cliente>"


def _headings(text: str) -> list[tuple[int, int, str]]:
    """(line index, level, lowered text) of section headings. Markdown '#' headings win when present; otherwise
    short bold or numbered lines are treated as headings."""
    lines = text.splitlines()
    md = [(i, len(ln.strip()) - len(ln.strip().lstrip("#")), ln.strip().lower()) for i, ln in enumerate(lines)
          if ln.strip().startswith("#")]
    if md:
        return md
    out = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if len(s) < 90 and (s.startswith("**") or re.match(r"^\d+(\.\d+)*[.)]?\s+\S", s)):
            out.append((i, 1, s.lower()))
    return out


def _section_text(text: str, pattern: str) -> str:
    """Body of the first section whose heading matches `pattern`, up to the next heading of the same or higher level."""
    lines = text.splitlines()
    heads = _headings(text)
    for n, (i, lvl, h) in enumerate(heads):
        if re.search(pattern, h):
            end = next((j for j, l2, _ in heads[n + 1:] if l2 <= lvl), len(lines))
            return "\n".join(lines[i + 1:end])
    return ""


_PAY_ROW = re.compile(r"signature|mobili[sz]a|milestone|hold-?back|final acceptance|firma|movilizaci|hito|"
                      r"retenci[oó]n final|aceptaci[oó]n final|assinatura|marco|reten[cç][aã]o|aceite final", re.I)


@hive_tool("delivery")
@_guard
def dlv_sow_quality_check(sow_text: str, language: str = "auto") -> dict:
    """QA a SOW draft against the SOW standards: required sections, vague terms, placeholders, acceptance, payments.

    Args:
        sow_text: The full SOW draft (markdown) or the key of a sample document.
        language: 'en', 'es', 'pt' or 'auto' (detected from section headings).

    Returns:
        Score (0-100), verdict (ready / revise), missing sections, vague terms with context, placeholders,
        deliverables (D1, D2...) without an acceptance criterion and payment-percentage check, each with a fix.
    """
    text = _text(sow_text)
    if len(text) < 200:
        return err("SOW text too short to check (min 200 characters)")
    lang = language.lower()[:2]
    if lang not in _SECTIONS:
        heads = " ".join(h for _, _, h in _headings(text))
        lang = max(_SECTIONS, key=lambda lg: sum(bool(re.search(p, heads)) for p in _SECTIONS[lg].values()))
    heads = " | ".join(h for _, _, h in _headings(text))
    missing = [s for s, p in _SECTIONS[lang].items() if not re.search(p, heads)]
    vague = []
    for p in _VAGUE[lang]:
        for m in list(re.finditer(p, text, re.I))[:2]:
            vague.append({"term": m.group(0), "context": text[max(0, m.start() - 50):m.end() + 30].replace("\n", " ")})
    placeholders = sorted({m.group(0) for m in re.finditer(_PLACEHOLDER, text, re.I)})
    deliv = _section_text(text, _SECTIONS[lang]["deliverables"])
    d_ids = sorted(set(re.findall(r"\bD(\d{1,2})\b", deliv or text)), key=int)
    acc = _section_text(text, _SECTIONS[lang]["acceptance"])
    in_table = any(ln.strip().startswith("|") and re.search(r"acceptance|aceptaci|aceite", ln, re.I)
                   for ln in deliv.splitlines())
    no_acc = [] if in_table else [f"D{i}" for i in d_ids if not re.search(rf"\bD{i}\b", acc)]
    rows = [ln for ln in text.splitlines() if ln.strip().startswith("|") and _PAY_ROW.search(ln)
            and not re.search(r"\btotal\b", ln, re.I) and re.search(r"\d\s?%", ln)]
    pcts = [float(re.search(r"(\d{1,3}(?:[.,]\d+)?)\s?%", r).group(1).replace(",", ".")) for r in rows]
    pay_issue = None
    if pcts and abs(sum(pcts) - 100) > 0.5:
        pay_issue = f"payment schedule rows sum to {round(sum(pcts), 2)}% (must be 100%)"
    score = 100 - 12 * len(missing) - min(24, 3 * len(vague)) - min(20, 5 * len(placeholders)) \
        - min(24, 8 * len(no_acc)) - (10 if pay_issue else 0)
    score = max(0, score)
    fixes = [f"Add section: {s.replace('_', ' ')}" for s in missing] + \
            [f"Replace vague term '{v['term']}' with a measurable commitment" for v in vague[:5]] + \
            [f"Resolve placeholder {p}" for p in placeholders] + \
            [f"Add an acceptance criterion for {d}" for d in no_acc] + ([pay_issue] if pay_issue else [])
    return ok(language=lang, score=score,
              verdict="ready for review" if score >= 80 and not missing and not placeholders else "revise",
              missing_sections=missing, vague_terms=vague, placeholders=placeholders, deliverables_found=len(d_ids),
              deliverables_without_acceptance=no_acc, payment_check=pay_issue or ("ok — rows sum to 100%" if pcts else "no payment table found"), fixes=fixes)


@hive_tool("delivery")
@_guard
def dlv_latam_fiscal_profile(country: str, amount_usd: float = 0.0, billing: str = "cross_border") -> dict:
    """Illustrative fiscal profile for a LATAM SOW: currency, planning FX, VAT, withholding and gross-up impact.

    Args:
        country: ISO code: MX, CO, BR, CL, PE or SV.
        amount_usd: Optional SOW value in USD to convert and to compute VAT / withholding impact.
        billing: 'cross_border' (the provider's US entity invoices in USD; client may withhold tax) or 'local_partner'
            (local reseller invoices in local currency with VAT).

    Returns:
        Currency, planning FX rate, local amount, VAT name/rate, illustrative withholding rate, net received,
        gross-up needed to receive the full fee, e-invoicing system, data-protection law, contract-language and
        payment-term norms. Illustrative planning values only — validate with local tax counsel.
    """
    data = fixture("dlv_latam_fiscal")
    p = data["countries"].get(country.upper())
    if not p:
        return err(f"unknown country {country!r}", available=sorted(data["countries"]))
    if billing not in ("cross_border", "local_partner"):
        return err("billing must be cross_border or local_partner")
    out = {"country": country.upper(), **p, "fx_as_of": data["fx_as_of"], "disclaimer": data["disclaimer"]}
    if amount_usd > 0:
        fx = p["planning_fx_per_usd"]
        calc = {"amount_usd": amount_usd, "amount_local": round(amount_usd * fx, 2), "currency": p["currency"],
                "billing": billing}
        if billing == "cross_border":
            wht = p["withholding_planning_pct"] / 100
            calc.update(withholding_usd=round(amount_usd * wht, 2), net_received_usd=round(amount_usd * (1 - wht), 2),
                        gross_up_invoice_usd=round(amount_usd / (1 - wht), 2) if wht < 1 else None,
                        vat_note=p["vat"]["cross_border_note"])
        else:
            vat = p["vat"]["rate_pct"] / 100
            local = amount_usd * fx
            calc.update(vat_local=round(local * vat, 2), total_with_vat_local=round(local * (1 + vat), 2),
                        fx_risk_note="Local-currency price fixed at the planning rate; add an FX adjustment clause "
                                     "if the rate moves more than 5%.")
        out["calculation"] = calc
    return ok(**out)


_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
             "ten": 10, "a dozen": 12}


def _quantity(text: str, unit_words: list[str]) -> float | None:
    """Number attached to a unit word ('150 contractors', 'two sessions'), else the first number in the text."""
    num = r"(\d[\d,]*(?:\.\d+)?|" + "|".join(_WORD_NUM) + r")"
    for u in unit_words:
        m = re.search(num + r"\s+(?:[a-z-]+\s+){0,2}?" + re.escape(u.lower()), text)
        if m:
            g = m.group(1)
            return float(_WORD_NUM[g]) if g in _WORD_NUM else float(g.replace(",", ""))
    m = re.search(r"\b\d[\d,]*\b", text)
    return float(m.group(0).replace(",", "")) if m else None


@hive_tool("delivery")
@_guard
def dlv_check_scope(sow_id: str, requests: list[str]) -> dict:
    """Check requested changes against a signed SOW: in scope, out of scope, over a contractual cap, or ambiguous.

    Args:
        sow_id: Signed SOW id, e.g. 'SOW-2026-0412' (Kestrel migration) or 'SOW-2026-0388' (Bluestem analytics).
        requests: One sentence per client ask (from an email, meeting notes or transcript). Empty returns the SOW
            summary only.

    Returns:
        SOW summary (client, model, value, dates, burn) and, per request, the classification with the matching
        clause (IS-/OOS-/CAP- id), the reference effort for out-of-scope items and a recommended next step.
    """
    sows = fixture("dlv_signed_sows")
    s = sows.get(sow_id.strip().upper())
    if not s:
        return err(f"unknown SOW {sow_id!r}", available=sorted(sows))
    summary = {k: s[k] for k in ("client", "title", "pricing_model", "value_usd", "signed", "start", "end",
                                 "hours_budget", "hours_burned")}
    summary["burn_pct"] = round(s["hours_burned"] / s["hours_budget"] * 100, 1)
    summary["change_orders_to_date"] = s.get("change_orders", [])
    results = []
    for r in requests or []:
        low = r.lower()
        hit = next((o for o in s["out_of_scope"] if any(k in low for k in o["keywords"])), None)
        if hit:
            results.append({"request": r, "classification": "out_of_scope", "clause": hit["id"], "clause_text": hit["item"],
                            "reference_effort": hit.get("reference_effort", []),
                            "schedule_impact_days": hit.get("schedule_impact_days", 0),
                            "next_step": "Draft a change order (dlv_draft_change_order with oos_ref)"})
            continue
        cap = next((c for c in s["caps"] if any(k in low for k in c["keywords"])), None)
        if cap:
            results.append({"request": r, "classification": "exceeds_cap", "clause": cap["id"], "clause_text": cap["item"],
                            "quantity_detected": _quantity(low, cap.get("unit_words", [cap["unit"]])),
                            "cap_unit": cap["unit"],
                            "reference_effort_per_unit": cap.get("effort_per_unit", []),
                            "next_step": "Draft a change order (oos_ref = cap id, quantity = extra units)"})
            continue
        ins = next((i for i in s["in_scope"] if any(k in low for k in i["keywords"])), None)
        if ins:
            results.append({"request": r, "classification": "in_scope", "clause": ins["id"], "clause_text": ins["item"],
                            "next_step": "Plan within the current SOW; no change order"})
        else:
            results.append({"request": r, "classification": "ambiguous", "clause": None,
                            "next_step": "PM judgement: clarify with the client and log in the change register"})
    counts = {k: sum(1 for x in results if x["classification"] == k)
              for k in ("in_scope", "out_of_scope", "exceeds_cap", "ambiguous")}
    return ok(sow_id=sow_id.upper(), summary=summary, results=results, counts=counts,
              out_of_scope_catalogue=[{"id": o["id"], "item": o["item"]} for o in s["out_of_scope"]],
              caps=[{"id": c["id"], "item": c["item"]} for c in s["caps"]])


@hive_tool("delivery", kind="action")
@_guard
def dlv_draft_change_order(sow_id: str, items: list[dict], requested_by: str = "") -> dict:
    """Draft a change order against a signed SOW, priced at the SOW's contracted rates (simulated filing).

    Args:
        sow_id: Signed SOW id, e.g. 'SOW-2026-0412'.
        items: List of {"title": str, "oos_ref": "OOS-01" or "CAP-01" (uses the SOW's reference effort),
            "quantity": number (extra units for a CAP item), "role_hours": [{"role": str, "hours": number}]
            (custom effort instead of oos_ref), "schedule_impact_days": int}.
        requested_by: Client requester (name, role).

    Returns:
        Change-order id, priced lines, CO total, contingency, updated contract value, schedule impact, required
        provider-side approver and client signature status (draft filed — simulated).
    """
    sows = fixture("dlv_signed_sows")
    s = sows.get(sow_id.strip().upper())
    if not s:
        return err(f"unknown SOW {sow_id!r}", available=sorted(sows))
    if not items:
        return err("items must not be empty")
    rates = s["contracted_rates"]
    lines, days = [], 0
    for it in items:
        ref = str(it.get("oos_ref", "")).upper()
        effort = it.get("role_hours") or []
        title = str(it.get("title", ""))
        if not ref and not effort:   # infer the clause from the title (an id in it, else the SOW's keywords)
            m = re.search(r"\b(?:OOS|CAP)-\d+\b", title.upper())
            low = f" {title.lower()} "
            hit = next((x for x in [*s["out_of_scope"], *s["caps"]] if any(k in low for k in x["keywords"])), None)
            ref = m.group(0) if m else (hit["id"] if hit else "")
            if ref.startswith("CAP-") and not it.get("quantity"):
                c = next((x for x in s["caps"] if x["id"] == ref), None)
                it = {**it, "quantity": _quantity(low, c.get("unit_words", [c["unit"]])) if c else None}
        if ref:
            o = next((x for x in s["out_of_scope"] if x["id"] == ref), None)
            c = next((x for x in s["caps"] if x["id"] == ref), None)
            if o:
                effort = o.get("reference_effort", [])
                days += int(it.get("schedule_impact_days", o.get("schedule_impact_days", 0)) or 0)
            elif c:
                qty = float(it.get("quantity") or 0)
                if qty <= 0:
                    return err(f"{ref} is a cap — pass quantity (extra {c['unit']})")
                units = qty / c["unit_divisor"]
                effort = [{"role": e["role"], "hours": round(e["hours"] * units)} for e in c["effort_per_unit"]]
                days += int(it.get("schedule_impact_days", 0) or 0)
            else:
                return err(f"unknown reference {ref!r} for {sow_id}")
        else:
            days += int(it.get("schedule_impact_days", 0) or 0)
        if not effort:
            return err(f"item {it.get('title')!r} needs oos_ref or role_hours")
        for e in effort:
            role = _key(e.get("role", ""))
            if role not in rates:
                return err(f"role {e.get('role')!r} has no contracted rate in {sow_id}", roles=sorted(rates))
            h = float(e.get("hours", 0))
            lines.append({"item": it.get("title") or ref, "ref": ref or "custom", "role": role, "hours": h,
                          "rate_usd": rates[role], "amount_usd": round(h * rates[role], 2)})
    subtotal = round(sum(ln["amount_usd"] for ln in lines), 2)
    rc = fixture("dlv_rate_card")
    pol = rc["policy"]["change_orders"]
    contingency = round(subtotal * pol["fixed_contingency_pct"] / 100, 2) if s["pricing_model"] == "fixed" else 0.0
    total = round(subtotal + contingency, 2)
    approver = next(a["approver"] for a in pol["approvals"] if total <= a["max_usd"])
    co_id = f"CO-{s['id_short']}-{len(s.get('change_orders', [])) + 1:02d}"
    return ok(change_order_id=co_id, sow_id=sow_id.upper(), client=s["client"], requested_by=requested_by,
              pricing_model=s["pricing_model"], lines=lines, hours=sum(ln["hours"] for ln in lines),
              subtotal_usd=subtotal, contingency_usd=contingency, total_usd=total,
              contract_value_before_usd=s["value_usd"], contract_value_after_usd=round(s["value_usd"] + total, 2),
              schedule_impact_days=days, **{f"{rc.get('firm_key', 'wursta')}_approver": approver},
              client_signature="required before work starts", valid_for_days=pol["validity_days"],
              result="draft filed in the change register (simulated)", simulated=True)


# =====================================================================================================================
# DELIVERY ENGINE — VDR Validator, Enablement Engine, Cert Notifier
# =====================================================================================================================


@hive_tool("delivery")
@_guard
def dlv_vdr_validate(document: str, template: str = "design_review") -> dict:
    """Validate a delivery document (design review or validation report) against the required VDR template.

    Args:
        document: Document text or a sample key such as 'dlv_vdr_design_kestrel' or 'dlv_vdr_validation_bluestem'.
        template: 'design_review' or 'validation_report'.

    Returns:
        Missing sections, missing document-control fields, version mismatch with the revision history, sign-off
        rows without name/date/decision, placeholders, inconsistent figures, failed tests without a defect id,
        stated vs computed pass rate, a score and a verdict (ready for sign-off / revise and resubmit).
    """
    tpls = fixture("dlv_vdr_templates")
    tpl = tpls.get(template)
    if not tpl:
        return err(f"unknown template {template!r}", available=sorted(tpls))
    text = _text(document)
    if len(text) < 200:
        return err("document too short to validate (min 200 characters)")
    heads = " | ".join(h for _, _, h in _headings(text))
    missing = [s["name"] for s in tpl["required_sections"] if not re.search(s["pattern"], heads)]
    fields = {}
    for f in tpl["control_fields"]:
        m = re.search(rf"\|\s*{f}\s*\|\s*([^|\n]*)\|", text, re.I) or re.search(rf"^\s*\**{f}\**\s*:\s*(.*)$", text,
                                                                                re.I | re.M)
        fields[f] = m.group(1).strip() if m else ""
    missing_fields = [f for f, v in fields.items() if not v]
    issues = []
    rev = _section_text(text, r"revision history|change log")
    versions = re.findall(r"\b(\d+\.\d+)\b", rev)
    if fields.get("Version") and versions:
        latest = max(versions, key=lambda v: tuple(map(int, v.split("."))))
        if latest != fields["Version"].split()[0]:
            issues.append({"type": "version_mismatch", "severity": "major",
                           "detail": f"document control says {fields['Version']} but revision history ends at {latest}"})
    signoff = _section_text(text, r"sign-?off|approvals")
    for role in tpl["signoff_roles"]:
        row = next((ln for ln in signoff.splitlines() if role.lower() in ln.lower()), None)
        if not row:
            issues.append({"type": "signoff_missing_role", "severity": "major", "detail": f"no sign-off row for {role}"})
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 4 or any(not c or c in ("-", "—") for c in cells[1:4]):
            issues.append({"type": "signoff_incomplete", "severity": "major",
                           "detail": f"{role}: name, date and decision are required ({' | '.join(cells[1:4])})"})
    for p in sorted({m.group(0) for m in re.finditer(_PLACEHOLDER, text, re.I)}):
        issues.append({"type": "placeholder", "severity": "minor", "detail": f"placeholder '{p}' left in the document"})
    for unit in ("users", "mailboxes", "shared drives", "test cases"):
        vals = sorted({n.replace(",", "") for n in re.findall(rf"\b(\d[\d,]*)\s+{unit}\b", text, re.I)}, key=int)
        if len(vals) > 1 and unit in ("users", "test cases"):
            issues.append({"type": "inconsistent_figure", "severity": "major",
                           "detail": f"'{unit}' stated with different values: {', '.join(vals)}"})
    stats = {}
    if template == "validation_report":
        rows = [ln for ln in text.splitlines() if re.match(r"^\|\s*TC-\d+", ln.strip())]
        failed = [ln for ln in rows if re.search(r"\|\s*fail", ln, re.I)]
        passed = [ln for ln in rows if re.search(r"\|\s*pass", ln, re.I)]
        for ln in failed:
            if not re.search(r"DEF-\d+", ln):
                issues.append({"type": "fail_without_defect", "severity": "major",
                               "detail": f"{ln.split('|')[1].strip()} failed without a defect id"})
        if rows:
            computed = round(len(passed) / len(rows) * 100, 1)
            stated = re.search(r"pass rate[^0-9]{0,20}(\d{1,3}(?:\.\d)?)\s?%", text, re.I)
            stats = {"test_cases": len(rows), "passed": len(passed), "failed": len(failed),
                     "computed_pass_rate_pct": computed, "stated_pass_rate_pct": float(stated.group(1)) if stated else None}
            if stated and abs(float(stated.group(1)) - computed) > 0.5:
                issues.append({"type": "pass_rate_mismatch", "severity": "major",
                               "detail": f"summary states {stated.group(1)}% but the table gives {computed}%"})
        sev1_open = re.search(r"sev(?:erity)?\s*1\b[^\n]*\bopen\b", text, re.I)
        rec = _section_text(text, r"recommendation")
        go = bool(re.search(r"\bGO\b", rec)) and not re.search(r"NO[- ]GO", rec, re.I)
        if sev1_open and go:
            issues.append({"type": "recommendation_conflict", "severity": "major",
                           "detail": "recommends GO while a Severity 1 defect is still open"})
    major = sum(1 for i in issues if i["severity"] == "major")
    score = max(0, 100 - 10 * len(missing) - 5 * len(missing_fields) - 8 * major
                - 3 * (len(issues) - major))
    return ok(template=tpl["title"], score=score,
              verdict="ready for sign-off" if score >= 85 and not missing and not major else "revise and resubmit",
              missing_sections=missing, control_fields=fields, missing_control_fields=missing_fields, issues=issues,
              test_stats=stats or None, required_sections=[s["name"] for s in tpl["required_sections"]],
              signoff_roles=tpl["signoff_roles"])


@hive_tool("delivery")
@_guard
def dlv_build_training_plan(client_id: str = "kestrel", start_date: str = "2026-11-09", cohort_size: int = 0,
                            sessions_per_day: int = 4, roles: str = "") -> dict:
    """Build a role-based enablement plan: learning paths, cohorts by language, and a session calendar.

    Args:
        client_id: 'kestrel' (Workspace migration, 1,200 users) or 'harborline' (850 users + Gemini pilot).
        start_date: First training day (YYYY-MM-DD); sessions run on business days.
        cohort_size: Override participants per live session (0 = each module's default maximum).
        sessions_per_day: Sessions each trainer can deliver per day (1-6).
        roles: Optional comma-separated role filter (e.g. 'admin,champion').

    Returns:
        Learning path per role, sessions per module and language, trainer and participant hours, the first 15
        calendar slots, the last training date and modules that are self-paced.
    """
    en = fixture("dlv_enablement")
    cl = en["clients"].get(client_id.lower())
    if not cl:
        return err(f"unknown client {client_id!r}", available=sorted(en["clients"]))
    start = _date(start_date)
    if start is None or not 1 <= sessions_per_day <= 6:
        return err("start_date must be YYYY-MM-DD and sessions_per_day 1-6")
    wanted = {r.strip() for r in roles.split(",") if r.strip()}
    order = en["role_priority"]
    sessions, paths, selfpaced = [], {}, {}
    for role in sorted(cl["roles"], key=lambda r: order.index(r) if r in order else 99):
        if wanted and role not in wanted:
            continue
        info = cl["roles"][role]
        path = en["role_paths"].get(role, [])
        paths[role] = {"headcount": info["headcount"], "modules": path,
                       "hours": round(sum(en["modules"][m]["minutes"] for m in path) / 60, 1)}
        for mid in path:
            mod = en["modules"][mid]
            if mod["format"] == "self-paced":
                selfpaced[mid] = selfpaced.get(mid, 0) + info["headcount"]
                continue
            cap = cohort_size or mod["max_cohort"]
            for lang, share in info["languages"].items():
                n = round(info["headcount"] * share)
                if not n:
                    continue
                lang_eff = lang if lang in mod["languages"] else "en"
                for k in range(math.ceil(n / cap)):
                    sessions.append({"module": mid, "title": mod["title"], "role": role, "language": lang_eff,
                                     "participants": min(cap, n - k * cap), "minutes": mod["minutes"]})
    if not sessions and not selfpaced:
        return err("no roles matched", available=sorted(cl["roles"]))
    slots = ["09:00", "11:00", "14:00", "16:00", "08:00", "17:00"][:sessions_per_day]
    day, i, cal = start, 0, []
    while day.weekday() >= 5:
        day += dt.timedelta(days=1)
    while i < len(sessions):
        for t in slots:
            for tr in range(cl["trainers"]):
                if i < len(sessions):
                    cal.append({**sessions[i], "date": day.isoformat(), "time": t, "trainer": f"Trainer {tr + 1}"})
                    i += 1
        day = _add_business_days(day, 1)
    by_mod: dict = {}
    for s in sessions:
        b = by_mod.setdefault(s["module"], {"title": s["title"], "sessions": 0, "participants": 0, "languages": set()})
        b["sessions"] += 1
        b["participants"] += s["participants"]
        b["languages"].add(s["language"])
    for b in by_mod.values():
        b["languages"] = sorted(b["languages"])
    trainer_h = round(sum(s["minutes"] for s in sessions) / 60 * (1 + en["prep_ratio"]), 1)
    part_h = round(sum(s["minutes"] * s["participants"] for s in sessions) / 60, 1)
    return ok(client=cl["name"], start_date=start.isoformat(), last_session=cal[-1]["date"] if cal else None,
              trainers=cl["trainers"], paths=paths, modules=by_mod, total_live_sessions=len(sessions),
              trainer_hours_incl_prep=trainer_h, participant_hours=part_h,
              self_paced={m: {"title": en["modules"][m]["title"], "learners": n} for m, n in selfpaced.items()},
              calendar_first_15=cal[:15], note=cl.get("note", ""))


@hive_tool("delivery")
@_guard
def dlv_generate_quiz(module_id: str, num_questions: int = 5) -> dict:
    """Generate a knowledge-check quiz for an enablement module from the approved question bank.

    Args:
        module_id: Module id, e.g. 'M-EU-102' (Drive & Shared drives) or 'M-ADM-301' (Workspace admin).
        num_questions: Number of questions (1-8).

    Returns:
        Questions with options (A-D), a separate answer key with explanations and the pass mark.
    """
    en = fixture("dlv_enablement")
    bank = en["question_bank"].get(module_id.upper())
    if bank is None:
        return err(f"no question bank for {module_id!r}", available=sorted(en["question_bank"]))
    n = max(1, min(num_questions, 8, len(bank)))
    qs, key = [], []
    for i, q in enumerate(bank[:n], start=1):
        qs.append({"n": i, "question": q["q"], "options": [f"{'ABCD'[j]}. {o}" for j, o in enumerate(q["options"])]})
        key.append({"n": i, "answer": "ABCD"[q["answer"]], "why": q["why"]})
    mod = en["modules"][module_id.upper()]
    return ok(module=module_id.upper(), title=mod["title"], questions=qs, answer_key=key,
              pass_mark_pct=en["quiz_pass_mark_pct"], available_in_bank=len(bank))


def _certs(as_of: dt.date) -> tuple[list[dict], dict]:
    c = fixture("dlv_certifications")
    rows = []
    for p in c["consultants"]:
        for cert in p["certs"]:
            ct = c["cert_types"][cert["cert"]]
            earned = dt.date.fromisoformat(cert["earned"])
            try:
                exp = earned.replace(year=earned.year + ct["validity_years"])
            except ValueError:
                exp = earned.replace(year=earned.year + ct["validity_years"], day=28)
            rows.append({"consultant_id": p["id"], "consultant": p["name"], "practice": p["practice"],
                         "manager": p["manager"], "cert": cert["cert"], "cert_name": ct["name"],
                         "earned": earned.isoformat(), "expires": exp.isoformat(),
                         "days_left": (exp - as_of).days, "renewal_booked": cert.get("renewal_booked", "")})
    return rows, c


@hive_tool("delivery")
@_guard
def dlv_cert_tracker(as_of: str = "2026-11-06", window_days: int = 90, specialization: str = "") -> dict:
    """Track consultants' Google Cloud certifications: expiries and partner specialization coverage now and ahead.

    Args:
        as_of: Reference date (YYYY-MM-DD).
        window_days: Look-ahead window for expiring certifications (e.g. 30, 60, 90).
        specialization: Optional specialization id ('infrastructure', 'data_analytics', 'ai_ml', 'security',
            'work_transformation'); empty checks all.

    Returns:
        Expired and expiring certifications (who, what, days left, renewal booked), per-specialization coverage
        today and at the end of the window versus the illustrative specialization targets, gaps and at-risk counts.
    """
    day = _date(as_of)
    if day is None or not 1 <= window_days <= 365:
        return err("as_of must be YYYY-MM-DD and window_days 1-365")
    rows, c = _certs(day)
    horizon = day + dt.timedelta(days=window_days)
    expired = sorted([r for r in rows if r["days_left"] < 0], key=lambda r: r["days_left"])
    expiring = sorted([r for r in rows if 0 <= r["days_left"] <= window_days], key=lambda r: r["days_left"])
    specs = c["specializations"]
    if specialization:
        if specialization not in specs:
            return err(f"unknown specialization {specialization!r}", available=sorted(specs))
        specs = {specialization: specs[specialization]}
    coverage = []
    for sid, sp in specs.items():
        for req in sp["requirements"]:
            now = {r["consultant_id"] for r in rows if r["cert"] == req["cert"] and r["days_left"] >= 0}
            later = {r["consultant_id"] for r in rows if r["cert"] == req["cert"]
                     and (dt.date.fromisoformat(r["expires"]) > horizon or bool(r["renewal_booked"]))}
            coverage.append({"specialization": sp["name"], "cert": req["cert"],
                             "cert_name": c["cert_types"][req["cert"]]["name"], "required": req["min"],
                             "valid_now": len(now), "valid_at_window_end": len(later),
                             "gap_now": max(0, req["min"] - len(now)),
                             "gap_at_window_end": max(0, req["min"] - len(later)),
                             "status": "gap" if len(now) < req["min"] else "at risk" if len(later) < req["min"] else "ok"})
    return ok(as_of=day.isoformat(), window_days=window_days, consultants=len(c["consultants"]),
              expired=expired, expiring=expiring, coverage=coverage,
              at_risk_specializations=sorted({x["specialization"] for x in coverage if x["status"] != "ok"}),
              policy=c["policy"], note=c["note"])


@hive_tool("delivery", kind="action")
@_guard
def dlv_send_cert_reminders(consultant_ids: list[str], channel: str = "email", as_of: str = "2026-11-06",
                            window_days: int = 90) -> dict:
    """Send certification-renewal reminders to consultants (and cc their managers) — simulated notifications.

    Args:
        consultant_ids: Consultant ids such as ['C-104', 'C-111'] (from dlv_cert_tracker).
        channel: 'email' or 'chat'.
        as_of: Reference date (YYYY-MM-DD).
        window_days: Only certifications expiring within this window (or already expired) are included.

    Returns:
        One reminder per consultant with the certifications, days left, voucher eligibility, the rendered message
        and the next reminder date from the cadence policy (simulated — nothing is sent).
    """
    day = _date(as_of)
    if day is None or channel not in ("email", "chat"):
        return err("as_of must be YYYY-MM-DD and channel email or chat")
    rows, c = _certs(day)
    cadence = sorted(c["policy"]["reminder_cadence_days"], reverse=True)
    sent, skipped = [], []
    for cid in consultant_ids:
        mine = [r for r in rows if r["consultant_id"] == cid.upper() and r["days_left"] <= window_days
                and not r["renewal_booked"]]
        if not mine:
            skipped.append({"consultant_id": cid, "reason": "nothing expiring in window or renewal already booked"})
            continue
        p = mine[0]
        certs = "; ".join(f"{r['cert_name']} ({'expired ' + str(-r['days_left']) + ' days ago' if r['days_left'] < 0 else str(r['days_left']) + ' days left'})"
                          for r in mine)
        soonest = min(r["days_left"] for r in mine)
        nxt = next((d for d in cadence if d < soonest), None)
        sent.append({"consultant_id": cid.upper(), "to": p["consultant"], "cc": p["manager"], "channel": channel,
                     "certifications": [{"cert": r["cert_name"], "expires": r["expires"], "days_left": r["days_left"]}
                                        for r in mine],
                     "voucher_eligible": soonest <= c["policy"]["renewal_start_days"],
                     "message": f"Hi {p['consultant'].split()[0]}, your {certs}. Book the renewal exam via the "
                                f"Learning portal; a voucher is available from the partner team. Reply here if you need "
                                f"study time on your next assignment.",
                     "next_reminder_on": (day + dt.timedelta(days=soonest - nxt)).isoformat() if nxt is not None
                     and soonest > 0 else "escalate to manager weekly"})
    if not sent:
        return err("no reminders to send", skipped=skipped)
    return ok(reminders=sent, skipped=skipped, result=f"{len(sent)} reminders sent via {channel} (simulated)",
              simulated=True)


# =====================================================================================================================
# DELIVERY ENGINE — Migration Ready, Migration CM, Migration Report, Demo Scripts
# =====================================================================================================================


@hive_tool("delivery")
@_guard
def dlv_readiness_assessment(client_id: str) -> dict:
    """Score a client's Workspace-migration readiness questionnaire by domain and give a go / conditional / no-go.

    Args:
        client_id: 'harborline' (Harborline Logistics), 'quarrystone' (Quarrystone Credit Union) or 'kestrel'
            (Kestrel Manufacturing, assessed before its migration).

    Returns:
        Per-domain scores (0-100) with weights, overall weighted score, blockers (critical questions answered no,
        partial or unknown) with remediation, the verdict per the readiness rules and all answers.
    """
    rd = fixture("dlv_readiness")
    cl = rd["clients"].get(client_id.lower())
    if not cl:
        return err(f"unknown client {client_id!r}", available=sorted(rd["clients"]))
    pts = rd["answer_points"]
    domains = []
    for did, d in rd["domains"].items():
        ans = [a for a in cl["answers"] if a["domain"] == did]
        if not ans:
            continue
        sc = round(sum(pts[a["answer"]] for a in ans) / len(ans) * 100, 1)
        domains.append({"domain": did, "name": d["name"], "weight": d["weight"], "score": sc,
                        "questions": len(ans)})
    wsum = sum(d["weight"] for d in domains)
    overall = round(sum(d["score"] * d["weight"] for d in domains) / wsum, 1) if wsum else 0
    blockers = [{"id": a["id"], "question": a["question"], "answer": a["answer"], "evidence": a.get("evidence", ""),
                 "remediation": a.get("remediation", "")}
                for a in cl["answers"] if a["critical"] and a["answer"] != "yes"]
    rules = rd["rules"]
    if any(b["answer"] == "no" for b in blockers) or overall < rules["no_go_below"]:
        verdict = "NO-GO"
    elif blockers or overall < rules["go_from"]:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "GO"
    return ok(client=cl["name"], assessed_on=cl["assessed_on"], profile=cl["profile"], overall_score=overall,
              verdict=verdict, domains=sorted(domains, key=lambda d: d["score"]), blockers=blockers,
              rules=rules, answers=cl["answers"])


@hive_tool("delivery")
@_guard
def dlv_change_profile(client_id: str = "kestrel", section: str = "all") -> dict:
    """Change-management profile for a migration client: stakeholder map and post-migration adoption telemetry.

    Args:
        client_id: 'kestrel' (migration in flight, adoption data for waves W0-W3) or 'harborline' (pre-migration).
        section: 'all', 'stakeholders' or 'adoption'.

    Returns:
        Stakeholders with influence/impact (1-5), attitude, concerns and needs, placed in a power-interest quadrant;
        impacted groups; adoption by department vs thresholds (Drive/Meet usage, legacy client use, training,
        champions coverage) with flagged gaps; the current champions network.
    """
    data = fixture("dlv_change_profiles")
    cps, th = data["clients"], data["thresholds"]
    cp = cps.get(client_id.lower())
    if not cp:
        return err(f"unknown client {client_id!r}", available=sorted(cps))
    if section not in ("all", "stakeholders", "adoption"):
        return err("section must be all, stakeholders or adoption")
    out: dict = {"client": cp["name"], "context": cp["context"]}
    if section in ("all", "stakeholders"):
        rows = []
        for s in cp["stakeholders"]:
            q = ("manage closely" if s["influence"] >= 4 and s["impact"] >= 4 else
                 "keep satisfied" if s["influence"] >= 4 else "keep informed" if s["impact"] >= 4 else "monitor")
            rows.append({**s, "quadrant": q})
        out["stakeholders"] = sorted(rows, key=lambda r: (-r["influence"] - r["impact"], r["name"]))
        out["resistance_risks"] = [r["name"] for r in rows if r["attitude"] in ("skeptic", "resistant")
                                   and r["influence"] >= 3]
        out["impacted_groups"] = cp["impacted_groups"]
    if section in ("all", "adoption"):
        ad = cp.get("adoption")
        if not ad:
            out["adoption"] = None
            out["adoption_note"] = "No adoption telemetry yet — client has not migrated."
        else:
            rows = []
            for d in ad["by_department"]:
                flags = []
                if d["drive_wau_pct"] < th["drive_wau_min_pct"]:
                    flags.append(f"Drive usage {d['drive_wau_pct']}% < {th['drive_wau_min_pct']}%")
                if d["legacy_client_pct"] > th["legacy_client_max_pct"]:
                    flags.append(f"legacy desktop client {d['legacy_client_pct']}% > {th['legacy_client_max_pct']}%")
                if d["training_completion_pct"] < th["training_min_pct"]:
                    flags.append(f"training {d['training_completion_pct']}% < {th['training_min_pct']}%")
                per50 = round(d["champions"] / d["users"] * 50, 2)
                if per50 < th["champions_per_50_min"]:
                    flags.append(f"{per50} champions per 50 users < {th['champions_per_50_min']}")
                rows.append({**d, "champions_per_50_users": per50, "flags": flags,
                             "health": "red" if len(flags) >= 2 else "amber" if flags else "green"})
            out["adoption"] = {"as_of": ad["as_of"], "by_department": rows, "champions": ad["champions"],
                               "thresholds": th}
    return ok(**out)


def _tracker_waves_kes() -> tuple[list[dict], list[dict], dict]:
    rs = fixture("atlas_run_state")
    waves = []
    for w in _baseline():
        st = rs["waves"].get(w["wave_id"], {"status": "scheduled"})
        waves.append({"wave_id": w["wave_id"], "label": w["label"], "planned_date": w["cutover_date"],
                      "actual_date": st.get("cutover_actual"), "planned_users": w["users"],
                      "migrated_users": st.get("users_migrated", 0) if st["status"] in ("complete", "hypercare") else 0,
                      "deferred_users": len(st.get("deferred", [])), "status": st["status"],
                      "data_tb": round(w["data_gb"]["total"] / 1000, 2)})
    return waves, rs["issues"], rs["hypercare"]


@hive_tool("delivery")
@_guard
def dlv_migration_tracker(project_id: str = "KES-WS-2026", as_of: str = "2026-11-06") -> dict:
    """Read a migration tracker and compute progress, plan-vs-actual, burndown and a completion forecast.

    Args:
        project_id: 'KES-WS-2026' (Kestrel, Atlas-run, in flight) or 'TDW-WS-2026' (Tidewell Dental Group, complete).
        as_of: Report date (YYYY-MM-DD).

    Returns:
        Summary (users and waves complete, % done), waves with planned vs actual dates and users, burndown series
        (planned vs actual users remaining), schedule variance, velocity, forecast finish vs baseline, open issues
        by severity and hypercare ticket trend.
    """
    pid = project_id.strip().upper()
    day = _date(as_of)
    if day is None:
        return err("as_of must be YYYY-MM-DD")
    if pid == "KES-WS-2026":
        waves, issues, hyper = _tracker_waves_kes()
        meta = {"client": fixture("atlas_tenant")["tenant"]["client"], "engine": "Atlas suite",
                "sow_id": "SOW-2026-0412"}
    else:
        projs = fixture("dlv_migration_projects")
        p = projs.get(pid)
        if not p:
            return err(f"unknown project {project_id!r}", available=["KES-WS-2026", *sorted(projs)])
        waves, issues, hyper = p["waves"], p["issues"], p["hypercare"]
        meta = {k: p[k] for k in ("client", "engine", "sow_id")}
    total = sum(w["planned_users"] for w in waves)
    burndown, rem_plan, rem_act = [], total, total
    for w in waves:
        rem_plan -= w["planned_users"]
        point = {"wave_id": w["wave_id"], "date": w["planned_date"], "planned_remaining": rem_plan}
        if w["actual_date"]:
            rem_act -= w["migrated_users"]
            point["actual_remaining"] = rem_act
        burndown.append(point)
    done = [w for w in waves if w["actual_date"]]
    migrated = sum(w["migrated_users"] for w in done)
    slips = [(dt.date.fromisoformat(w["actual_date"]) - dt.date.fromisoformat(w["planned_date"])).days for w in done]
    slip = max(slips[-1:] or [0], default=0)
    remaining = [w for w in waves if not w["actual_date"]]
    baseline_finish = waves[-1]["planned_date"]
    forecast = (dt.date.fromisoformat(baseline_finish) + dt.timedelta(days=max(0, slip))).isoformat() \
        if remaining else (done[-1]["actual_date"] if done else baseline_finish)
    deferred = sum(w["deferred_users"] for w in waves)
    first = dt.date.fromisoformat(done[0]["actual_date"]) if done else day
    weeks = max(1, ((day - first).days + 1) / 7)
    sev = {"Sev1": 0, "Sev2": 0, "Sev3": 0, "Sev4": 0}
    for i in issues:
        if i["status"] != "closed":
            sev[i["severity"]] += 1
    return ok(project_id=pid, as_of=day.isoformat(), **meta,
              summary={"users_total": total, "users_migrated": migrated, "pct_complete": round(migrated / total * 100, 1),
                       "waves_complete": len(done), "waves_total": len(waves), "deferred_users": deferred,
                       "velocity_users_per_week": round(migrated / weeks, 1),
                       "schedule_variance_days": slip, "baseline_finish": baseline_finish, "forecast_finish": forecast,
                       "on_track": forecast <= baseline_finish},
              waves=waves, burndown=burndown, open_issues_by_severity=sev,
              open_issues=[i for i in issues if i["status"] != "closed"], hypercare=hyper)


@hive_tool("delivery")
@_guard
def dlv_agent_demo_facts(agent_id: str) -> dict:
    """Return the facts a demo script needs about what is being demoed: what it does, how, exact inputs, KPIs.

    Args:
        agent_id: Id or name of the agent or solution to demo, as named in the demo request (an unknown id
            returns the available ones).

    Returns:
        Name, tagline, description, audience, how it works (pattern, steps, tools), which actions are simulated,
        the tested sample inputs (exact prompts for the click path), sample document, KPIs and related items.
    """
    sols = fixture("dlv_demo_rules").get("solutions")
    if sols:   # an edition can demo its own solutions instead of the agent catalog
        want = _key(agent_id)
        s = next((x for x in sols if want in (x["id"], _key(x["name"]))), None) or next(
            (x for x in sols if want and (want in _key(x["name"]) or x["id"] in want)), None)
        if not s:
            return err(f"unknown solution {agent_id!r}", available=[f"{x['id']} ({x['name']})" for x in sols])
        return ok(kind="solution", **s)
    from ..catalog import load_catalog

    cat = load_catalog()
    want = agent_id.strip().lower()
    match = next((x for x in cat.agents() if want in (x.id, x.code.lower(), x.name.lower(), (x.aka or "").lower())),
                 None) or next((x for x in cat.agents() if want.replace("_", " ") in x.name.lower()
                                or x.id in want or want in x.id), None)
    try:
        a = match or cat.agent(want)
    except KeyError:
        ids = [x.id for x in cat.agents()]
        close = [i for i in ids if agent_id.lower().split("_")[0] in i][:8]
        return err(f"unknown agent {agent_id!r}", similar=close)
    from ._base import TOOL_META

    tools = a.tools + [t for s in a.steps for t in s.tools]
    return ok(id=a.id, code=a.code, name=a.name, realm=a.realm, agent_status=a.status, aka=a.aka, tagline=a.tagline,
              description=a.description, persona=a.persona, use_cases=a.use_cases, model=a.model, pattern=a.pattern,
              steps=[{"id": s.id, "name": s.name, "model": s.model, "role": s.role} for s in a.steps],
              tools=[{"name": t, "kind": TOOL_META[t]["kind"], "summary": TOOL_META[t]["summary"]} for t in tools
                     if t in TOOL_META],
              simulated_actions=[t for t in tools if TOOL_META.get(t, {}).get("kind") == "action"],
              grounding=a.grounding, samples=a.samples, sample_doc=a.sample_doc, kpis=a.kpis, related=a.related)


@hive_tool("delivery")
@_guard
def dlv_demo_timing(segments: list[dict], slot_minutes: int = 30) -> dict:
    """Check a demo run-of-show against the demo standards: timing, live share, buffer and fallbacks.

    Args:
        segments: Ordered list of {"name": str, "minutes": number, "type": "intro"|"context"|"live_demo"|"story"|
            "qa"|"close", "fallback": str (required for live_demo)}.
        slot_minutes: Length of the meeting slot in minutes.

    Returns:
        Total minutes, buffer, share of time by segment type, each rule (pass/fail with the fix) and a verdict.
    """
    rules = fixture("dlv_demo_rules")
    if not segments or slot_minutes <= 0:
        return err("segments must not be empty and slot_minutes > 0")
    try:
        total = sum(float(s.get("minutes", 0)) for s in segments)
    except (TypeError, ValueError):
        return err("every segment needs numeric minutes")
    by_type: dict = {}
    for s in segments:
        by_type[s.get("type", "story")] = by_type.get(s.get("type", "story"), 0) + float(s.get("minutes", 0))
    share = {k: round(v / total * 100, 1) for k, v in by_type.items()} if total else {}
    buffer = slot_minutes - total
    checks = [
        {"rule": "Fits the slot with buffer", "pass": buffer >= slot_minutes * rules["min_buffer_pct"] / 100,
         "detail": f"{total:g} of {slot_minutes} min planned; buffer {buffer:g} min (min {rules['min_buffer_pct']}%)",
         "fix": "cut context or merge story segments"},
        {"rule": "Live demo share", "pass": share.get("live_demo", 0) >= rules["min_live_pct"],
         "detail": f"live demo {share.get('live_demo', 0)}% (min {rules['min_live_pct']}%)",
         "fix": "move explanation into the live click path"},
        {"rule": "Context/intro cap", "pass": share.get("context", 0) + share.get("intro", 0) <= rules["max_context_pct"],
         "detail": f"intro+context {round(share.get('context', 0) + share.get('intro', 0), 1)}% (max {rules['max_context_pct']}%)",
         "fix": "one slide of context, then show"},
        {"rule": "Q&A reserved", "pass": by_type.get("qa", 0) >= rules["min_qa_minutes"],
         "detail": f"Q&A {by_type.get('qa', 0):g} min (min {rules['min_qa_minutes']})", "fix": "reserve Q&A time"},
        {"rule": "No long monologue", "pass": all(float(s.get("minutes", 0)) <= rules["max_talk_segment_minutes"]
                                                  for s in segments if s.get("type") in ("intro", "context", "story")),
         "detail": f"talk segments <= {rules['max_talk_segment_minutes']} min", "fix": "split or add an interaction"},
        {"rule": "Fallback for every live segment",
         "pass": all(str(s.get("fallback", "")).strip() for s in segments if s.get("type") == "live_demo"),
         "detail": "each live_demo segment names its fallback (recorded run, screenshot, cached answer)",
         "fix": "add a fallback to each live segment"},
    ]
    return ok(total_minutes=total, slot_minutes=slot_minutes, buffer_minutes=buffer, share_pct_by_type=share,
              checks=checks, verdict="approved" if all(c["pass"] for c in checks) else "revise",
              failed=[c["rule"] for c in checks if not c["pass"]])

"""Synthetic BigQuery rows for WAISentry (SMB realm) — security telemetry of the fictional client Kitewing Software.

    tables() -> {"sentry_events": [...], "sentry_incidents": [...], "sentry_ingest_daily": [...]}

Deterministic (random.Random(SEED)). The three demo telemetry batches and the seven incidents in
agenthive/tools/fixtures/sentry_*.json are included with the same ids, scores and timings, so AI Triage, WAISentry SOC
and BigQuery tell the same story; generated events never fall inside the batch windows. Identities are tokenised with
the same HMAC scheme as agenthive/tools/waisentry.py (zero-PII). Telemetry runs from go-live (2026-10-08) to
2026-11-06 09:30, Kitewing local time (UTC-6). Every person and company is fictional.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

SEED = 20261107
FIX = Path(__file__).resolve().parents[2] / "agenthive" / "tools" / "fixtures"
TZ = dt.timezone(dt.timedelta(hours=-6))
FIRST_DAY = dt.date(2026, 10, 8)
TODAY = dt.date(2026, 11, 6)
NOW = dt.datetime(2026, 11, 6, 9, 30, tzinfo=TZ)
_KEY = b"waisentry-demo/kitewing.example/tokeniser-v1"   # same demo constant as the tools
_PREFIX = {"user": "USR", "external": "EXT", "file": "FIL", "message": "MSG", "device": "DEV"}

CATEGORY = {"workspace.login": "identity", "workspace.admin": "identity", "workspace.token": "oauth",
            "workspace.drive": "data", "workspace.gmail": "email", "mimecast": "email", "dnsfilter": "network",
            "web_proxy": "network", "firewall_ids": "onprem", "syslog.dc": "onprem", "syslog.fs": "onprem",
            "edr": "endpoint", "knowbe4": "awareness"}
SOURCES = list(CATEGORY)
# raw records per day (weekday, weekend); dnsfilter and mimecast are scaled to the SaaS summaries in the fixtures
RAW = {"workspace.login": (900, 160), "workspace.admin": (120, 15), "workspace.token": (1400, 600),
       "workspace.drive": (5200, 600), "workspace.gmail": (300, 60), "web_proxy": (9000, 1500),
       "firewall_ids": (2600, 2300), "syslog.dc": (1500, 700), "syslog.fs": (900, 500), "edr": (3400, 2200),
       "knowbe4": (60, 5)}

# (source, type, summary, signals, actor kind, when)  when: any = round the clock, day = mostly business hours
NOISE = [
    ("firewall_ids", "inbound_scan_blocked", "Inbound port scan from {scanner} blocked at MB-FW01", ["inbound_scan_blocked"], "asset:MB-FW01", "any", 9),
    ("dnsfilter", "dns_block", "Blocked ad/tracker domain {ad}", ["ad_tracker_block"], "device", "any", 9),
    ("workspace.login", "login_success", "Sign-in from {home}, security key, known device", ["security_key_used", "known_device"], "user", "day", 10),
    ("workspace.login", "login_failed_then_success", "One wrong password, then success from a known device", ["single_failure", "known_device", "security_key_used"], "user", "day", 3),
    ("workspace.drive", "file_edit", "Edited an internal document they own", ["routine_edit"], "user", "day", 9),
    ("workspace.drive", "internal_share", "Shared a document with a colleague (internal only)", [], "user", "day", 6),
    ("mimecast", "mail_delivered", "Newsletter delivered from a bulk sender (DMARC pass)", ["bulk_mail"], "user", "any", 7),
    ("mimecast", "spam_rejected", "Spam from {scanner} rejected on reputation", ["spam_blocked"], "user", "any", 6),
    ("edr", "scan_complete", "Scheduled EDR scan completed, 0 detections", ["scheduled_task"], "device", "any", 5),
    ("syslog.dc", "kerberos_routine", "Routine Kerberos ticket renewals on MB-DC01 ({n} accounts)", ["routine_auth"], "asset:MB-DC01", "any", 5),
    ("syslog.fs", "backup_job", "Nightly backup job completed (Projects-Archive)", ["scheduled_task"], "asset:MB-FS01", "night", 1),
    ("workspace.token", "token_refresh", "Token refresh for sanctioned app {app}", ["sanctioned_app"], "user", "any", 6),
    ("web_proxy", "web_allowed", "Browsed business-category sites (allowed)", [], "device", "day", 5),
    ("knowbe4", "training_completed", "Completed a security-awareness module", ["training"], "user", "day", 2),
    ("workspace.admin", "admin_routine", "Admin viewed audit reports", ["admin_routine"], "user:noah.kim", "day", 1),
    ("dnsfilter", "nrd_block", "Blocked newly registered domain {nrd}", ["newly_registered_domain", "dns_blocked"], "device", "any", 2),
    ("workspace.token", "oauth_grant", "Granted allowlisted app {app2} (verified, file-only scope)", ["verified_publisher", "low_risk_scope", "allowlisted"], "user", "day", 1),
]
# benign alerts (score >= 60) that analysts closed without an incident
ALERTS = [
    ("workspace.token", "oauth_grant", "Granted unverified app '{legacy}' high-risk scopes (reviewed: legacy grant, posture finding PC-06)",
     ["unverified_publisher", "high_risk_scope", "first_seen_app"], "user", "T1528", "benign_true_positive", "pre_policy"),
    ("workspace.login", "impossible_travel", "Sign-in through a consumer VPN exit in {vpn} 20 minutes after a home sign-in",
     ["impossible_travel", "new_country", "hosting_asn", "single_failure"], "user", "T1078.004", "false_positive", None),
    ("workspace.drive", "bulk_download", "Downloaded 240 files from Customers/QBR (owner's own team folder)",
     ["bulk_download", "sensitive_folder", "customer_data"], "user", "T1530", "benign_true_positive", None),
    ("edr", "pup_detected", "Potentially unwanted app from a new download site blocked and removed",
     ["unsigned_binary", "edr_medium", "executable_download", "newly_registered_domain"], "device", "T1204.002", "benign_true_positive", None),
    ("workspace.drive", "public_link_created", "Set 'anyone with the link' on a Confidential proposal for a customer (approved by the account owner)",
     ["external_link_on_confidential", "customer_data"], "user", "T1567.002", "benign_true_positive", None),
    ("mimecast", "impersonation_blocked", "CEO display-name impersonation (gift-card request) from a new domain — blocked at the gateway",
     ["lookalike_domain", "newly_registered_domain", "external_sender_first_contact", "bank_change_language"], "user", "T1656", "true_positive_blocked", None),
]
SCANNERS = ["192.0.2.201", "192.0.2.34", "192.0.2.118", "192.0.2.77", "192.0.2.159", "192.0.2.12", "192.0.2.240"]
ADS = ["adserve-metrics.example", "pixel-track.example", "cdn-beacon.example", "clickstat.example"]
NRDS = ["parcel-track-update.example", "invoice-view-now.example", "promo-giftbox.example", "secure-login-check.example"]
APPS = ["Slack", "Zoom", "DocuSign", "Kitewing FieldOps SSO", "KnowBe4 Phish Alert Button"]
APPS2 = ["Diagram Helper", "MailMerge Toolkit"]
LEGACY = ["Docs PDF Converter Plus", "AI Meeting Notes Free", "Calendar Sync Pro"]
VPN = [("Toronto, CA", "198.51.100.201"), ("Dublin, IE", "198.51.100.202"), ("Montreal, CA", "198.51.100.203")]
HOME = {"Cedar Harbor HQ": "Cedar Harbor", "Millbrook office": "Millbrook", "Remote": "home ISP"}


def token(kind: str, value: str) -> str:
    v = re.sub(r"\s+", " ", str(value).strip().lower())
    return f"{_PREFIX[kind]}-{hmac.new(_KEY, f'{kind}:{v}'.encode(), hashlib.sha256).hexdigest()[:4].upper()}"


def _fx(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text())


def _after_hours(d: dt.datetime) -> bool:
    return d.weekday() >= 5 or not (7 <= d.hour < 19)


def _secs(a: str | None, b: str | None) -> int | None:
    return int((dt.datetime.fromisoformat(b) - dt.datetime.fromisoformat(a)).total_seconds()) if a and b else None


def _local(s: str | dt.datetime) -> dt.datetime:
    d = dt.datetime.fromisoformat(s) if isinstance(s, str) else s
    return d.astimezone(TZ)


def _row(eid: str, when: dt.datetime, src: str, typ: str, actor: str, summary: str, signals: list[str], sc: dict,
         incident: str | None = None, technique: str | None = None, batch: str | None = None, ip: str | None = None,
         geo: str | None = None, triage_s: int | None = None, disposition: str | None = None) -> dict:
    score = max(0, min(99, sc["base"] + sum(sc["weights"].get(s, 0) for s in signals)))
    sev = next(name for floor, name in sc["bands"] if score >= floor)
    alert = score >= sc["alert_threshold"]
    verdict = ("incident" if incident else "alert") if alert else "noise"
    tname, tactic = sc["techniques"].get(technique, [None, None]) if technique else (None, None)
    loc = _local(when)
    return {"event_id": eid, "event_ts": loc.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "event_local": loc.strftime("%Y-%m-%dT%H:%M:%S"), "event_date": loc.date().isoformat(), "batch_id": batch,
            "source": src, "category": CATEGORY[src], "event_type": typ, "actor_token": actor, "summary": summary,
            "src_ip": ip, "geo": geo, "signals": ",".join(signals), "triage_score": score, "severity": sev,
            "verdict": verdict, "disposition": (disposition or "true_positive") if alert else None,
            "mitre_technique": technique, "mitre_name": tname, "mitre_tactic": tactic, "incident_id": incident,
            "after_hours": _after_hours(loc), "triage_seconds": triage_s if alert else None}


def _windows(batches: dict) -> list[tuple[dt.datetime, dt.datetime]]:
    return [(dt.datetime.fromisoformat(b["window"][0]), dt.datetime.fromisoformat(b["window"][1])) for b in batches.values()]


def _when(rng: random.Random, day: dt.date, kind: str, windows, last: dt.datetime | None) -> dt.datetime:
    for _ in range(50):
        if kind == "day" and rng.random() < 0.88:
            h = rng.randint(7, 18)
        elif kind == "night":
            h = rng.randint(1, 4)
        else:
            h = rng.randint(0, 23)
        t = dt.datetime.combine(day, dt.time(h, rng.randint(0, 59), rng.randint(0, 59)), tzinfo=TZ)
        if last and t >= last:
            continue
        if any(a <= t < b for a, b in windows):
            continue
        return t
    return dt.datetime.combine(day, dt.time(6, 0), tzinfo=TZ)


def _split(total: int, weights: list[float]) -> list[int]:
    s = sum(weights)
    parts = [int(total * w / s) for w in weights]
    parts[-1] += total - sum(parts)
    return parts


def tables() -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    tel, incs, ten, saas = _fx("sentry_telemetry"), _fx("sentry_incidents")["incidents"], _fx("sentry_tenant"), _fx("sentry_saas")
    sc, batches = tel["scoring"], tel["batches"]
    people = [d for d in ten["directory"] if d["type"] in ("employee", "contractor")]
    windows = _windows(batches)
    days = [FIRST_DAY + dt.timedelta(days=i) for i in range((TODAY - FIRST_DAY).days + 1)]

    events: list[dict] = []
    # 1) the three demo batches, exactly as the triage tool sees them
    for bid, b in batches.items():
        for e in b["events"]:
            events.append(_row(e["id"], e["ts"], e["src"], e["type"], e["actor"], e["detail"], e["signals"], sc,
                               incident=e.get("incident"), technique=e.get("technique"), batch=bid, ip=e.get("ip"),
                               geo=e.get("geo"), triage_s=e.get("triaged_s")))
    # 2) incident events that are not in a batch
    for inc in incs:
        for e in inc.get("events", []):
            events.append(_row(e["id"], e["ts"], e["src"], e["type"], e["actor"], e["detail"], e["signals"], sc,
                               incident=inc["id"], technique=e.get("technique"), ip=e.get("ip"), geo=e.get("geo"),
                               triage_s=e.get("triaged_s")))
    per_day_fixed = Counter(r["event_date"] for r in events)
    # 3) generated noise and benign alerts
    weights = [x[6] for x in NOISE]
    for day in days:
        mmdd = day.strftime("%m%d")
        last = NOW if day == TODAY else None
        if day == TODAY:
            target = rng.randint(95, 125)
        elif day.weekday() >= 5:
            target = rng.randint(120, 170)
        else:
            target = rng.randint(330, 430)
        n_alerts = rng.choice([0, 0, 1] if day.weekday() >= 5 or day == TODAY else [0, 1, 1, 2, 2, 3])
        n_noise = max(0, target - per_day_fixed.get(day.isoformat(), 0) - n_alerts)
        k = 0
        for _ in range(n_noise):
            src, typ, summ, sig, akind, when, _w = rng.choices(NOISE, weights=weights)[0]
            p = rng.choice(people)
            if akind.startswith("asset:"):
                actor = akind.split(":", 1)[1]
            elif akind.startswith("user:"):
                actor = token("user", f"{akind.split(':', 1)[1]}@kitewing.example")
            elif akind == "device":
                actor = token("device", p["device"])
            else:
                actor = token("user", p["email"])
            t = _when(rng, day, when, windows, last)
            signals = list(sig) + (["after_hours"] if _after_hours(t) and src.startswith("workspace") and typ != "token_refresh" else [])
            summary = summ.format(scanner=rng.choice(SCANNERS), ad=rng.choice(ADS), home=HOME[p["office"]],
                                  n=rng.randint(6, 18), app=rng.choice(APPS), app2=rng.choice(APPS2), nrd=rng.choice(NRDS))
            ip = (f"203.0.113.{rng.randint(20, 180)}" if src == "workspace.login" else
                  summary.split(" from ")[1].split(" ")[0] if "port scan" in summary or "Spam from" in summary else None)
            geo = f"{HOME[p['office']].replace('home ISP', 'Remote')}, US" if src == "workspace.login" else None
            k += 1
            events.append(_row(f"EV-{mmdd}-G{k:04d}", t, src, typ, actor, summary, signals, sc, ip=ip, geo=geo))
        for _ in range(n_alerts):
            pool = [a for a in ALERTS if a[7] != "pre_policy" or day < dt.date(2026, 11, 3)]
            src, typ, summ, sig, akind, tech, disp, _c = rng.choice(pool)
            p = rng.choice(people)
            actor = token("device", p["device"]) if akind == "device" and p["device"] else token("user", p["email"])
            t = _when(rng, day, "day", windows, last)
            city, ip = rng.choice(VPN)
            summary = summ.format(legacy=rng.choice(LEGACY), vpn=city)
            signals = list(sig) + (["after_hours"] if _after_hours(t) else [])
            k += 1
            events.append(_row(f"EV-{mmdd}-G{k:04d}", t, src, typ, actor, summary, signals, sc, technique=tech,
                               ip=ip if typ == "impossible_travel" else None, geo=city if typ == "impossible_travel" else None,
                               triage_s=rng.randint(3, 12), disposition=disp))
    events.sort(key=lambda r: r["event_local"])

    # incidents
    inc_rows = []
    for inc in incs:
        rows = inc.get("containment") or []
        inc_rows.append({
            "incident_id": inc["id"], "title": inc["title"], "category": inc["category"], "severity": inc["severity"],
            "status": "open" if inc["status"].startswith("open") else inc["status"], "primary_actor": inc["primary_actor"],
            "first_malicious_ts": _local(inc["first_malicious"]).astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "opened_local": _local(inc["opened"]).strftime("%Y-%m-%dT%H:%M:%S"),
            "contained_local": _local(inc["contained_at"]).strftime("%Y-%m-%dT%H:%M:%S") if inc.get("contained_at") else None,
            "contained_by": inc.get("contained_by"),
            "triage_seconds": _secs(inc["first_malicious"], inc["first_alert"]),
            "investigation_seconds": _secs(inc["opened"], inc["confirmed"]),
            "active_containment_seconds": _secs(inc["authorised"], max(r["end"] for r in rows)) if rows else None,
            "seconds_to_contain": _secs(inc["first_malicious"], inc.get("contained_at")),
            "playbooks": ",".join(r["playbook"] for r in rows) or None, "escalated_actions": len(inc["escalate"]),
            "analyst": inc["analyst"].split(" (")[0],
            "mitre_techniques": ",".join(dict.fromkeys(t for t, _ in inc["attack_path"])),
            "funds_at_risk_usd": float(inc["funds_at_risk_usd"]), "funds_lost_usd": float(inc["funds_lost_usd"]),
            "batch_id": inc.get("batch"), "outcome": inc["outcome"]})

    # daily ingest volumes
    scored = Counter((r["event_date"], r["source"]) for r in events)
    alerts = Counter((r["event_date"], r["source"]) for r in events if r["verdict"] != "noise")
    wk = [0.3 if d == TODAY else 0.72 if d.weekday() >= 5 else 1.0 for d in days]
    last7 = [d >= TODAY - dt.timedelta(days=6) for d in days]
    fixed_raw = {}
    for src, key in (("dnsfilter", ("dnsfilter", "queries")), ("mimecast", ("mimecast", "inbound"))):
        t7 = saas["alerts"]["7"][key[0]][key[1]]
        t30 = saas["alerts"]["30"][key[0]][key[1]]
        early = _split(t30 - t7, [w * rng.uniform(0.9, 1.1) for w, l in zip(wk, last7) if not l])
        late = _split(t7, [w * rng.uniform(0.9, 1.1) for w, l in zip(wk, last7) if l])
        fixed_raw[src] = early + late
    ingest = []
    for i, d in enumerate(days):
        for src in SOURCES:
            if src in fixed_raw:
                raw = fixed_raw[src][i]
            else:
                base = RAW[src][1] if d.weekday() >= 5 else RAW[src][0]
                raw = int(base * (0.3 if d == TODAY else 1.0) * rng.uniform(0.85, 1.15))
            n, a = scored[(d.isoformat(), src)], alerts[(d.isoformat(), src)]
            ingest.append({"day": d.isoformat(), "source": src, "raw_records": max(raw, n), "events_scored": n,
                           "alerts": a, "noise_removed_pct": round(100 * (1 - a / n), 2) if n else None})
    return {"sentry_events": events, "sentry_incidents": inc_rows, "sentry_ingest_daily": ingest}


if __name__ == "__main__":
    t = tables()
    for name, rows in t.items():
        print(name, len(rows))
    ev = t["sentry_events"]
    al = [r for r in ev if r["verdict"] != "noise"]
    print("alerts", len(al), "noise removed %", round(100 * (1 - len(al) / len(ev)), 2), Counter(r["verdict"] for r in ev))
    print(Counter(r["mitre_technique"] for r in al).most_common(8))
    by_day = defaultdict(int)
    for r in ev:
        by_day[r["event_date"]] += 1
    print(sorted(by_day.items())[:3], sorted(by_day.items())[-3:])

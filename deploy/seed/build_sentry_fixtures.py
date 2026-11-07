"""Builds (regenerates) the WAISentry fixtures (agenthive/tools/fixtures/sentry_*.json) for the Kitewing demo world.

Readable templates use placeholders that are replaced by deterministic HMAC tokens (zero-PII telemetry):
  <<u:local>>  user/shared mailbox (local part @kitewing.example) -> USR-xxxx
  <<x:email>>  external address -> EXT-xxxx
  <<f:name>>   file name -> FIL-xxxx
  <<d:host>>   personal device hostname -> DEV-xxxx
  <<m:text>>   message subject -> MSG-xxxx
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "agenthive" / "tools" / "fixtures"
DOMAIN = "kitewing.example"
KEY = b"waisentry-demo/kitewing.example/tokeniser-v1"
PREFIX = {"user": "USR", "external": "EXT", "file": "FIL", "message": "MSG", "device": "DEV", "phone": "PHN",
          "account": "ACC"}
TZ = dt.timezone(dt.timedelta(hours=-6))


def token(kind: str, value: str) -> str:
    v = re.sub(r"\s+", " ", str(value).strip().lower())
    return f"{PREFIX[kind]}-{hmac.new(KEY, f'{kind}:{v}'.encode(), hashlib.sha256).hexdigest()[:4].upper()}"


# ----------------------------------------------------------------------------------------------- directory
# (local, name, title, team, office, os, two_sv, kind)
D = [
    ("dana.whitfield", "Dana Whitfield", "CEO", "Leadership", "Cedar Harbor HQ", "macOS"),
    ("marcus.bell", "Marcus Bell", "COO & CFO", "Leadership", "Cedar Harbor HQ", "macOS"),
    ("lena.okafor", "Lena Okafor", "VP Sales", "Sales", "Cedar Harbor HQ", "macOS"),
    ("jamie.cho", "Jamie Cho", "Account Executive (Mid-market)", "Sales", "Cedar Harbor HQ", "macOS"),
    ("priya.natarajan", "Priya Natarajan", "Account Executive (SMB)", "Sales", "Remote", "Windows"),
    ("ethan.caldwell", "Ethan Caldwell", "Account Executive", "Sales", "Remote", "Windows"),
    ("owen.gallagher", "Owen Gallagher", "Sales Development Representative", "Sales", "Cedar Harbor HQ", "Windows"),
    ("rosa.delgado", "Rosa Delgado", "Sales Engineer", "Sales", "Cedar Harbor HQ", "macOS"),
    ("theo.marsh", "Theo Marsh", "Sales Development Representative", "Sales", "Cedar Harbor HQ", "Windows"),
    ("isla.brennan", "Isla Brennan", "Sales Operations Analyst", "Sales", "Remote", "Windows"),
    ("marco.venturi", "Marco Venturi", "Account Executive (Enterprise)", "Sales", "Remote", "macOS"),
    ("hannah.brooks", "Hannah Brooks", "Head of Customer Success", "Customer Success", "Cedar Harbor HQ", "macOS"),
    ("kwame.mensah", "Kwame Mensah", "Customer Success Manager", "Customer Success", "Remote", "macOS"),
    ("ruth.adebayo", "Ruth Adebayo", "Customer Success Manager", "Customer Success", "Cedar Harbor HQ", "Windows"),
    ("paul.ngata", "Paul Ngata", "Customer Success Manager", "Customer Success", "Millbrook office", "Windows"),
    ("ines.duarte", "Ines Duarte", "Senior Implementation Consultant", "Customer Success", "Remote", "macOS"),
    ("tomas.rivera", "Tomás Rivera", "Implementation Consultant", "Customer Success", "Millbrook office", "Windows"),
    ("liam.oconnor", "Liam O'Connor", "Support Lead", "Customer Success", "Millbrook office", "Windows"),
    ("ava.lindholm", "Ava Lindholm", "Support Specialist", "Customer Success", "Millbrook office", "ChromeOS"),
    ("jonah.petit", "Jonah Petit", "Support Specialist", "Customer Success", "Millbrook office", "Windows"),
    ("zara.quinn", "Zara Quinn", "Support Specialist", "Customer Success", "Millbrook office", "ChromeOS"),
    ("kofi.asante", "Kofi Asante", "Support Specialist", "Customer Success", "Remote", "ChromeOS"),
    ("wei.zhang", "Wei Zhang", "Implementation Consultant", "Customer Success", "Remote", "macOS"),
    ("fatima.diallo", "Fatima Diallo", "Support Specialist", "Customer Success", "Millbrook office", "ChromeOS"),
    ("sam.okoro", "Sam Okoro", "Customer Education Specialist", "Customer Success", "Remote", "ChromeOS"),
    ("alicia.moreau", "Alicia Moreau", "Head of Marketing", "Marketing", "Cedar Harbor HQ", "macOS"),
    ("ben.hartley", "Ben Hartley", "Content & Social Marketer", "Marketing", "Cedar Harbor HQ", "macOS"),
    ("sienna.park", "Sienna Park", "Demand Generation Manager", "Marketing", "Remote", "macOS"),
    ("rafael.costa", "Rafael Costa", "Brand Designer", "Marketing", "Remote", "macOS"),
    ("victor.lindgren", "Victor Lindgren", "CTO", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("sofia.petrov", "Sofia Petrov", "Product Manager", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("arjun.mehta", "Arjun Mehta", "Engineering Manager", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("femi.adeyemi", "Femi Adeyemi", "Data Engineer", "Product & Engineering", "Remote", "macOS"),
    ("diego.alvarez", "Diego Alvarez", "Frontend Engineer", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("chloe.nakamura", "Chloe Nakamura", "Senior Backend Engineer", "Product & Engineering", "Remote", "macOS"),
    ("nadia.rahman", "Nadia Rahman", "Product Designer", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("lucas.weber", "Lucas Weber", "QA Engineer", "Product & Engineering", "Cedar Harbor HQ", "Windows"),
    ("riley.ford", "Riley Ford", "QA Engineer (contractor)", "Product & Engineering", "Remote", "Windows"),
    ("mila.novak", "Mila Novak", "Mobile Engineer", "Product & Engineering", "Remote", "macOS"),
    ("kenji.arai", "Kenji Arai", "Site Reliability Engineer", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("aisha.bello", "Aisha Bello", "Backend Engineer", "Product & Engineering", "Remote", "macOS"),
    ("tom.becker", "Tom Becker", "Backend Engineer", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("laura.kowalski", "Laura Kowalski", "Frontend Engineer", "Product & Engineering", "Remote", "macOS"),
    ("ravi.iyer", "Ravi Iyer", "Platform Engineer", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("jess.moreno", "Jess Moreno", "Mobile Engineer", "Product & Engineering", "Remote", "macOS"),
    ("pablo.ruiz", "Pablo Ruiz", "Backend Engineer", "Product & Engineering", "Remote", "macOS"),
    ("hana.sato", "Hana Sato", "ML Engineer (Kitewing Assist)", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("nils.eriksen", "Nils Eriksen", "Site Reliability Engineer", "Product & Engineering", "Remote", "macOS"),
    ("yusuf.kaya", "Yusuf Kaya", "Backend Engineer", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("elif.demir", "Elif Demir", "QA Engineer", "Product & Engineering", "Cedar Harbor HQ", "Windows"),
    ("maria.santos", "Maria Santos", "Frontend Engineer", "Product & Engineering", "Remote", "macOS"),
    ("ivy.chen", "Ivy Chen", "Product Manager", "Product & Engineering", "Cedar Harbor HQ", "macOS"),
    ("kai.lindqvist", "Kai Lindqvist", "Data Engineer (contractor)", "Product & Engineering", "Remote", "macOS"),
    ("erin.walsh", "Erin Walsh", "People & Culture Lead", "People & Operations", "Cedar Harbor HQ", "macOS"),
    ("noah.kim", "Noah Kim", "IT & Security Administrator", "People & Operations", "Cedar Harbor HQ", "macOS"),
    ("maya.singh", "Maya Singh", "Finance Manager", "People & Operations", "Cedar Harbor HQ", "Windows"),
    ("tessa.morgan", "Tessa Morgan", "AP & Billing Specialist", "People & Operations", "Millbrook office", "Windows"),
    ("daniel.okeke", "Daniel Okeke", "Payroll & People Ops Specialist", "People & Operations", "Cedar Harbor HQ", "Windows"),
    ("hugo.laurent", "Hugo Laurent", "IT Support Technician", "People & Operations", "Millbrook office", "Windows"),
    ("amara.nwosu", "Amara Nwosu", "Talent Acquisition Partner", "People & Operations", "Remote", "macOS"),
    ("greta.holm", "Greta Holm", "Office Manager (Millbrook)", "People & Operations", "Millbrook office", "ChromeOS"),
    ("sean.murphy", "Sean Murphy", "Financial Analyst", "People & Operations", "Cedar Harbor HQ", "Windows"),
]
assert len(D) == 62, len(D)
CONTRACTORS = {"riley.ford", "kai.lindqvist"}
PROMPT_2SV = {"riley.ford", "kai.lindqvist"}
SUPER_ADMINS = {"noah.kim", "hugo.laurent", "it-breakglass"}
SHARED = [
    ("ap", "Accounts Payable (shared mailbox)", "shared_mailbox", "Delegated to Maya Singh and Tessa Morgan; no interactive sign-in"),
    ("it-breakglass", "Break-glass super admin", "break_glass", "Security key kept in the HQ safe; sign-in alerts to Noah Kim"),
    ("scanner-millbrook", "Millbrook scan-to-email account", "device_account", "Multifunction printer; SMTP with an app password (legacy)"),
]
OS_SUFFIX = {"macOS": "mbp", "Windows": "win", "ChromeOS": "cb"}


def host(local: str, os_: str) -> str:
    first, last = local.split(".")
    if local == "riley.ford":
        return "rford-byod"
    return f"{first[0]}{last}-{OS_SUFFIX[os_]}"


HOSTS = {loc: host(loc, os_) for loc, _, _, _, _, os_ in D}

directory = []
for loc, name, title, team, office, os_ in D:
    directory.append({
        "email": f"{loc}@{DOMAIN}", "name": name, "title": title, "team": team, "office": office,
        "type": "contractor" if loc in CONTRACTORS else "employee",
        "two_step": "google_prompt" if loc in PROMPT_2SV else "security_key",
        "super_admin": loc in SUPER_ADMINS, "device": HOSTS[loc], "device_os": os_,
    })
for loc, name, kind, note in SHARED:
    directory.append({"email": f"{loc}@{DOMAIN}", "name": name, "title": note, "team": "—", "office": "—",
                      "type": kind, "two_step": {"shared_mailbox": "n/a (delegated)", "break_glass": "security_key",
                                                  "device_account": "app_password"}[kind],
                      "super_admin": loc in SUPER_ADMINS, "device": None, "device_os": None})

EXTERNAL_CONTACTS = [
    {"name": "Paolo Tessaro", "email": "paolo@tessarodesign.example", "org": "Tessaro Design Studio (vendor)"},
    {"name": "Accounts team (spoofed)", "email": "accounts@tessaro-designs.example", "org": "lookalike of Tessaro Design Studio"},
    {"name": "Reply-to drop box", "email": "tessaro.remit@relaymail.example", "org": "free relay mailbox (attacker)"},
    {"name": "Forwarding drop box", "email": "ms.archive@relaymail.example", "org": "free relay mailbox (attacker)"},
    {"name": "Phishing sender", "email": "docs-share@securedoc-viewer.example", "org": "consent-phishing sender"},
    {"name": "Ben Hartley (personal)", "email": "ben.hartley.design@personalmail.example", "org": "personal mailbox"},
    {"name": "Kai Lindqvist (own company)", "email": "kai@lindqvist-data.example", "org": "contractor's company"},
    {"name": "BillFlow AP inbox", "email": "invoices@billflow.example", "org": "sanctioned AP automation vendor"},
    {"name": "Payroll lure sender", "email": "hr-notice@payroll-kitewing.example", "org": "phishing sender (Oct 15)"},
]
FILES = [
    {"name": "Vendor bank details 2026.xlsx", "folder": "Finance/Vendors", "label": "Confidential", "owner": "maya.singh"},
    {"name": "AP remittance schedule Nov 2026.xlsx", "folder": "Finance/Vendors", "label": "Confidential", "owner": "maya.singh"},
    {"name": "Customer ARR export Q4 2026.xlsx", "folder": "Marketing/Case studies", "label": "Confidential", "owner": "ben.hartley"},
    {"name": "Q4 vendor remittance.pdf", "folder": "(phishing lure — not in Drive)", "label": "—", "owner": None},
    {"name": "Support macros v12.docx", "folder": "Support/Playbooks", "label": "Internal", "owner": "liam.oconnor"},
    {"name": "pdfconvert_setup.exe", "folder": "(downloaded to a laptop)", "label": "—", "owner": None},
    {"name": "Invoice TD-2026-1187.pdf", "folder": "Finance/Vendors/Tessaro", "label": "Internal", "owner": "maya.singh"},
]
MESSAGES = [
    "Shared document: Q4 vendor remittance",
    "Updated remittance details — invoice TD-2026-1187",
    "Payroll portal: confirm your direct deposit",
]

PH = re.compile(r"<<([uxfdm]):([^>]+)>>")


def sub(text: str) -> str:
    def rep(m):
        k, v = m.group(1), m.group(2)
        if k == "u":
            return token("user", f"{v}@{DOMAIN}")
        if k == "x":
            return token("external", v)
        if k == "f":
            return token("file", v)
        if k == "d":
            return token("device", v)
        return token("message", v)
    return PH.sub(rep, text)


def walk(o):
    if isinstance(o, dict):
        return {walk(k) if isinstance(k, str) else k: walk(v) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(x) for x in o]
    if isinstance(o, str):
        return sub(o)
    return o


def ts(day: str, hms: str) -> str:
    return f"{day}T{hms}-06:00"


# ------------------------------------------------------------------------------------------- scoring model
SCORING = {
    "base": 5,
    "alert_threshold": 60,
    "bands": [[90, "critical"], [75, "high"], [60, "medium"], [0, "info"]],
    "business_hours": "Mon-Fri 07:00-19:00 Kitewing local time (UTC-6)",
    "weights": {
        "unverified_publisher": 25, "high_risk_scope": 25, "lookalike_name": 10, "consent_via_email_link": 15,
        "after_hours": 5, "external_forwarding": 35, "hidden_filter": 25, "finance_keywords": 10,
        "created_by_app": 15, "impossible_travel": 40, "password_ok_2sv_failed": 25, "hosting_asn": 10,
        "new_country": 10, "new_location": 10, "bulk_mail_read": 25, "app_token_from_hosting_ip": 20,
        "bulk_download": 25, "sensitive_folder": 15, "external_link_on_confidential": 40, "lookalike_domain": 30,
        "newly_registered_domain": 15, "bank_change_language": 20, "reply_to_mismatch": 10,
        "references_real_invoice": 15, "credential_store_access": 40, "unsigned_binary": 15, "edr_high": 20,
        "edr_medium": 10, "exfil_to_hosting_ip": 25, "executable_download": 15, "session_replay": 40,
        "concurrent_geo": 25, "ua_mismatch": 10, "share_to_personal_address": 25, "confidential_label": 20,
        "customer_data": 15, "mfa_prompt_burst": 40, "password_ok": 15, "kerberos_preauth_burst": 45,
        "many_accounts": 20, "eol_host_no_edr": 10, "outbound_c2_pattern": 35, "server_host": 10,
        "external_sender_first_contact": 5, "mass_rename": 30, "user_reported_phish": 30,
        "phishing_category": 25, "first_seen_app": 5, "single_failure": 5,
        "known_travel": -30, "security_key_used": -10, "known_device": -10, "sanctioned_app": -10,
        "scheduled_task": -20, "inbound_scan_blocked": -5, "ad_tracker_block": -5, "dns_blocked": -10,
        "simulation": -25, "routine_auth": -10, "routine_edit": -5, "bulk_mail": -5, "spam_blocked": -5,
        "training": -5, "admin_routine": -5, "blocked_by_policy": -15, "verified_publisher": -15,
        "low_risk_scope": -10, "allowlisted": -15, "same_extension_no_entropy": -25, "change_ticket": -30,
    },
    "phrases": {
        "unverified_publisher": "app publisher is unverified", "high_risk_scope": "requests high-risk scopes (mail/Drive)",
        "lookalike_name": "app name imitates a document tool", "consent_via_email_link": "consent came from an email link",
        "after_hours": "outside business hours", "external_forwarding": "forwards mail to an external address",
        "hidden_filter": "filter skips the inbox and marks read (hides messages)", "finance_keywords": "targets invoice/payment/bank mail",
        "created_by_app": "created through a third-party app, not by the user", "impossible_travel": "impossible travel from the previous location",
        "password_ok_2sv_failed": "correct password but 2-step verification failed", "hosting_asn": "source is a hosting/VPS network",
        "new_country": "first sign-in from this country", "new_location": "first sign-in from this city",
        "bulk_mail_read": "bulk mailbox read through the API", "app_token_from_hosting_ip": "app token used from a hosting IP",
        "bulk_download": "bulk file download", "sensitive_folder": "sensitive folder (Finance/Vendors)",
        "external_link_on_confidential": "public link on a Confidential file", "lookalike_domain": "sender domain imitates a known vendor/brand",
        "newly_registered_domain": "domain registered in the last 30 days", "bank_change_language": "asks to change bank details",
        "reply_to_mismatch": "reply-to differs from the sender", "references_real_invoice": "quotes a real open invoice",
        "credential_store_access": "process read the browser credential/cookie store", "unsigned_binary": "unsigned executable",
        "edr_high": "EDR severity high", "edr_medium": "EDR severity medium", "exfil_to_hosting_ip": "upload to a hosting IP",
        "executable_download": "executable downloaded from the web", "session_replay": "session cookie replayed without a sign-in",
        "concurrent_geo": "same account active in two countries at once", "ua_mismatch": "browser fingerprint mismatch",
        "share_to_personal_address": "shared with a personal mailbox", "confidential_label": "file labelled Confidential",
        "customer_data": "contains customer data", "mfa_prompt_burst": "burst of 2-step prompts (MFA fatigue)",
        "password_ok": "password was correct", "kerberos_preauth_burst": "burst of failed Kerberos pre-authentication",
        "many_accounts": "many accounts targeted from one host", "eol_host_no_edr": "source host is end-of-life without EDR",
        "outbound_c2_pattern": "outbound beacon pattern", "server_host": "on a server", "external_sender_first_contact": "first contact from this sender",
        "mass_rename": "mass file rename", "user_reported_phish": "reported by users as phishing", "phishing_category": "DNS category: phishing",
        "first_seen_app": "first time this app is seen", "single_failure": "one failed attempt",
        "known_travel": "known travel", "security_key_used": "security key used", "known_device": "known device",
        "sanctioned_app": "sanctioned app", "scheduled_task": "scheduled job", "inbound_scan_blocked": "blocked at the perimeter",
        "ad_tracker_block": "ad/tracker block", "dns_blocked": "blocked at DNS", "simulation": "KnowBe4 simulation",
        "routine_auth": "routine authentication", "routine_edit": "owner editing", "bulk_mail": "bulk newsletter",
        "spam_blocked": "spam blocked", "training": "training activity", "admin_routine": "routine admin task",
        "blocked_by_policy": "blocked by policy", "verified_publisher": "verified publisher", "low_risk_scope": "low-risk scope",
        "allowlisted": "allowlisted", "same_extension_no_entropy": "same extensions, no encryption entropy",
        "change_ticket": "matches an approved change ticket",
    },
    "techniques": {
        "T1566.002": ["Phishing: Spearphishing Link", "Initial Access"],
        "T1528": ["Steal Application Access Token", "Credential Access"],
        "T1114.003": ["Email Collection: Email Forwarding Rule", "Collection"],
        "T1564.008": ["Hide Artifacts: Email Hiding Rules", "Defense Evasion"],
        "T1078.004": ["Valid Accounts: Cloud Accounts", "Initial Access"],
        "T1114.002": ["Email Collection: Remote Email Collection", "Collection"],
        "T1530": ["Data from Cloud Storage", "Collection"],
        "T1567.002": ["Exfiltration Over Web Service: Exfiltration to Cloud Storage", "Exfiltration"],
        "T1656": ["Impersonation", "Defense Evasion"],
        "T1204.002": ["User Execution: Malicious File", "Execution"],
        "T1555.003": ["Credentials from Web Browsers", "Credential Access"],
        "T1539": ["Steal Web Session Cookie", "Credential Access"],
        "T1041": ["Exfiltration Over C2 Channel", "Exfiltration"],
        "T1550.004": ["Use Alternate Authentication Material: Web Session Cookie", "Lateral Movement"],
        "T1621": ["Multi-Factor Authentication Request Generation", "Credential Access"],
        "T1110.003": ["Brute Force: Password Spraying", "Credential Access"],
        "T1110.004": ["Brute Force: Credential Stuffing", "Credential Access"],
        "T1219": ["Remote Access Software", "Command and Control"],
        "T1071.001": ["Application Layer Protocol: Web Protocols", "Command and Control"],
        "T1046": ["Network Service Discovery", "Discovery"],
    },
}


def score(signals: list[str]) -> int:
    return max(0, min(99, SCORING["base"] + sum(SCORING["weights"][s] for s in signals)))


# ------------------------------------------------------------------------------------------- telemetry batches
rng = random.Random(20261101)
EXT_SCANNERS = ["192.0.2.201", "192.0.2.34", "192.0.2.118", "192.0.2.77", "192.0.2.159"]
ADS = ["adserve-metrics.example", "pixel-track.example", "cdn-beacon.example", "clickstat.example"]
SANCTIONED = ["Slack", "Zoom", "DocuSign", "Kitewing FieldOps (internal)"]
HOME = {"Cedar Harbor HQ": "Cedar Harbor", "Millbrook office": "Millbrook", "Remote": "home ISP"}
LOCALS = [d[0] for d in D]
DIR = {d[0]: d for d in D}

NOISE = [
    # source, type, detail, signals, reason, night_ok, actor_kind
    ("firewall_ids", "inbound_scan_blocked", "Inbound port scan from {scanner} blocked at MB-FW01",
     ["inbound_scan_blocked"], "Internet background scan, blocked at the perimeter", True, "asset:MB-FW01"),
    ("dnsfilter", "dns_block", "Blocked ad/tracker domain {ad}", ["ad_tracker_block"],
     "Ad/tracker block — policy working as intended", True, "device"),
    ("workspace.login", "login_success", "Sign-in from {home}, security key, known device",
     ["security_key_used", "known_device"], "Routine sign-in from a known device and location", True, "user"),
    ("workspace.drive", "file_edit", "Edited an internal document they own", ["routine_edit"],
     "Owner editing an internal file", True, "user"),
    ("workspace.drive", "internal_share", "Shared a document with a colleague (internal only)", [],
     "Internal sharing", False, "user"),
    ("mimecast", "mail_delivered", "Newsletter delivered from a bulk sender (DMARC pass)", ["bulk_mail"],
     "Clean bulk mail", True, "user"),
    ("mimecast", "spam_rejected", "Spam from {scanner} rejected on reputation", ["spam_blocked"],
     "Spam blocked at the gateway", True, "user"),
    ("edr", "scan_complete", "Scheduled EDR scan completed, 0 detections", ["scheduled_task"],
     "Scheduled EDR scan", True, "device"),
    ("syslog.dc", "kerberos_routine", "Routine Kerberos ticket renewals on MB-DC01 ({n} accounts)", ["routine_auth"],
     "Routine domain authentication", True, "asset:MB-DC01"),
    ("workspace.token", "token_refresh", "Token refresh for sanctioned app {app}", ["sanctioned_app"],
     "Sanctioned app refreshing its token", True, "user"),
    ("web_proxy", "web_allowed", "Browsed business-category sites (allowed)", [], "Routine browsing", False, "device"),
    ("knowbe4", "training_completed", "Completed a security-awareness module", ["training"], "Training activity",
     False, "user"),
    ("workspace.admin", "admin_routine", "Admin viewed audit reports", ["admin_routine"], "Routine admin activity",
     False, "user:noah.kim"),
    ("workspace.login", "login_failed_then_success", "One wrong password, then success from a known device",
     ["single_failure", "known_device", "security_key_used"], "Single typo followed by a normal sign-in", True, "user"),
]


def actor_for(kind: str, avoid: set[str]) -> tuple[str, str]:
    if kind.startswith("asset:"):
        return kind.split(":", 1)[1], ""
    if kind.startswith("user:"):
        loc = kind.split(":", 1)[1]
        return f"<<u:{loc}>>", loc
    loc = rng.choice([x for x in LOCALS if x not in avoid])
    if kind == "device":
        return f"<<d:{HOSTS[loc]}>>", loc
    return f"<<u:{loc}>>", loc


def noise_events(day: str, start: str, minutes: int, n: int, night: bool, avoid: set[str], prefix: str,
                 extra: list[dict]) -> list[dict]:
    t0 = dt.datetime.fromisoformat(f"{day}T{start}")
    evs = []
    pool = [x for x in NOISE if x[5] or not night]
    for _ in range(n):
        src, typ, detail, sig, reason, _, kind = rng.choice(pool)
        actor, loc = actor_for(kind, avoid)
        t = t0 + dt.timedelta(seconds=rng.randint(0, minutes * 60 - 1))
        d = detail.format(scanner=rng.choice(EXT_SCANNERS), ad=rng.choice(ADS),
                          home=HOME[DIR[loc][4]] if loc else "", n=rng.randint(6, 18), app=rng.choice(SANCTIONED))
        sigs = list(sig)
        if night and src.startswith("workspace") and "after_hours" not in sigs and typ != "token_refresh":
            sigs.append("after_hours")
        evs.append({"ts": t.strftime("%Y-%m-%dT%H:%M:%S") + "-06:00", "src": src, "type": typ, "actor": actor,
                    "detail": d, "signals": sigs, "noise": reason})
    evs.extend(extra)
    evs.sort(key=lambda e: e["ts"])
    for i, e in enumerate(evs, 1):
        e.setdefault("id", f"EV-{prefix}-{i:03d}")
    return evs


# ---- Sunday 2026-11-01 01:30-02:30 — consent phishing -> BEC (INC-1101-01)
S = "2026-11-01"
sun_attack = [
    {"ts": ts(S, "01:33:12"), "src": "workspace.login", "type": "login_success", "actor": "<<u:dana.whitfield>>",
     "detail": "Sign-in from Lisbon, PT (on leave since 2026-10-29), security key, known device",
     "ip": "203.0.113.188", "geo": "Lisbon, PT", "signals": ["new_country", "known_travel", "security_key_used", "known_device", "after_hours"],
     "noise": "Known travel (leave noted in calendar), security key and known device"},
    {"ts": ts(S, "01:58:02"), "src": "mimecast", "type": "mail_delivered", "actor": "<<u:maya.singh>>",
     "detail": "Delivered '<<m:Shared document: Q4 vendor remittance>>' from <<x:docs-share@securedoc-viewer.example>> (domain 2 days old); URL rewritten by URL Protect; also sent to <<u:tessa.morgan>> and <<u:sean.murphy>>",
     "signals": ["newly_registered_domain", "external_sender_first_contact", "after_hours"],
     "noise": "Rewritten link from a new sender — not malicious on its own", "incident": "INC-1101-01",
     "technique": "T1566.002"},
    {"ts": ts(S, "01:58:40"), "src": "workspace.login", "type": "login_success", "actor": "<<u:maya.singh>>",
     "detail": "Sign-in from Cedar Harbor (home ISP 203.0.113.61), security key, known device <<d:msingh-win>>",
     "ip": "203.0.113.61", "geo": "Cedar Harbor, US", "signals": ["security_key_used", "known_device", "after_hours"],
     "noise": "Routine sign-in from a known device and location", "incident": "INC-1101-01"},
    {"ts": ts(S, "02:03:37"), "src": "dnsfilter", "type": "dns_allowed", "actor": "<<d:msingh-win>>",
     "detail": "Resolved securedoc-viewer.example (registered 2026-10-30, uncategorised at the time — allowed)",
     "signals": ["newly_registered_domain", "after_hours"],
     "noise": "Uncategorised new domain, allowed — no other signal yet", "incident": "INC-1101-01",
     "technique": "T1566.002"},
    {"id": "EV-1101-A1", "ts": ts(S, "02:04:11"), "src": "workspace.token", "type": "oauth_grant", "actor": "<<u:maya.singh>>",
     "detail": "Granted 'PDF Secure Viewer' (client 990417-pdfsecureviewer, publisher unverified) scopes gmail.readonly, gmail.settings.sharing, drive",
     "ip": "203.0.113.61", "signals": ["unverified_publisher", "high_risk_scope", "lookalike_name", "consent_via_email_link", "after_hours"],
     "technique": "T1528", "incident": "INC-1101-01", "triaged_s": 8},
    {"id": "EV-1101-A2", "ts": ts(S, "02:05:40"), "src": "workspace.gmail", "type": "forwarding_rule_created", "actor": "<<u:maya.singh>>",
     "detail": "Forwarding address <<x:ms.archive@relaymail.example>> added and filter created by app 'PDF Secure Viewer': subject invoice OR payment OR remittance OR bank OR wire -> forward, skip inbox, mark as read",
     "signals": ["external_forwarding", "hidden_filter", "finance_keywords", "created_by_app", "after_hours"],
     "technique": "T1114.003", "also": ["T1564.008"], "incident": "INC-1101-01", "triaged_s": 4},
    {"id": "EV-1101-A3", "ts": ts(S, "02:06:12"), "src": "workspace.login", "type": "login_2sv_failed", "actor": "<<u:maya.singh>>",
     "detail": "Password accepted, security-key challenge failed, from 198.51.100.77 (Amsterdam, NL — AS64501 hosting); previous activity Cedar Harbor 01:58:40",
     "ip": "198.51.100.77", "geo": "Amsterdam, NL",
     "signals": ["impossible_travel", "password_ok_2sv_failed", "hosting_asn", "new_country", "after_hours"],
     "technique": "T1078.004", "incident": "INC-1101-01", "triaged_s": 3},
    {"id": "EV-1101-A4", "ts": ts(S, "02:06:58"), "src": "workspace.gmail", "type": "api_bulk_read", "actor": "<<u:maya.singh>>",
     "detail": "App 'PDF Secure Viewer' read 412 messages through the Gmail API from 198.51.100.77",
     "ip": "198.51.100.77", "signals": ["bulk_mail_read", "app_token_from_hosting_ip", "unverified_publisher", "after_hours"],
     "technique": "T1114.002", "incident": "INC-1101-01", "triaged_s": 5},
    {"id": "EV-1101-A5", "ts": ts(S, "02:07:10"), "src": "mimecast", "type": "impersonation_delivered", "actor": "<<u:ap>>",
     "detail": "'<<m:Updated remittance details — invoice TD-2026-1187>>' from <<x:accounts@tessaro-designs.example>> (lookalike of tessarodesign.example, registered 2026-10-29), reply-to <<x:tessaro.remit@relaymail.example>>, to the accounts-payable shared mailbox, cc <<u:maya.singh>>; delivered with an impersonation banner",
     "signals": ["lookalike_domain", "newly_registered_domain", "bank_change_language", "reply_to_mismatch", "references_real_invoice", "after_hours"],
     "technique": "T1656", "incident": "INC-1101-01", "triaged_s": 6},
    {"id": "EV-1101-A6", "ts": ts(S, "02:07:30"), "src": "workspace.drive", "type": "api_bulk_download", "actor": "<<u:maya.singh>>",
     "detail": "App 'PDF Secure Viewer' downloaded 38 files from Finance/Vendors including <<f:Vendor bank details 2026.xlsx>>",
     "ip": "198.51.100.77", "signals": ["bulk_download", "unverified_publisher", "sensitive_folder", "after_hours"],
     "technique": "T1530", "incident": "INC-1101-01", "triaged_s": 4},
    {"id": "EV-1101-A7", "ts": ts(S, "02:07:41"), "src": "workspace.drive", "type": "public_link_created", "actor": "<<u:maya.singh>>",
     "detail": "App 'PDF Secure Viewer' set 'anyone with the link' on <<f:AP remittance schedule Nov 2026.xlsx>> and <<f:Vendor bank details 2026.xlsx>>",
     "ip": "198.51.100.77", "signals": ["external_link_on_confidential", "created_by_app", "unverified_publisher", "after_hours"],
     "technique": "T1567.002", "incident": "INC-1101-01", "triaged_s": 3},
    {"ts": ts(S, "02:08:25"), "src": "workspace.gmail", "type": "api_call_rejected", "actor": "<<u:maya.singh>>",
     "detail": "Gmail API call by 'PDF Secure Viewer' from 198.51.100.77 rejected (token revoked by PB-02) — containment verified",
     "ip": "198.51.100.77", "signals": ["blocked_by_policy", "after_hours"],
     "noise": "Rejected after containment — evidence that the revoke worked", "incident": "INC-1101-01"},
]
sun_attack = [{**e, "id": e.get("id") or f"EV-1101-X{i}"} for i, e in enumerate(sun_attack, 1)]
avoid_sun = {"maya.singh", "dana.whitfield", "tessa.morgan", "sean.murphy"}
TB1 = noise_events(S, "01:30:00", 60, 35, True, avoid_sun, "1101", sun_attack)

# ---- Wednesday 2026-10-28 14:00-15:00 — infostealer -> session hijack attempt (INC-1028-01)
W = "2026-10-28"
wed_attack = [
    {"ts": ts(W, "14:18:05"), "src": "web_proxy", "type": "file_download", "actor": "<<d:jpetit-win>>",
     "detail": "Downloaded <<f:pdfconvert_setup.exe>> from freepdfconvert-pro.example (registered 2026-10-11, uncategorised)",
     "signals": ["executable_download", "newly_registered_domain"],
     "noise": "Executable from a new domain — watched, not alerted on its own", "incident": "INC-1028-01",
     "technique": "T1204.002"},
    {"id": "EV-1028-A1", "ts": ts(W, "14:21:48"), "src": "edr", "type": "credential_store_access", "actor": "<<d:jpetit-win>>",
     "detail": "Unsigned process pdfconvert_setup.exe read the Chrome cookie and login-data stores (EDR alert ED-2210) — user <<u:jonah.petit>>",
     "signals": ["credential_store_access", "unsigned_binary", "edr_high"], "technique": "T1555.003", "also": ["T1539"],
     "incident": "INC-1028-01", "triaged_s": 6},
    {"id": "EV-1028-A2", "ts": ts(W, "14:22:30"), "src": "edr", "type": "outbound_upload", "actor": "<<d:jpetit-win>>",
     "detail": "pdfconvert_setup.exe uploaded 4.1 MB over HTTPS to 198.51.100.23 (Frankfurt, DE — AS64502 hosting) (EDR alert ED-2211)",
     "ip": "198.51.100.23", "signals": ["exfil_to_hosting_ip", "unsigned_binary", "edr_high"], "technique": "T1041",
     "incident": "INC-1028-01", "triaged_s": 5},
    {"id": "EV-1028-A3", "ts": ts(W, "14:31:02"), "src": "workspace.login", "type": "session_replay", "actor": "<<u:jonah.petit>>",
     "detail": "Stolen session cookie replayed from 198.51.100.23 (Frankfurt, DE) while the user's laptop is active in Millbrook — rejected: sessions were already revoked by PB-01 at 14:24:14",
     "ip": "198.51.100.23", "geo": "Frankfurt, DE",
     "signals": ["session_replay", "concurrent_geo", "hosting_asn", "ua_mismatch", "new_country"], "technique": "T1550.004",
     "incident": "INC-1028-01", "triaged_s": 4},
    {"id": "EV-1028-A4", "ts": ts(W, "14:31:09"), "src": "workspace.login", "type": "login_2sv_failed", "actor": "<<u:jonah.petit>>",
     "detail": "Password from the stolen browser store accepted, security-key challenge failed, from 198.51.100.23 (Frankfurt, DE); account suspended by PB-03 since 14:24:20",
     "ip": "198.51.100.23", "geo": "Frankfurt, DE",
     "signals": ["password_ok_2sv_failed", "hosting_asn", "new_country", "concurrent_geo"], "technique": "T1078.004",
     "incident": "INC-1028-01", "triaged_s": 3},
]
wed_attack = [{**e, "id": e.get("id") or f"EV-1028-X{i}"} for i, e in enumerate(wed_attack, 1)]
TB2 = noise_events(W, "14:00:00", 60, 31, False, {"jonah.petit"}, "1028", wed_attack)

# ---- Friday 2026-11-06 09:00-09:30 — this morning (INC-1106-01)
F = "2026-11-06"
fri_events = [
    {"ts": ts(F, "09:02:14"), "src": "workspace.login", "type": "login_success", "actor": "<<u:priya.natarajan>>",
     "detail": "Sign-in from Kansas City, US (customer visit in calendar), security key, known device",
     "geo": "Kansas City, US", "signals": ["new_location", "known_travel", "security_key_used", "known_device"],
     "noise": "Known travel (calendar), security key and known device"},
    {"id": "EV-1106-A1", "ts": ts(F, "09:04:22"), "src": "workspace.drive", "type": "public_link_created", "actor": "<<u:ben.hartley>>",
     "detail": "Set 'anyone with the link' on <<f:Customer ARR export Q4 2026.xlsx>> (label Confidential, 171 customer rows with ARR)",
     "signals": ["external_link_on_confidential", "customer_data"], "technique": "T1567.002",
     "incident": "INC-1106-01", "triaged_s": 5},
    {"id": "EV-1106-A2", "ts": ts(F, "09:04:40"), "src": "workspace.drive", "type": "external_share", "actor": "<<u:ben.hartley>>",
     "detail": "Shared <<f:Customer ARR export Q4 2026.xlsx>> with personal address <<x:ben.hartley.design@personalmail.example>>",
     "signals": ["share_to_personal_address", "confidential_label", "customer_data"], "technique": "T1567.002",
     "incident": "INC-1106-01", "triaged_s": 6},
    {"ts": ts(F, "09:08:15"), "src": "workspace.token", "type": "oauth_grant", "actor": "<<u:nadia.rahman>>",
     "detail": "Granted 'Diagram Helper' (verified publisher, allowlisted) scope drive.file",
     "signals": ["verified_publisher", "low_risk_scope", "allowlisted"], "noise": "Verified, allowlisted app with a file-only scope"},
    {"ts": ts(F, "09:12:02"), "src": "workspace.token", "type": "oauth_blocked", "actor": "<<u:owen.gallagher>>",
     "detail": "Consent to 'AI Meeting Notes Free' (unverified; calendar, gmail.send) blocked by the 2026-11-03 app-access policy",
     "signals": ["unverified_publisher", "high_risk_scope", "blocked_by_policy"],
     "noise": "Blocked by the new third-party app policy — no access granted"},
    {"ts": ts(F, "09:15:47"), "src": "dnsfilter", "type": "nrd_block", "actor": "<<d:fdiallo-cb>>",
     "detail": "Blocked newly registered domain parcel-track-update.example",
     "signals": ["newly_registered_domain", "dns_blocked"], "noise": "Blocked at DNS; no follow-on activity"},
    {"ts": ts(F, "09:21:10"), "src": "knowbe4", "type": "simulation_click", "actor": "<<u:theo.marsh>>",
     "detail": "Clicked a KnowBe4 simulated phishing link (campaign 'Holiday bonus', launched 2026-11-06 09:00)",
     "signals": ["simulation"], "noise": "Phishing simulation — a training event, not an attack"},
]
fri_events = [{**e, "id": e.get("id") or f"EV-1106-X{i}"} for i, e in enumerate(fri_events, 1)]
TB3 = noise_events(F, "09:00:00", 30, 27, False, {"ben.hartley"}, "1106", fri_events)


def finalize(events):
    out = []
    for e in events:
        e = dict(e)
        e["score"] = score(e["signals"])
        out.append(e)
    return out


BATCHES = {
    "TB-1101-0200": {"label": "Sunday 2026-11-01 01:30-02:30 (Kitewing local time, UTC-6)",
                     "window": [ts(S, "01:30:00"), ts(S, "02:30:00")], "raw_records": 4812,
                     "raw_by_source": {"dnsfilter": 2911, "firewall_ids": 1240, "workspace": 388, "mimecast": 141,
                                       "edr": 77, "syslog (DC + file server)": 55},
                     "doc": "sentry_alert_batch_sun0200", "events": finalize(TB1)},
    "TB-1028-1400": {"label": "Wednesday 2026-10-28 14:00-15:00 (Kitewing local time, UTC-6)",
                     "window": [ts(W, "14:00:00"), ts(W, "15:00:00")], "raw_records": 21406,
                     "raw_by_source": {"dnsfilter": 12870, "firewall_ids": 3102, "workspace": 2944, "mimecast": 1180,
                                       "web_proxy": 702, "edr": 361, "syslog (DC + file server)": 198, "knowbe4": 49},
                     "doc": None, "events": finalize(TB2)},
    "TB-1106-0900": {"label": "Friday 2026-11-06 09:00-09:30 (this morning, Kitewing local time, UTC-6)",
                     "window": [ts(F, "09:00:00"), ts(F, "09:30:00")], "raw_records": 10937,
                     "raw_by_source": {"dnsfilter": 6420, "firewall_ids": 1515, "workspace": 1630, "mimecast": 788,
                                       "web_proxy": 341, "edr": 152, "syslog (DC + file server)": 61, "knowbe4": 30},
                     "doc": None, "events": finalize(TB3)},
}
# Priya's 08:41 sign-in is before the window — move it into it as a late-arriving event? keep it but label
for b in BATCHES.values():
    for e in b["events"]:
        if e.get("technique") and e["score"] < SCORING["alert_threshold"] and "noise" not in e:
            raise SystemExit(f"technique event below threshold without noise reason: {e['id']}")

# ------------------------------------------------------------------------------------------- incidents
PLAYBOOK_TIMING = {"PB-01": (1, 3), "PB-02": (2, 5), "PB-04": (3, None), "PB-03": (5, 5)}


def pb_window(authorised: str, pb: str, files: int = 0) -> tuple[str, str]:
    a = dt.datetime.fromisoformat(authorised)
    off, dur = PLAYBOOK_TIMING[pb]
    dur = dur if dur is not None else 2 + 12 * max(1, files)
    s = a + dt.timedelta(seconds=off)
    return s.isoformat(), (s + dt.timedelta(seconds=dur)).isoformat()


INCIDENTS = [
    {
        "id": "INC-1101-01", "title": "Consent phishing -> hidden mail forwarding -> vendor payment-diversion (BEC) attempt",
        "category": "identity / OAuth / email", "severity": "critical", "status": "contained",
        "batch": "TB-1101-0200", "primary_actor": "<<u:maya.singh>>", "actor_role": "Finance Manager (finance team)",
        "analyst": "A-17 (certified Wursta SOC analyst, Tier 2)",
        "first_malicious": ts(S, "02:04:11"), "first_alert": ts(S, "02:04:19"), "opened": ts(S, "02:05:44"),
        "analyst_ack": ts(S, "02:06:20"), "confirmed": ts(S, "02:07:52"), "authorised": ts(S, "02:07:52"),
        "attack_path": [
            ["T1566.002", "Consent-phishing email 'Shared document: Q4 vendor remittance' from a 2-day-old domain (01:58)"],
            ["T1528", "User granted the unverified 'PDF Secure Viewer' app mail-read, mail-settings and full-Drive scopes (02:04)"],
            ["T1114.003", "App added an external forwarding address and a finance-keyword filter (02:05)"],
            ["T1564.008", "Filter skips the inbox and marks messages read, so the user never sees replies"],
            ["T1078.004", "Password sign-in from Amsterdam 8 minutes after a Cedar Harbor sign-in — stopped by the security key (02:06)"],
            ["T1114.002", "412 messages read through the Gmail API (02:06)"],
            ["T1656", "Lookalike-vendor email asks AP to change bank details for open invoice TD-2026-1187 (02:07)"],
            ["T1530", "38 files downloaded from Finance/Vendors (02:07)"],
            ["T1567.002", "Public links created on 2 Confidential finance files (02:07)"],
        ],
        "blast_radius": {
            "users": ["<<u:maya.singh>>"], "ap_shared_mailbox_targeted": "<<u:ap>>",
            "phish_recipients_not_compromised": ["<<u:tessa.morgan>>", "<<u:sean.murphy>>"],
            "apps": [{"app": "PDF Secure Viewer", "client_id": "990417-pdfsecureviewer", "users": 1}],
            "mail_rules": [{"mailbox": "<<u:maya.singh>>", "forward_to": "<<x:ms.archive@relaymail.example>>", "messages_forwarded": 1}],
            "messages_read": 412, "files_downloaded": 38,
            "files_public": ["<<f:Vendor bank details 2026.xlsx>>", "<<f:AP remittance schedule Nov 2026.xlsx>>"],
            "external_views_of_public_links": 0,
            "devices": [{"device": "<<d:msingh-win>>", "edr": "clean (full scan 02:20)"}],
            "money_at_risk": {"invoice": "TD-2026-1187", "vendor": "Tessaro Design Studio", "amount_usd": 48600, "due": "2026-11-10"},
        },
        "iocs": {"domains": ["securedoc-viewer.example", "tessaro-designs.example", "relaymail.example"],
                 "ips": ["198.51.100.77 (AS64501, hosting, Amsterdam NL)"], "oauth_client_ids": ["990417-pdfsecureviewer"],
                 "addresses": ["<<x:ms.archive@relaymail.example>>", "<<x:accounts@tessaro-designs.example>>", "<<x:tessaro.remit@relaymail.example>>"]},
        "analyst_checklist": [
            ["Is 'PDF Secure Viewer' an approved app?", "No — unverified publisher, domain 2 days old, not on the allowlist"],
            ["Did anyone else grant it?", "No — 1 grant; the 2 other recipients did not click"],
            ["Did the Amsterdam sign-in succeed?", "No — the security-key challenge failed"],
            ["What left through the forwarding rule?", "1 message (the attacker's own bank-change email)"],
            ["Which files were exposed?", "38 downloaded through the API; 2 public links, 0 external views"],
            ["Is a payment due to the impersonated vendor?", "Yes — TD-2026-1187, $48,600, due 2026-11-10: finance must hold it"],
            ["Was internal phishing sent from the mailbox?", "No messages sent through the app"],
        ],
        "recommended_playbooks": [
            {"playbook": "PB-01", "target": "<<u:maya.singh>>", "why": "end every web session and token the attacker may hold"},
            {"playbook": "PB-02", "target": "PDF Secure Viewer", "why": "revoke the app tenant-wide and block its client id"},
            {"playbook": "PB-04", "target": "2 public files", "why": "remove the public links"},
            {"playbook": "PB-03", "target": "<<u:maya.singh>>", "why": "suspend 4 h until the password is reset (security key kept)"},
        ],
        "escalate": [
            "Remove the forwarding filter and forwarding address (mail-rule change is not pre-approved)",
            "Reset the user's password (client IT)",
            "Hold payment of TD-2026-1187 and verify the vendor's bank details by phone on file (client finance)",
            "Block tessaro-designs.example, securedoc-viewer.example and relaymail.example in Mimecast and DNSFilter (client approval)",
        ],
        "client_actions": [
            [ts(S, "02:09:05"), "Analyst A-17 phoned Noah Kim (client on-call) and paged Marcus Bell for the payment hold"],
            [ts(S, "02:24:30"), "Noah Kim removed the filter and forwarding address"],
            [ts(S, "02:31:10"), "Password reset; account unsuspended at 06:10 after the user confirmed by phone"],
            ["2026-11-02T09:00:00-06:00", "External auto-forwarding disabled domain-wide (posture fix)"],
            ["2026-11-02T10:15:00-06:00", "Marcus Bell verified with Tessaro by phone: no bank change; TD-2026-1187 paid to the account on file on 2026-11-04"],
            ["2026-11-03T11:00:00-06:00", "Third-party app access restricted: unverified apps blocked, 14-app allowlist"],
        ],
        "outcome": "Contained in 29 s after analyst confirmation; payment diversion of $48,600 prevented; $0 lost; no external views of the public links.",
        "funds_at_risk_usd": 48600, "funds_lost_usd": 0, "files_quarantined": 2,
        "soc_payload": {"egress_bytes": 2318, "fields": ["incident id", "user token", "app name + client id + scopes",
                                                       "forward-to token", "file tokens", "message-subject tokens",
                                                       "IPs, ASN, geo", "timestamps", "ATT&CK techniques", "scores"]},
    },
    {
        "id": "INC-1028-01", "title": "Infostealer on a support laptop -> stolen session cookie replay (blocked)",
        "category": "endpoint / identity", "severity": "critical", "status": "contained",
        "batch": "TB-1028-1400", "primary_actor": "<<u:jonah.petit>>", "actor_role": "Support Specialist (Millbrook)",
        "analyst": "A-09 (certified Wursta SOC analyst, Tier 2)",
        "first_malicious": ts(W, "14:21:48"), "first_alert": ts(W, "14:21:54"), "opened": ts(W, "14:21:58"),
        "analyst_ack": ts(W, "14:22:35"), "confirmed": ts(W, "14:24:10"), "authorised": ts(W, "14:24:10"),
        "attack_path": [
            ["T1204.002", "User ran 'pdfconvert_setup.exe' downloaded from a 17-day-old PDF-converter site (14:18)"],
            ["T1555.003", "Unsigned process read the Chrome login-data store (14:21)"],
            ["T1539", "...and the cookie store, stealing live web-session cookies"],
            ["T1041", "4.1 MB uploaded to 198.51.100.23, Frankfurt (14:22)"],
            ["T1550.004", "Stolen cookie replayed from Frankfurt at 14:31 — rejected, sessions already revoked at 14:24"],
            ["T1078.004", "Stolen password tried at 14:31 — security key and suspension blocked it"],
        ],
        "blast_radius": {
            "users": ["<<u:jonah.petit>>"], "devices": [{"device": "<<d:jpetit-win>>", "edr": "infostealer — isolated 14:38, reimaged 2026-10-29"}],
            "saved_browser_passwords": 4, "apps": [], "files_downloaded": 0, "files_public": [],
            "messages_read": 0, "money_at_risk": None,
        },
        "iocs": {"domains": ["freepdfconvert-pro.example"], "ips": ["198.51.100.23 (AS64502, hosting, Frankfurt DE)"],
                 "files": ["<<f:pdfconvert_setup.exe>> (unsigned)"]},
        "analyst_checklist": [
            ["Is the EDR detection a true positive?", "Yes — unsigned binary read browser credential and cookie stores"],
            ["Was data sent out?", "Yes — 4.1 MB to a hosting IP: assume cookies and saved passwords are stolen"],
            ["Which accounts are exposed?", "The user's Workspace session + 4 saved SaaS passwords"],
            ["Is the device still online?", "Yes — isolation needs the client (not pre-approved)"],
        ],
        "recommended_playbooks": [
            {"playbook": "PB-01", "target": "<<u:jonah.petit>>", "why": "invalidate every stolen session cookie and token"},
            {"playbook": "PB-03", "target": "<<u:jonah.petit>>", "why": "suspend 4 h until the password is reset"},
        ],
        "escalate": [
            "Isolate the laptop with the EDR console (device isolation is not pre-approved)",
            "Rotate the 4 saved SaaS passwords and reset the Workspace password (client IT)",
            "Block 198.51.100.23 and freepdfconvert-pro.example (client approval)",
        ],
        "client_actions": [
            [ts(W, "14:25:00"), "Analyst A-09 called Hugo Laurent (Millbrook IT)"],
            [ts(W, "14:38:20"), "Hugo Laurent isolated the laptop in the EDR console"],
            [ts(W, "16:05:00"), "Passwords rotated; freepdfconvert-pro.example blocked in DNSFilter"],
            ["2026-10-29T10:30:00-06:00", "Laptop reimaged and returned"],
        ],
        "outcome": "Sessions revoked 7 minutes before the attacker tried the stolen cookie; replay and password sign-in both failed; no data accessed in Workspace.",
        "funds_at_risk_usd": 0, "funds_lost_usd": 0, "files_quarantined": 0,
        "soc_payload": {"egress_bytes": 1544, "fields": ["incident id", "user token", "device token", "process + hash",
                                                       "IPs, ASN, geo", "timestamps", "ATT&CK techniques", "scores"]},
    },
    {
        "id": "INC-1106-01", "title": "Confidential customer ARR export shared publicly and to a personal mailbox",
        "category": "data exposure (Drive)", "severity": "medium", "status": "open — PB-04 recommended, awaiting containment",
        "batch": "TB-1106-0900", "primary_actor": "<<u:ben.hartley>>", "actor_role": "Content & Social Marketer",
        "analyst": "A-21 (certified Wursta SOC analyst, Tier 1)",
        "first_malicious": ts(F, "09:04:22"), "first_alert": ts(F, "09:04:27"), "opened": ts(F, "09:04:50"),
        "analyst_ack": ts(F, "09:05:30"), "confirmed": ts(F, "09:07:05"), "authorised": ts(F, "09:07:05"),
        "attack_path": [
            ["T1567.002", "Confidential export (171 customer rows with ARR) set to 'anyone with the link' (09:04)"],
            ["T1567.002", "Same file shared with a personal mailbox (09:04)"],
        ],
        "blast_radius": {
            "users": ["<<u:ben.hartley>>"], "files_public": ["<<f:Customer ARR export Q4 2026.xlsx>>"],
            "external_recipients": ["<<x:ben.hartley.design@personalmail.example>>"], "external_views_of_public_links": 0,
            "apps": [], "messages_read": 0, "files_downloaded": 0, "money_at_risk": None,
        },
        "iocs": {},
        "analyst_checklist": [
            ["Malicious or accidental?", "Accidental — the owner is preparing case-study numbers; no other risky activity"],
            ["Was the link opened externally?", "No — 0 external views so far"],
            ["Is the file Confidential?", "Yes — label Confidential, customer ARR for 171 accounts"],
        ],
        "recommended_playbooks": [
            {"playbook": "PB-04", "target": "<<f:Customer ARR export Q4 2026.xlsx>>", "why": "remove the public link and the personal-mailbox share"},
        ],
        "escalate": [
            "Tell the user's manager (Alicia Moreau) and remind the user of the sharing policy (client)",
            "Change the Marketing OU default link sharing to 'restricted' (domain setting — client admin)",
        ],
        "client_actions": [],
        "outcome": "Open: PB-04 recommended; no external views yet.",
        "funds_at_risk_usd": 0, "funds_lost_usd": 0, "files_quarantined": 0,
        "soc_payload": {"egress_bytes": 911, "fields": ["incident id", "user token", "file token", "recipient token",
                                                      "label", "row count", "timestamps", "scores"]},
    },
    {
        "id": "INC-1015-01", "title": "Payroll-lure credential-harvest phishing wave (no compromise)",
        "category": "email", "severity": "medium", "status": "resolved",
        "batch": None, "primary_actor": "<<u:owen.gallagher>>", "actor_role": "Sales Development Representative (clicked; page blocked)",
        "analyst": "A-21 (certified Wursta SOC analyst, Tier 1)",
        "first_malicious": "2026-10-15T10:12:03-06:00", "first_alert": "2026-10-15T10:13:46-06:00",
        "opened": "2026-10-15T10:13:50-06:00", "analyst_ack": "2026-10-15T10:14:30-06:00",
        "confirmed": "2026-10-15T10:16:20-06:00", "authorised": None,
        "attack_path": [["T1566.002", "14 users received 'Payroll portal: confirm your direct deposit' from payroll-kitewing.example"],
                        ["T1566.002", "1 click (page blocked by DNSFilter, phishing category); 6 users reported it with the KnowBe4 button"]],
        "blast_radius": {"users": ["<<u:owen.gallagher>>"], "recipients": 14, "clicks": 1, "credentials_entered": 0,
                         "apps": [], "files_public": [], "money_at_risk": None},
        "iocs": {"domains": ["payroll-kitewing.example"], "addresses": ["<<x:hr-notice@payroll-kitewing.example>>"]},
        "analyst_checklist": [["Did anyone enter credentials?", "No — the only click was blocked at DNS"]],
        "recommended_playbooks": [],
        "escalate": ["Purge the 14 messages from mailboxes with Mimecast (message purge is not pre-approved)"],
        "client_actions": [["2026-10-15T10:19:02-06:00", "Noah Kim approved the purge in chat"],
                           ["2026-10-15T10:21:40-06:00", "Analyst purged 14 messages"]],
        "outcome": "No compromise; 14 messages purged 8 minutes after the first report.",
        "funds_at_risk_usd": 0, "funds_lost_usd": 0, "files_quarantined": 0,
        "events": [
            {"id": "EV-1015-A1", "ts": "2026-10-15T10:12:03-06:00", "src": "mimecast", "type": "mail_delivered", "actor": "<<u:owen.gallagher>>",
             "detail": "'<<m:Payroll portal: confirm your direct deposit>>' delivered to 14 users from <<x:hr-notice@payroll-kitewing.example>>",
             "signals": ["lookalike_domain", "newly_registered_domain", "external_sender_first_contact"], "technique": "T1566.002"},
            {"id": "EV-1015-A2", "ts": "2026-10-15T10:13:40-06:00", "src": "knowbe4", "type": "phish_reported", "actor": "<<u:tessa.morgan>>",
             "detail": "3 users reported the message with the Phish Alert Button within 90 s",
             "signals": ["user_reported_phish", "lookalike_domain", "newly_registered_domain"], "technique": "T1566.002", "triaged_s": 6},
            {"id": "EV-1015-A3", "ts": "2026-10-15T10:14:05-06:00", "src": "dnsfilter", "type": "phishing_block", "actor": "<<d:ogallagher-win>>",
             "detail": "Click to payroll-kitewing.example blocked (category phishing)",
             "signals": ["phishing_category", "lookalike_domain", "newly_registered_domain", "dns_blocked"], "technique": "T1566.002", "triaged_s": 5},
        ],
    },
    {
        "id": "INC-1021-01", "title": "MFA-fatigue push bombing against a contractor account",
        "category": "identity", "severity": "high", "status": "contained",
        "batch": None, "primary_actor": "<<u:riley.ford>>", "actor_role": "QA Engineer (contractor, Google prompt — security key pending)",
        "analyst": "A-17 (certified Wursta SOC analyst, Tier 2)",
        "first_malicious": "2026-10-21T23:10:02-06:00", "first_alert": "2026-10-21T23:12:31-06:00",
        "opened": "2026-10-21T23:12:35-06:00", "analyst_ack": "2026-10-21T23:13:10-06:00",
        "confirmed": "2026-10-21T23:13:55-06:00", "authorised": "2026-10-21T23:13:55-06:00",
        "attack_path": [["T1110.004", "Password from a third-party breach used from 198.51.100.140 (Singapore, hosting)"],
                        ["T1621", "11 Google prompts in 4 minutes; the user denied all of them"]],
        "blast_radius": {"users": ["<<u:riley.ford>>"], "successful_sign_ins": 0, "apps": [], "files_public": [], "money_at_risk": None},
        "iocs": {"ips": ["198.51.100.140 (AS64503, hosting, Singapore SG)"]},
        "analyst_checklist": [["Did any prompt get approved?", "No — 11 denied"], ["Is the password known to the attacker?", "Yes — reset needed"]],
        "recommended_playbooks": [
            {"playbook": "PB-01", "target": "<<u:riley.ford>>", "why": "end any session, just in case"},
            {"playbook": "PB-03", "target": "<<u:riley.ford>>", "why": "suspend 4 h to stop the prompts until the password is reset"}],
        "escalate": ["Reset the password and ship a security key (client IT)"],
        "client_actions": [["2026-10-22T08:30:00-06:00", "Password reset; security key ordered (arrives 2026-11-09)"]],
        "outcome": "Prompts stopped within 4 minutes of the first one; no sign-in succeeded.",
        "funds_at_risk_usd": 0, "funds_lost_usd": 0, "files_quarantined": 0,
        "events": [
            {"id": "EV-1021-A1", "ts": "2026-10-21T23:12:31-06:00", "src": "workspace.login", "type": "mfa_prompt_burst", "actor": "<<u:riley.ford>>",
             "detail": "5th Google prompt in 150 s after correct passwords from 198.51.100.140 (Singapore, hosting); all denied",
             "ip": "198.51.100.140", "geo": "Singapore, SG",
             "signals": ["mfa_prompt_burst", "password_ok", "hosting_asn", "new_country", "after_hours"], "technique": "T1621", "triaged_s": 4},
        ],
    },
    {
        "id": "INC-1023-01", "title": "Legacy remote-access tool on the Millbrook file server beaconing to a re-registered domain",
        "category": "on-prem server", "severity": "medium", "status": "resolved",
        "batch": None, "primary_actor": "MB-FS01", "actor_role": "Legacy file server (Windows Server 2016)",
        "analyst": "A-09 (certified Wursta SOC analyst, Tier 2)",
        "first_malicious": "2026-10-23T03:12:03-06:00", "first_alert": "2026-10-23T03:12:09-06:00",
        "opened": "2026-10-23T03:12:12-06:00", "analyst_ack": "2026-10-23T03:13:00-06:00",
        "confirmed": "2026-10-23T03:15:30-06:00", "authorised": None,
        "attack_path": [["T1219", "'LegacyRemote 6' support agent left by a former IT provider tried to self-update"],
                        ["T1071.001", "Update domain had changed owner (re-registered 2026-10-20); DNSFilter and the IDS blocked it"]],
        "blast_radius": {"servers": ["MB-FS01"], "data_sent": "none (blocked)", "apps": [], "files_public": [], "money_at_risk": None},
        "iocs": {"domains": ["update-check.cdn-mirror.example"]},
        "analyst_checklist": [["Did any connection succeed?", "No — blocked at DNS and at the firewall"]],
        "recommended_playbooks": [],
        "escalate": ["Uninstall LegacyRemote 6 from MB-FS01 (server change — client IT, business hours)"],
        "client_actions": [["2026-10-23T10:40:00-06:00", "Hugo Laurent uninstalled the tool"]],
        "outcome": "Blocked by preventive controls in real time; tool removed the same morning.",
        "funds_at_risk_usd": 0, "funds_lost_usd": 0, "files_quarantined": 0,
        "events": [
            {"id": "EV-1023-A1", "ts": "2026-10-23T03:12:03-06:00", "src": "dnsfilter", "type": "nrd_block", "actor": "MB-FS01",
             "detail": "MB-FS01 lookup of update-check.cdn-mirror.example blocked (newly registered / malware)",
             "signals": ["newly_registered_domain", "dns_blocked", "server_host", "outbound_c2_pattern", "after_hours"], "technique": "T1071.001", "triaged_s": 6},
            {"id": "EV-1023-A2", "ts": "2026-10-23T03:12:04-06:00", "src": "firewall_ids", "type": "ids_block", "actor": "MB-FS01",
             "detail": "IDS signature 'LegacyRemote outdated agent update' — outbound connection blocked at MB-FW01",
             "signals": ["outbound_c2_pattern", "server_host", "unsigned_binary", "after_hours"], "technique": "T1219", "triaged_s": 5},
        ],
    },
    {
        "id": "INC-1030-01", "title": "Password spray against the Millbrook domain controller from an end-of-life reception PC",
        "category": "on-prem identity", "severity": "high", "status": "contained",
        "batch": None, "primary_actor": "MB-WS07", "actor_role": "Reception PC (Windows 10, out of support, no EDR)",
        "analyst": "A-17 (certified Wursta SOC analyst, Tier 2)",
        "first_malicious": "2026-10-30T22:47:12-06:00", "first_alert": "2026-10-30T22:47:40-06:00",
        "opened": "2026-10-30T22:47:44-06:00", "analyst_ack": "2026-10-30T22:48:20-06:00",
        "confirmed": "2026-10-30T22:50:05-06:00", "authorised": None,
        "attack_path": [["T1110.003", "312 failed Kerberos pre-authentications against 41 AD accounts in 11 minutes from MB-WS07"]],
        "blast_radius": {"hosts": ["MB-WS07", "MB-DC01"], "ad_accounts_targeted": 41, "successful_logons": 0, "lockouts": 6,
                         "apps": [], "files_public": [], "money_at_risk": None},
        "iocs": {"hosts": ["MB-WS07"]},
        "analyst_checklist": [["Any successful logon?", "No"], ["Is the source host managed?", "No EDR, Windows 10 out of support"]],
        "recommended_playbooks": [],
        "escalate": ["Isolate MB-WS07 from the network (on-prem device isolation is not pre-approved)"],
        "client_actions": [["2026-10-30T23:31:00-06:00", "Hugo Laurent disabled the switch port (P2 phone escalation)"],
                           ["2026-10-31T08:15:00-06:00", "PC removed; forensic image found a commodity loader from a USB stick"]],
        "outcome": "No account compromised; 41 minutes from confirmation to isolation because on-prem isolation needs the client.",
        "funds_at_risk_usd": 0, "funds_lost_usd": 0, "files_quarantined": 0,
        "events": [
            {"id": "EV-1030-A1", "ts": "2026-10-30T22:47:40-06:00", "src": "syslog.dc", "type": "kerberos_preauth_burst", "actor": "MB-WS07",
             "detail": "Burst of failed Kerberos pre-authentication (4771) and logon failures (4625) on MB-DC01 for 41 accounts from MB-WS07",
             "signals": ["kerberos_preauth_burst", "many_accounts", "eol_host_no_edr", "after_hours"], "technique": "T1110.003", "triaged_s": 28},
        ],
    },
]

# containment windows computed from the playbook timing (same rule as the tool)
for inc in INCIDENTS:
    rows = []
    if inc["authorised"]:
        for r in inc["recommended_playbooks"]:
            files = len(inc["blast_radius"].get("files_public") or []) if r["playbook"] == "PB-04" else 0
            s, e = pb_window(inc["authorised"], r["playbook"], files)
            rows.append({"playbook": r["playbook"], "target": r["target"], "start": s, "end": e})
    if inc["status"].startswith("contained") or inc["status"] == "resolved":
        inc["containment"] = rows
        if rows:
            inc["contained_at"] = max(r["end"] for r in rows)
            inc["contained_by"] = "pre-approved playbooks " + ", ".join(r["playbook"] for r in rows)
    else:
        inc["containment"] = []
        inc["planned_containment"] = rows
ESCALATION_CONTAINED = {
    "INC-1015-01": ("2026-10-15T10:21:40-06:00", "escalation — analyst purged the messages after client approval"),
    "INC-1023-01": ("2026-10-23T03:12:04-06:00", "preventive controls — DNSFilter and the IDS blocked the beacon"),
    "INC-1030-01": ("2026-10-30T23:31:00-06:00", "escalation — client IT disabled the switch port"),
}
for inc in INCIDENTS:
    if inc["id"] in ESCALATION_CONTAINED:
        inc["contained_at"], inc["contained_by"] = ESCALATION_CONTAINED[inc["id"]]

# --------------------------------------------------------------------------------------------- identity
GEO = {"Cedar Harbor, US": [41.88, -87.95], "Millbrook, US": [41.70, -88.30], "Amsterdam, NL": [52.37, 4.90],
       "Frankfurt, DE": [50.11, 8.68], "Singapore, SG": [1.35, 103.82], "Lisbon, PT": [38.72, -9.14],
       "Denver, US": [39.74, -104.99], "Kansas City, US": [39.10, -94.58], "unknown (192.0.2.66)": None}

IDENTITY = {
    "window": "2026-10-08 to 2026-11-06 (since WAISentry go-live)",
    "geo": GEO,
    "detections": [
        {"id": "ID-01", "ts": ts(S, "02:04:11"), "type": "risky_oauth_consent", "user": "<<u:maya.singh>>", "severity": "high",
         "technique": "T1528", "status": "contained — app revoked 02:07:59 (PB-02)", "incident": "INC-1101-01",
         "evidence": "Unverified 'PDF Secure Viewer' granted gmail.readonly, gmail.settings.sharing, drive from an email link"},
        {"id": "ID-02", "ts": ts(S, "02:05:40"), "type": "hidden_forwarding_rule", "user": "<<u:maya.singh>>", "severity": "critical",
         "technique": "T1114.003", "status": "removed by client 02:24:30", "incident": "INC-1101-01",
         "evidence": "Filter on invoice/payment/bank keywords forwards to <<x:ms.archive@relaymail.example>>, skips inbox, marks read; created by an app"},
        {"id": "ID-03", "ts": ts(S, "02:06:12"), "type": "impossible_travel", "user": "<<u:maya.singh>>", "severity": "critical",
         "technique": "T1078.004", "status": "blocked by security key", "incident": "INC-1101-01",
         "travel": {"from": "Cedar Harbor, US", "from_ts": ts(S, "01:58:40"), "to": "Amsterdam, NL", "to_ts": ts(S, "02:06:12"),
                    "to_ip": "198.51.100.77 (AS64501 hosting)"},
         "evidence": "Password accepted, security-key challenge failed"},
        {"id": "ID-04", "ts": ts(S, "02:07:10"), "type": "bec_impersonation", "user": "<<u:ap>>", "severity": "critical",
         "technique": "T1656", "status": "payment held; vendor verified by phone 2026-11-02", "incident": "INC-1101-01",
         "evidence": "Lookalike vendor domain asks the accounts-payable shared mailbox to change bank details for open invoice TD-2026-1187 ($48,600)"},
        {"id": "ID-05", "ts": ts(W, "14:31:02"), "type": "session_hijack_attempt", "user": "<<u:jonah.petit>>", "severity": "critical",
         "technique": "T1550.004", "status": "blocked — sessions revoked 14:24:14 (PB-01)", "incident": "INC-1028-01",
         "travel": {"from": "Millbrook, US", "from_ts": ts(W, "14:30:40"), "to": "Frankfurt, DE", "to_ts": ts(W, "14:31:02"),
                    "to_ip": "198.51.100.23 (AS64502 hosting)", "concurrent": True},
         "evidence": "Stolen cookie replayed with a different browser fingerprint while the laptop was active in Millbrook"},
        {"id": "ID-06", "ts": "2026-10-21T23:10:02-06:00", "type": "mfa_fatigue", "user": "<<u:riley.ford>>", "severity": "high",
         "technique": "T1621", "status": "contained — suspended 23:14:05 (PB-03)", "incident": "INC-1021-01",
         "evidence": "11 Google prompts in 4 minutes from 198.51.100.140 (Singapore, hosting); all denied; password was correct"},
        {"id": "ID-07", "ts": "2026-11-04T03:20:00-06:00", "type": "credential_stuffing", "user": "5 sales accounts", "severity": "low",
         "technique": "T1110.004", "status": "resolved — 0 successes, blocked by login challenges",
         "users": ["<<u:owen.gallagher>>", "<<u:theo.marsh>>", "<<u:isla.brennan>>", "<<u:priya.natarajan>>", "<<u:ethan.caldwell>>"],
         "evidence": "23 failed passwords in 9 minutes from 192.0.2.66; addresses match the public website team page"},
        {"id": "ID-08", "ts": "2026-10-29T07:40:00-06:00", "type": "new_country_known_travel", "user": "<<u:dana.whitfield>>", "severity": "info",
         "technique": None, "status": "suppressed — known travel",
         "travel": {"from": "Cedar Harbor, US", "from_ts": "2026-10-28T17:55:00-06:00", "to": "Lisbon, PT", "to_ts": "2026-10-29T07:40:00-06:00", "to_ip": "203.0.113.188"},
         "evidence": "Leave in calendar; security key; known device"},
        {"id": "ID-09", "ts": "2026-10-27T08:05:00-06:00", "type": "new_location_known_travel", "user": "<<u:jamie.cho>>", "severity": "info",
         "technique": None, "status": "suppressed — trade show in calendar",
         "travel": {"from": "Cedar Harbor, US", "from_ts": "2026-10-26T18:10:00-06:00", "to": "Denver, US", "to_ts": "2026-10-27T08:05:00-06:00", "to_ip": "203.0.113.92"},
         "evidence": "Trade show 2026-10-27 to 10-29; security key; known device; hotel Wi-Fi"},
        {"id": "ID-10", "ts": "2026-11-06T09:02:14-06:00", "type": "new_location_known_travel", "user": "<<u:priya.natarajan>>", "severity": "info",
         "technique": None, "status": "suppressed — customer visit in calendar",
         "travel": {"from": "Cedar Harbor, US", "from_ts": "2026-11-05T17:20:00-06:00", "to": "Kansas City, US", "to_ts": "2026-11-06T09:02:14-06:00", "to_ip": "203.0.113.140"},
         "evidence": "Customer visit; security key; known device"},
        {"id": "ID-11", "ts": "2026-11-03T08:12:00-06:00", "type": "super_admin_new_device", "user": "<<u:noah.kim>>", "severity": "info",
         "technique": None, "status": "verified benign — replacement laptop (ticket IT-1093)",
         "evidence": "Super-admin sign-in from a new enrolled device with a security key"},
    ],
    "mail_rules": [
        {"id": "MR-01", "mailbox": "<<u:maya.singh>>", "kind": "filter + forwarding address", "forward_to": "<<x:ms.archive@relaymail.example>>",
         "external": True, "hides_mail": True, "criteria": "subject: invoice OR payment OR remittance OR bank OR wire",
         "created": ts(S, "02:05:40"), "created_by": "app 'PDF Secure Viewer'", "status": "removed 2026-11-01 02:24:30",
         "risk": "critical", "incident": "INC-1101-01"},
        {"id": "MR-02", "mailbox": "<<u:ben.hartley>>", "kind": "auto-forward all mail", "forward_to": "<<x:ben.hartley.design@personalmail.example>>",
         "external": True, "hides_mail": False, "criteria": "all mail", "created": "2025-09-12T16:20:00-06:00", "created_by": "user",
         "status": "still configured — blocked since 2026-11-02 by the domain policy", "risk": "medium"},
        {"id": "MR-03", "mailbox": "<<u:ap>>", "kind": "filter forward", "forward_to": "<<x:invoices@billflow.example>>",
         "external": True, "hides_mail": False, "criteria": "has attachment AND subject: invoice", "created": "2024-03-04T09:00:00-06:00",
         "created_by": "Noah Kim (AP automation)", "status": "active — allowlisted exception approved by Marcus Bell 2026-11-02", "risk": "low"},
        {"id": "MR-04", "mailbox": "<<u:kai.lindqvist>>", "kind": "forwarding address (no rule)", "forward_to": "<<x:kai@lindqvist-data.example>>",
         "external": True, "hides_mail": False, "criteria": "—", "created": "2026-06-02T11:00:00-06:00", "created_by": "user",
         "status": "inactive — blocked by the domain policy", "risk": "low"},
        {"id": "MR-05", "mailbox": "<<u:lena.okafor>>", "kind": "filter", "forward_to": None, "external": False, "hides_mail": True,
         "criteria": "from: newsletters -> skip inbox, label 'Reading'", "created": "2025-01-20T08:00:00-06:00", "created_by": "user",
         "status": "active", "risk": "none"},
        {"id": "MR-06", "mailbox": "<<u:liam.oconnor>>", "kind": "filter forward (internal)", "forward_to": "<<u:support-escalations>>",
         "external": False, "hides_mail": False, "criteria": "subject: [P1]", "created": "2025-05-14T10:00:00-06:00", "created_by": "user",
         "status": "active", "risk": "none"},
    ],
    "domain_policy": {"external_auto_forwarding": "disabled since 2026-11-02 (allowlist: billflow.example)",
                      "before": "allowed for all users until 2026-11-02"},
    "vendors": [
        {"vendor": "Tessaro Design Studio", "domain": "tessarodesign.example", "contact": "<<x:paolo@tessarodesign.example>>",
         "phone_on_file": "+1-555-0142", "bank_on_file": "account ending 4471", "open_invoices": [{"invoice": "TD-2026-1187", "amount_usd": 48600, "due": "2026-11-10"}]},
        {"vendor": "Brightline Hosting", "domain": "brightlinehosting.example", "phone_on_file": "+1-555-0177",
         "bank_on_file": "account ending 2290", "open_invoices": [{"invoice": "BH-311", "amount_usd": 9800, "due": "2026-11-15"}]},
        {"vendor": "Northgate Office Supply", "domain": "northgateoffice.example", "phone_on_file": "+1-555-0110",
         "bank_on_file": "account ending 7315", "open_invoices": [{"invoice": "NG-88412", "amount_usd": 2140, "due": "2026-11-20"}]},
        {"vendor": "BillFlow", "domain": "billflow.example", "phone_on_file": "+1-555-0199", "bank_on_file": "card on file",
         "open_invoices": []},
    ],
    "domain_intel": {
        "tessaro-designs.example": {"registered": "2026-10-29", "note": "lookalike of tessarodesign.example"},
        "securedoc-viewer.example": {"registered": "2026-10-30", "note": "consent-phishing landing page"},
        "relaymail.example": {"registered": "2019-04-02", "note": "free anonymous relay mailbox provider"},
        "payroll-kitewing.example": {"registered": "2026-10-13", "note": "payroll-lure phishing domain"},
        "freepdfconvert-pro.example": {"registered": "2026-10-11", "note": "infostealer download site"},
        "tessarodesign.example": {"registered": "2014-06-18", "note": "real vendor domain"},
    },
}

# --------------------------------------------------------------------------------------------- SaaS & OAuth
SAAS = {
    "as_of": "2026-11-06",
    "app_policy": "Since 2026-11-03: unverified third-party apps blocked for new grants; 14-app allowlist. Legacy grants remain until revoked.",
    "scope_risk": {
        "https://mail.google.com/": "critical", "gmail.readonly": "high", "gmail.modify": "high", "gmail.send": "high",
        "gmail.settings.sharing": "high", "gmail.settings.basic": "high", "drive": "high", "drive.readonly": "high",
        "drive.file": "low", "calendar": "medium", "calendar.readonly": "low", "spreadsheets": "medium",
        "admin.reports.audit.readonly": "medium", "admin.directory.user.readonly": "medium", "openid": "none", "email": "none",
        "profile": "none", "chat.messages": "medium",
    },
    "oauth_apps": [
        {"app": "PDF Secure Viewer", "client_id": "990417-pdfsecureviewer", "publisher": "pdfsecure-viewer.example", "verified": False,
         "scopes": ["gmail.readonly", "gmail.settings.sharing", "drive"], "users": 1, "user_tokens": ["<<u:maya.singh>>"],
         "first_grant": "2026-11-01", "grant_origin": "link in an email", "publisher_domain_age_days": 2, "allowlisted": False,
         "status": "revoked 2026-11-01 02:07:59 (PB-02) and client id blocked", "incident": "INC-1101-01"},
        {"app": "QuickSign Free", "client_id": "771203-quicksignfree", "publisher": "quicksign-free.example", "verified": False,
         "scopes": ["gmail.readonly", "drive"], "users": 1, "user_tokens": ["<<u:ruth.adebayo>>"], "first_grant": "2026-10-19",
         "grant_origin": "marketplace search", "publisher_domain_age_days": 410, "allowlisted": False, "status": "active (legacy grant)"},
        {"app": "Docs PDF Converter Plus", "client_id": "552981-docspdfplus", "publisher": "docspdf-plus.example", "verified": False,
         "scopes": ["drive"], "users": 4, "user_tokens": ["<<u:tomas.rivera>>", "<<u:paul.ngata>>", "<<u:ava.lindholm>>"],
         "first_grant": "2026-08-30", "grant_origin": "browser extension prompt", "publisher_domain_age_days": 220, "allowlisted": False,
         "status": "active (legacy grant)"},
        {"app": "AI Meeting Notes Free", "client_id": "640118-aimeetingnotes", "publisher": "meetnotes-ai.example", "verified": False,
         "scopes": ["calendar", "drive.file", "gmail.send"], "users": 3,
         "user_tokens": ["<<u:jamie.cho>>", "<<u:marco.venturi>>", "<<u:ethan.caldwell>>"], "first_grant": "2026-09-22",
         "grant_origin": "calendar invite add-on", "publisher_domain_age_days": 95, "allowlisted": False,
         "status": "active (legacy grant); new consents blocked since 2026-11-03"},
        {"app": "Calendar Sync Pro", "client_id": "339870-calsyncpro", "publisher": "calsync.example", "verified": False,
         "scopes": ["calendar"], "users": 2, "user_tokens": ["<<u:lena.okafor>>", "<<u:sienna.park>>"], "first_grant": "2026-05-11",
         "grant_origin": "marketplace search", "publisher_domain_age_days": 1300, "allowlisted": False, "status": "active (legacy grant)"},
        {"app": "MailMerge Toolkit", "client_id": "118044-mailmergetk", "publisher": "MailMerge Toolkit Ltd", "verified": True,
         "scopes": ["gmail.send", "spreadsheets"], "users": 6, "user_tokens": ["<<u:sienna.park>>", "<<u:ben.hartley>>", "<<u:owen.gallagher>>"],
         "first_grant": "2025-03-02", "grant_origin": "marketplace", "publisher_domain_age_days": 2900, "allowlisted": True, "status": "active (allowlisted)"},
        {"app": "Diagram Helper", "client_id": "204417-diagramhelper", "publisher": "Diagram Helper Inc.", "verified": True,
         "scopes": ["drive.file"], "users": 9, "user_tokens": ["<<u:nadia.rahman>>", "<<u:arjun.mehta>>", "<<u:kenji.arai>>"],
         "first_grant": "2024-11-18", "grant_origin": "marketplace", "publisher_domain_age_days": 3100, "allowlisted": True, "status": "active (allowlisted)"},
        {"app": "Slack", "client_id": "slack-workspace", "publisher": "Slack", "verified": True, "scopes": ["calendar.readonly", "drive.readonly", "profile"],
         "users": 58, "user_tokens": [], "first_grant": "2021-02-10", "grant_origin": "admin-installed", "publisher_domain_age_days": 5000,
         "allowlisted": True, "status": "sanctioned"},
        {"app": "Zoom", "client_id": "zoom-workspace", "publisher": "Zoom", "verified": True, "scopes": ["calendar", "profile"], "users": 55,
         "user_tokens": [], "first_grant": "2021-02-10", "grant_origin": "admin-installed", "publisher_domain_age_days": 5000,
         "allowlisted": True, "status": "sanctioned"},
        {"app": "DocuSign", "client_id": "docusign-workspace", "publisher": "DocuSign", "verified": True, "scopes": ["drive.file", "gmail.send"],
         "users": 8, "user_tokens": [], "first_grant": "2022-01-15", "grant_origin": "admin-installed", "publisher_domain_age_days": 5000,
         "allowlisted": True, "status": "sanctioned"},
        {"app": "KnowBe4 Phish Alert Button", "client_id": "knowbe4-pab", "publisher": "KnowBe4", "verified": True, "scopes": ["gmail.modify"],
         "users": 62, "user_tokens": [], "first_grant": "2025-06-01", "grant_origin": "admin-installed", "publisher_domain_age_days": 5000,
         "allowlisted": True, "status": "sanctioned (security tool)"},
        {"app": "Kitewing FieldOps SSO", "client_id": "kitewing-fieldops", "publisher": "Kitewing Software (internal)", "verified": True,
         "scopes": ["openid", "email", "profile"], "users": 62, "user_tokens": [], "first_grant": "2021-03-01", "grant_origin": "internal",
         "publisher_domain_age_days": 5000, "allowlisted": True, "status": "internal"},
        {"app": "WAISentry telemetry connector", "client_id": "waisentry-connector", "publisher": "Wursta (in-tenant pipeline)", "verified": True,
         "scopes": ["admin.reports.audit.readonly", "admin.directory.user.readonly"], "users": 1, "user_tokens": [],
         "first_grant": "2026-10-05", "grant_origin": "admin-installed (onboarding day 1)", "publisher_domain_age_days": 5000,
         "allowlisted": True, "status": "sanctioned — read-only audit and directory APIs; runs inside the client's Google Cloud tenant"},
    ],
    "shadow_it": [
        {"service": "freepdfconvert-pro.example", "category": "PDF conversion", "users": 11, "uploads": 186, "uploaded_mb": 1430,
         "first_seen": "2026-10-11", "risk": "critical", "why": "infostealer source in INC-1028-01; blocked since 2026-10-28",
         "alternative": "Google Drive / Docs built-in PDF export"},
        {"service": "chat-ai-free.example", "category": "consumer AI chatbot", "users": 14, "uploads": 212, "uploaded_mb": 9,
         "first_seen": "2026-09-02", "risk": "high", "why": "37 pastes over 2,000 characters — likely customer or code content",
         "alternative": "Gemini in Google Workspace (enterprise data protections)"},
        {"service": "filedrop.example", "category": "large file transfer", "users": 7, "uploads": 41, "uploaded_mb": 2310,
         "first_seen": "2026-08-14", "risk": "high", "why": "2.3 GB uploaded outside Drive; no expiry or audit",
         "alternative": "Drive sharing with expiry and visitor sharing"},
        {"service": "personalmail.example", "category": "personal webmail", "users": 22, "uploads": 61, "uploaded_mb": 140,
         "first_seen": "2026-10-08", "risk": "medium", "why": "attachments uploaded to personal mailboxes", "alternative": "—"},
        {"service": "screenrec.example", "category": "screen recording", "users": 6, "uploads": 33, "uploaded_mb": 980,
         "first_seen": "2026-09-19", "risk": "medium", "why": "support screen recordings may show customer data",
         "alternative": "Google Vids / Meet recordings in Drive"},
        {"service": "notesync.example", "category": "note taking", "users": 5, "uploads": 120, "uploaded_mb": 12,
         "first_seen": "2026-07-30", "risk": "low", "why": "personal notes app synced from work laptops", "alternative": "Google Keep / Docs"},
    ],
    "alerts": {
        "7": {"period": "2026-10-31 to 2026-11-06",
              "knowbe4": {"phish_prone_pct": 9.7, "phish_prone_pct_baseline_2026_10_01": 21.0,
                          "last_simulation": "'Payroll update' 2026-11-03: 6 of 62 clicked, 0 entered credentials",
                          "training_completion": "58 of 62 (4 overdue)", "running_simulation": "'Holiday bonus' launched 2026-11-06 09:00 — 1 click so far", "phish_alert_reports": 11,
                          "reports_confirmed_malicious": 4, "reports_spam": 5, "reports_simulation": 2},
              "mimecast": {"inbound": 18940, "rejected": 1212, "impersonation_hits": 23, "url_protect_blocks": 9,
                           "attachments_held": 2, "dmarc_failures": 31,
                           "notable": "2026-11-01 02:07 lookalike tessaro-designs.example delivered with a banner (INC-1101-01) — recommend hold instead of banner for finance recipients"},
              "dnsfilter": {"queries": 1184220, "blocked": 3410, "blocked_by_category": {"ads/trackers": 2960, "newly registered": 61,
                            "phishing": 14, "malware": 3, "unsanctioned file sharing": 372},
                            "notable": "securedoc-viewer.example resolved (allowed) on 2026-11-01 02:03 — newly registered domains are not blocked for the finance group"},
              "web_proxy": {"uploads_to_unsanctioned_saas_mb": 2930, "executables_blocked": 4, "notable": "chat-ai-free.example: 9 large pastes this week"}},
        "30": {"period": "2026-10-08 to 2026-11-06",
               "knowbe4": {"phish_prone_pct": 9.7, "phish_prone_pct_baseline_2026_10_01": 21.0, "simulations": "3 (2026-10-13, 2026-11-03, 2026-11-06 running)",
                           "phish_alert_reports": 47, "reports_confirmed_malicious": 15},
               "mimecast": {"inbound": 79410, "rejected": 5233, "impersonation_hits": 88, "url_protect_blocks": 41,
                            "attachments_held": 9, "messages_purged": 14},
               "dnsfilter": {"queries": 5036810, "blocked": 14820, "blocked_by_category": {"ads/trackers": 12680,
                             "newly registered": 248, "phishing": 61, "malware": 9, "unsanctioned file sharing": 1822}},
               "web_proxy": {"uploads_to_unsanctioned_saas_mb": 4881, "executables_blocked": 17}},
    },
}

# --------------------------------------------------------------------------------------------- fleet & hybrid
frng = random.Random(77)
devices = []
for loc, name, title, team, office, os_ in D:
    d = {"device": f"<<d:{HOSTS[loc]}>>", "owner": f"<<u:{loc}>>", "os": {"macOS": "macOS", "Windows": "Windows 11", "ChromeOS": "ChromeOS"}[os_],
         "office": office, "update_status": "up to date", "patch_age_days": frng.randint(0, 12), "encryption": True,
         "edr": "healthy" if os_ != "ChromeOS" else "n/a (ChromeOS verified boot + DNSFilter)", "firewall": True,
         "screen_lock": True, "last_seen": f"2026-11-0{frng.choice([5, 6, 6, 6])}", "network_7d": "home / office",
         "issues": []}
    devices.append(d)
byname = {d["owner"]: d for d in devices}


def dev(loc):
    return byname[f"<<u:{loc}>>"]


dev("jonah.petit").update(issues=["infostealer 2026-10-28 (INC-1028-01) — reimaged 2026-10-29, healthy since"], patch_age_days=8)
dev("ben.hartley").update(update_status="2 updates behind", patch_age_days=64,
                          issues=["macOS 2 updates behind (64 days)", "adware browser extension removed 2026-10-19 (ED-2198)"])
dev("riley.ford").update(edr="missing (BYOD — agent not installed)", encryption=False, update_status="unknown", patch_age_days=None,
                         issues=["BYOD without EDR", "disk encryption not verified", "contractor access to Drive and GitHub"])
dev("kai.lindqvist").update(update_status="1 update behind", patch_age_days=33, issues=["macOS 1 update behind (33 days)"])
dev("sam.okoro").update(update_status="auto-update paused", patch_age_days=41, issues=["ChromeOS auto-update paused by user policy exception"])
dev("theo.marsh").update(screen_lock=False, issues=["screen lock disabled"])
dev("jamie.cho").update(network_7d="home / office")
dev("kwame.mensah").update(network_7d="open airport Wi-Fi 2026-11-02 + home", issues=["joined an open Wi-Fi network (always-on DNSFilter + Workspace TLS mitigated)"])
dev("priya.natarajan").update(network_7d="café Wi-Fi (open) 2026-11-04, hotel 2026-11-05/06", issues=["joined an open café Wi-Fi network"])
dev("maya.singh").update(issues=["full EDR scan 2026-11-01 02:20 clean (INC-1101-01 was OAuth-only)"])
for d in devices:
    d["compliant"] = not any(x for x in d["issues"] if not x.startswith(("full EDR scan", "infostealer 2026-10-28", "joined")))
office_pcs = [
    {"device": "MB-WS07", "owner": "Millbrook reception (shared)", "os": "Windows 10 22H2 (out of support since 2025-10-14)",
     "office": "Millbrook office", "update_status": "end of life", "patch_age_days": 390, "encryption": False, "edr": "missing",
     "firewall": True, "screen_lock": False, "last_seen": "2026-10-30", "network_7d": "office LAN — removed 2026-10-31",
     "issues": ["Windows 10 out of support", "no EDR", "source of the 2026-10-30 password spray (INC-1030-01) — removed from network"],
     "compliant": False},
    {"device": "MB-WS02", "owner": "Millbrook print & scan station (shared)", "os": "Windows 11", "office": "Millbrook office",
     "update_status": "up to date", "patch_age_days": 9, "encryption": True, "edr": "healthy", "firewall": True,
     "screen_lock": True, "last_seen": "2026-11-06", "network_7d": "office LAN", "issues": [], "compliant": True},
]
FLEET = {
    "as_of": "2026-11-06T09:30:00-06:00",
    "devices": devices + office_pcs,
    "edr_alerts": [
        {"id": "ED-2210", "ts": ts(W, "14:21:48"), "device": "<<d:jpetit-win>>", "severity": "critical", "technique": "T1555.003",
         "what": "Unsigned pdfconvert_setup.exe read Chrome login-data and cookie stores (infostealer)", "status": "isolated 14:38, reimaged 2026-10-29", "incident": "INC-1028-01"},
        {"id": "ED-2211", "ts": ts(W, "14:22:30"), "device": "<<d:jpetit-win>>", "severity": "high", "technique": "T1041",
         "what": "4.1 MB HTTPS upload to 198.51.100.23 by the same process", "status": "closed with ED-2210", "incident": "INC-1028-01"},
        {"id": "ED-2198", "ts": "2026-10-19T11:05:00-06:00", "device": "<<d:bhartley-mbp>>", "severity": "low", "technique": None,
         "what": "Adware browser extension 'SearchBoost' installed", "status": "auto-removed"},
        {"id": "ED-2204", "ts": "2026-10-23T03:12:05-06:00", "device": "MB-FS01", "severity": "medium", "technique": "T1219",
         "what": "Unsigned LegacyRemote 6 updater launched", "status": "tool uninstalled 10:40", "incident": "INC-1023-01"},
        {"id": "ED-2216", "ts": "2026-11-02T09:14:00-06:00", "device": "<<d:hlaurent-win>>", "severity": "low", "technique": None,
         "what": "Encoded PowerShell command", "status": "false positive — IT inventory script (Hugo Laurent)"},
    ],
    "onprem": {
        "site": "Millbrook office",
        "assets": [
            {"asset": "MB-DC01", "role": "Active Directory domain controller (badge system, printers, file-share sign-in; 41 AD accounts — not synced to Workspace)",
             "os": "Windows Server 2019", "edr": "healthy", "log_path": "Windows Event Forwarding -> MB-SYSLOG01", "status": "healthy"},
            {"asset": "MB-FS01", "role": "Legacy file server (\\\\MB-FS01\\Projects-Archive, 1.2 TB)", "os": "Windows Server 2016 (extended support ends 2027-01-12)",
             "edr": "healthy", "log_path": "Windows Event Forwarding -> MB-SYSLOG01", "status": "attention — SMBv1 still enabled; OS end of support in 67 days"},
            {"asset": "MB-SYSLOG01", "role": "Syslog forwarder (rsyslog over TLS to the in-tenant WAISentry pipeline)", "os": "Ubuntu 22.04 LTS",
             "edr": "healthy", "log_path": "-", "status": "healthy — last message 2026-11-06 09:29:58, lag 4 s; one gap 2026-10-26 01:00-01:42 (patch reboot)"},
            {"asset": "MB-FW01", "role": "Office firewall with IDS/IPS", "os": "appliance firmware (2 minor versions behind)",
             "edr": "n/a", "log_path": "syslog -> MB-SYSLOG01", "status": "attention — firmware update pending"},
        ],
        "events": [
            {"ts": "2026-10-08/2026-11-06", "asset": "MB-FW01", "type": "inbound scans blocked", "count": 57210, "severity": "info",
             "note": "Internet background scanning (~1,900/day), all blocked — counted as noise"},
            {"ts": "2026-10-23T03:12:04-06:00", "asset": "MB-FW01 / MB-FS01", "type": "IDS: LegacyRemote outdated agent update", "count": 1,
             "severity": "medium", "note": "Outbound blocked", "incident": "INC-1023-01"},
            {"ts": "2026-10-26T01:00:00-06:00", "asset": "MB-SYSLOG01", "type": "log gap 42 min", "count": 1, "severity": "low",
             "note": "Planned patch reboot; no events lost on the DC (forwarded from the local buffer)"},
            {"ts": "2026-10-30T22:47:12-06:00", "asset": "MB-DC01", "type": "failed Kerberos pre-auth (4771) + logon failures (4625)", "count": 312,
             "severity": "high", "note": "41 accounts, 6 lockouts, 0 successes, source MB-WS07", "incident": "INC-1030-01"},
            {"ts": "2026-11-02T10:05:00-06:00", "asset": "MB-DC01", "type": "Domain Admins membership change", "count": 2, "severity": "info",
             "note": "Hugo Laurent added 10:05, removed 11:20 — matches change ticket IT-1094 (verified benign)"},
            {"ts": "2026-11-03T15:10:00-06:00", "asset": "MB-FS01", "type": "mass file rename", "count": 2140, "severity": "info",
             "note": "Projects-Archive restructuring by <<u:tomas.rivera>> — same extensions, no encryption entropy (ransomware pattern ruled out)"},
        ],
    },
}

# --------------------------------------------------------------------------------------------- tenant
TENANT = {
    "_note": "In-tenant reference data for the fictional client Kitewing Software. It never leaves the client's Google Cloud tenant; the SOC only sees tokens.",
    "client": "Kitewing Software, Inc. (fictional)", "domain": DOMAIN, "people": 62, "employees": 60, "contractors": 2,
    "waisentry": {"posture_review": "2026-10-01", "onboarding": "2026-10-05 to 2026-10-07", "go_live": "2026-10-07 18:00",
                  "telemetry_from": "2026-10-08", "pre_approval_signed": "2026-10-05 by Marcus Bell (COO & CFO)"},
    "timezone": "Kitewing local time, UTC-6 (all timestamps)",
    "offices": {"Cedar Harbor HQ": "headquarters, 3rd floor", "Millbrook office": "support team + legacy on-prem footprint",
                "Remote": "about a third of staff"},
    "sources": ["Google Workspace audit logs (login, token, Drive, Gmail settings, admin) via native APIs",
                "Laptop EDR (macOS, Windows) + ChromeOS device signals", "Millbrook firewall/IDS (MB-FW01)",
                "Domain controller and file server events via syslog forwarder MB-SYSLOG01",
                "KnowBe4 (awareness + Phish Alert Button)", "Mimecast (email gateway)", "DNSFilter (DNS security)",
                "Cloud web proxy (secure web gateway)"],
    "contacts": [
        {"role": "Client security contact / on-call", "name": "Noah Kim", "title": "IT & Security Administrator"},
        {"role": "Millbrook IT", "name": "Hugo Laurent", "title": "IT Support Technician"},
        {"role": "Executive sponsor; finance escalation (payments)", "name": "Marcus Bell", "title": "COO & CFO"},
        {"role": "Executive briefing recipient", "name": "Dana Whitfield", "title": "CEO"},
    ],
    "token_policy": {"algorithm": "HMAC-SHA256 with a per-tenant key, truncated to 4 hex characters per type",
                     "types": {"USR": "people and mailboxes", "EXT": "external addresses", "FIL": "file names",
                               "MSG": "message subjects and bodies", "DEV": "personal device names", "PHN": "phone numbers",
                               "ACC": "bank or card account numbers"},
                     "kept_in_clear": ["IP addresses and ASNs", "domains and URLs", "app names and OAuth client ids",
                                       "server names (MB-*)", "timestamps", "ATT&CK techniques", "scores and counts"],
                     "key_note": "Demo constant. In the service the tokenisation key stays in the client's tenant, so only the client can re-identify."},
    "directory": directory,
    "external_contacts": EXTERNAL_CONTACTS,
    "files": FILES,
    "messages": MESSAGES,
}

# ------------------------------------------------------------------------------------------ write + checks
OUT = {
    "sentry_tenant": TENANT,
    "sentry_telemetry": {"_note": "Tokenised (zero-PII) telemetry batches as WAISentry triage receives them. Synthetic.",
                         "scoring": SCORING, "batches": BATCHES},
    "sentry_incidents": {"_note": "WAISentry incident case files for the fictional client Kitewing Software (tokenised). Synthetic.",
                         "incidents": INCIDENTS},
    "sentry_identity": IDENTITY,
    "sentry_saas": SAAS,
    "sentry_fleet": FLEET,
}

# extra vocab for the support-escalations group used in MR-06
directory.append({"email": f"support-escalations@{DOMAIN}", "name": "Support escalations (Google Group)", "title": "group",
                  "team": "Customer Success", "office": "—", "type": "group", "two_step": "n/a", "super_admin": False,
                  "device": None, "device_os": None})

vocab = {}
for d in directory:
    vocab.setdefault(token("user", d["email"]), set()).add(d["email"])
    if d["device"]:
        vocab.setdefault(token("device", d["device"]), set()).add(d["device"])
for c in EXTERNAL_CONTACTS:
    vocab.setdefault(token("external", c["email"]), set()).add(c["email"])
for f in FILES:
    vocab.setdefault(token("file", f["name"]), set()).add(f["name"])
for m in MESSAGES:
    vocab.setdefault(token("message", m), set()).add(m)
coll = {k: v for k, v in vocab.items() if len(v) > 1}
assert not coll, f"token collisions: {coll}"

for name, data in OUT.items():
    data = walk(data)
    txt = json.dumps(data, indent=1, ensure_ascii=False)
    left = PH.findall(txt)
    assert not left, left
    (FIX / f"{name}.json").write_text(txt + "\n")
    print(name, len(txt))

for b, v in BATCHES.items():
    alerts = [e for e in v["events"] if e["score"] >= 60]
    print(b, len(v["events"]), "events", len(alerts), "alerts", [(e["id"], e["score"]) for e in alerts])
for inc in INCIDENTS:
    print(inc["id"], inc.get("contained_at"), inc.get("planned_containment"))
print("maya", token("user", "maya.singh@kitewing.example"), "ben", token("user", "ben.hartley@kitewing.example"),
      "jonah", token("user", "jonah.petit@kitewing.example"), "riley", token("user", "riley.ford@kitewing.example"))

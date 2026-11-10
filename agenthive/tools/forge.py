"""Agent Forge tools — Platform Core realm, cluster `forge` (every tool is prefixed forge_).

Agent Forge is an agent factory for client-ready agents: Describe -> Plan -> Build -> Test -> Deploy to sandbox ->
Deploy to client, with plain-English change requests looping back as new versions and every run kept as a job.
Everything here is deterministic over synthetic fixtures frozen at the demo date 2026-11-06 (forge_*.json):
connector registry, forge agent catalog and version history, test-pane results, job log, standards and access.

Two tools do real work instead of reading fixtures:
  forge_static_check    AST-based static analysis of generated ADK agent code and its pytest tests (never executes it)
  forge_redact_secrets  regex detectors for common key formats; returns redacted text and findings
Side effects (registering connectors, test runs, deploys, jobs) are simulated and say so. The release gate is
enforced with deterministic tokens: a passing static check issues an SC- id that a new version needs before its
tests run, and only an all-pass test run issues the TR- id that a deploy needs.
"""
from __future__ import annotations

import ast
import copy
import datetime as dt
import hashlib
import json
import re
import statistics

from ._base import doc_text, err, fixture, hive_tool, ok

TODAY = dt.date(2026, 11, 6)
NOW = dt.datetime(2026, 11, 6, 12, 0)
_SALT = "agent-forge-demo"
JOB_TYPES = ("create", "modify", "fork", "deploy", "connector", "connector_modify")
JOB_STATUSES = ("queued", "running", "waiting_for_input", "succeeded", "failed", "cancelled")

# --- shared helpers ------------------------------------------------------------------------------------------------


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").lower()).strip("_")


def _vnum(v: str) -> int:
    m = re.search(r"(\d+)", str(v or ""))
    return int(m.group(1)) if m else 0


def _ver(v: str) -> str:
    return f"v{_vnum(v)}" if _vnum(v) else ""


def _token(prefix: str, *parts: object) -> str:
    return prefix + "-" + hashlib.sha1("|".join([_SALT, prefix, *map(str, parts)]).encode()).hexdigest()[:8].upper()


def _fake_values() -> dict[str, str]:
    """Obviously fake, correctly shaped keys for the redaction demo. Built by concatenation so that no key-shaped
    string is ever committed to this public repository (docs store <<FAKE:kind>> placeholders instead)."""
    z = "0" * 48
    return {
        "google_api_key": "AI" + "za" + ("SyFAKE-DEMO-KEY-NOT-REAL-" + z)[:35],
        "openai_key": "sk" + "-proj-" + "FAKEdemoKEYnotREAL" + "0" * 24,
        "slack_token": "xo" + "xb-" + "000000000000-000000000000-" + "FAKEdemoTOKENnotREAL0000",
        "github_token": "gh" + "p_" + "FAKEdemoTOKENnotREAL" + "0" * 16,
        "bearer_token": "fake" + "-demo-bearer-" + "0" * 24,
        "aws_access_key": "AK" + "IA" + "IOSFODNN7" + "EXAMPLE",
        "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/" + "bPxRfiCY" + "EXAMPLEKEY",
        "shopify_token": "sh" + "pat_" + "deadbeef" * 4,
        "google_oauth_secret": "GOC" + "SPX-" + ("FAKE-demo-secret-" + z)[:28],
        "private_key": "-----BEGIN " + "PRIVATE KEY-----\n" + "FAKEdemoKEYmaterialNOTREAL" + "0" * 38 + "\n-----END "
                       + "PRIVATE KEY-----",
    }


def _materialise(text: str) -> str:
    fakes = _fake_values()
    return re.sub(r"<<FAKE:([a-z_]+)>>", lambda m: fakes.get(m.group(1), m.group(0)), text or "")


def _text(text_or_key: str) -> tuple[str, str]:
    """Accept raw text or the key of a sample document; returns (text, source)."""
    key = (text_or_key or "").strip()
    if re.fullmatch(r"[a-z0-9_]{4,80}", key) and (d := doc_text(key)):
        return _materialise(d), key
    return _materialise(text_or_key or ""), "inline text"


def _clients() -> dict:
    return fixture("forge_agents")["clients"]


def _client_id(client: str) -> str | None:
    cs = _clients()
    c = _slug(client)
    if not c:
        return None
    if c in cs:
        return c
    for cid, rec in cs.items():
        if c == _slug(rec["name"]) or c in _slug(rec["name"]) or _slug(rec["name"]).startswith(c):
            return cid
    return None


def _agents() -> list[dict]:
    return fixture("forge_agents")["agents"]


def _agent(agent: str) -> dict | None:
    a = _slug(agent)
    for r in _agents():
        if a in (r["id"], _slug(r["name"])):
            return r
    for r in _agents():
        if a and (a in r["id"] or a in _slug(r["name"])):
            return r
    return None


def _connectors() -> list[dict]:
    return fixture("forge_connectors")["connectors"]


def _connector(cid: str) -> dict | None:
    c = _slug(str(cid).split("@")[0].split(" (")[0])
    for r in _connectors():
        if c in (r["id"], _slug(r["name"])):
            return r
    for r in _connectors():
        if c and (c in r["id"] or c in _slug(r["name"]) or r["id"] in c):
            return r
    return None


_WORKSPACE_SECRET = re.compile(r"^(GMAIL|GOOGLE_(SHEETS|DRIVE|DOCS|SLIDES|CALENDAR|WORKSPACE|OAUTH)|WORKSPACE)_|"
                               r"^(GMAIL|GOOGLE)_?OAUTH")


def _real_secrets(conn: dict) -> list[str]:
    return [s for s in conn.get("secrets", []) if "<" not in s]


def _versions(agent_id: str) -> list[dict]:
    return fixture("forge_versions")["agents"].get(agent_id, [])


def _snapshots(agent_id: str) -> list[tuple[dict, dict]]:
    """Rebuild every version's spec snapshot from v1 + deltas."""
    out, snap = [], {}
    for v in _versions(agent_id):
        if "spec" in v:
            snap = copy.deepcopy(v["spec"])
        else:
            snap = copy.deepcopy(snap)
            d = v.get("delta", {})
            for f in ("tools", "connectors", "rules", "tests"):
                cur = [x for x in snap.get(f, []) if x not in d.get(f + "-", [])]
                snap[f] = cur + [x for x in d.get(f + "+", []) if x not in cur]
            snap["settings"] = {**snap.get("settings", {}), **d.get("settings", {})}
        out.append((v, snap))
    return out


def _scoped(role: str) -> bool:
    """True for roles limited to their assigned clients (e.g. demo users), from the access fixture."""
    return fixture("forge_access")["roles"].get(role, {}).get("client_scope", "all") != "all"


def _user(email: str) -> dict | None:
    e = str(email or "").strip().lower()
    users = fixture("forge_access")["users"]
    return next((u for u in users if u["email"] == e), None) or next(
        (u for u in users if e and (e in u["email"] or e == u["name"].lower())), None)


# --- secret detection (real) ---------------------------------------------------------------------------------------

_DETECTORS: list[tuple[str, re.Pattern, int]] = [(n, re.compile(p), g) for n, p, g in [
    ("private_key_block", r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END (?:[A-Z]+ )*PRIVATE KEY"
                          r"(?: BLOCK)?-----", 0),
    ("google_api_key", r"\bAIza[0-9A-Za-z_\-]{35}", 0),
    ("google_oauth_client_secret", r"\bGOCSPX-[0-9A-Za-z_\-]{28}", 0),
    ("openai_style_key", r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{20,}", 0),
    ("stripe_style_key", r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}", 0),
    ("github_token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})", 0),
    ("slack_token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}", 0),
    ("slack_webhook", r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}", 0),
    ("aws_access_key_id", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", 0),
    ("aws_secret_access_key", r"(?i)aws_secret_access_key[\"']?\s*[=:]\s*[\"']?([A-Za-z0-9/+=]{40})", 1),
    ("shopify_token", r"\bshp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}\b", 0),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", 0),
    ("bearer_token", r"(?i)\bbearer\s+([A-Za-z0-9\-._~+/]{16,}=*)", 1),
    ("password_in_url", r"\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:([^\s@/]+)@", 1),
    ("generic_secret_assignment", r"(?i)\b[\w.-]*(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|token)\b"
                                  r"[\"']?\s*[:=]\s*[\"']?([^\s\"',;{}()\[\]]{8,}+)(?![(\[])", 1),
]]
_REFERENCE = re.compile(r"^(?:[A-Z][A-Z0-9_]{2,}|<.*|\$.*|\{\{.*|secret-manager://.*|sm://.*|projects/.*|env:.*|"
                        r"os\.environ.*|os\.getenv.*|\[REDACTED.*)$")
_ROTATE = {
    "google_api_key": "Rotate the Google API key and restrict it by API and referrer.",
    "google_oauth_client_secret": "Reset the OAuth client secret.",
    "openai_style_key": "Revoke the third-party model API key.",
    "github_token": "Revoke the GitHub token.",
    "slack_token": "Revoke and reissue the Slack token.",
    "aws_access_key_id": "Deactivate the AWS access key pair.",
    "aws_secret_access_key": "Deactivate the AWS access key pair.",
    "shopify_token": "Rotate the Shopify Admin API token.",
    "private_key_block": "Delete and replace the private key (service-account keys should not exist at all).",
    "password_in_url": "Change the database password and use a Secret Manager reference.",
}


_PREFIXED = {"google_api_key", "google_oauth_client_secret", "openai_style_key", "stripe_style_key", "github_token",
             "slack_token", "slack_webhook", "aws_access_key_id", "shopify_token", "jwt", "private_key_block"}


def _scan(text: str) -> list[dict]:
    """Find secret spans: [{type, start, end}] without overlaps (specific detectors win over the generic one)."""
    spans: list[dict] = []
    for name, rx, grp in _DETECTORS:
        for m in rx.finditer(text):
            s, e = m.span(grp)
            val = m.group(grp)
            if name == "generic_secret_assignment" and (
                    _REFERENCE.match(val) or val.lower() in ("redacted", "none", "null", "true", "false")):
                continue
            if any(not (e <= x["start"] or s >= x["end"]) for x in spans):
                continue
            spans.append({"type": name, "start": s, "end": e})
    return sorted(spans, key=lambda x: x["start"])


def _redact(text: str) -> tuple[str, list[dict]]:
    spans = _scan(text)
    out, last, findings = [], 0, []
    for sp in spans:
        val = text[sp["start"]:sp["end"]]
        out += [text[last:sp["start"]], f"[REDACTED:{sp['type']}]"]
        last = sp["end"]
        shown = val[:4] if sp["type"] in _PREFIXED else "****"
        findings.append({"type": sp["type"], "line": text.count("\n", 0, sp["start"]) + 1,
                         "preview": f"{shown}… ({len(val)} chars)"})
    out.append(text[last:])
    return "".join(out), findings


# --- catalog & connectors ------------------------------------------------------------------------------------------

_STOP = set("the and for with that this from into our their every each agent agents need needs want wants build "
            "make create new client clients connector connectors data what which when who how can will would should "
            "about all any get gets use using via per there them they have has are was were not".split())


def _terms(q: str) -> list[str]:
    return [t.rstrip("s") if len(t) > 4 else t for t in re.findall(r"[a-z0-9]+", (q or "").lower())
            if len(t) > 2 and t not in _STOP]


@hive_tool("platform")
def forge_search_catalog(query: str, client: str = "") -> dict:
    """Search the forge for reusable connectors and existing agents that match a plain-English need.

    Args:
        query: What the agent must do or which system it touches, e.g. 'bay times from Tekmetric' or 'Shopify returns'.
        client: Optional client name or id (e.g. 'Ridgeline Outfitters') to show its time zone and existing agents.

    Returns:
        Matching connectors (status, auth, secrets by name) and agents (client, version, connectors) ranked by match,
        plus reuse hints: an agent for another client is a fork candidate; a draft connector is not usable yet.
    """
    terms = _terms(query)
    if not terms:
        return err("query needs at least one meaningful word")

    def score(hay: str) -> int:
        hay = hay.lower()
        return sum(1 for t in terms if t in hay)

    conns = sorted(((score(" ".join([c["id"], c["name"], " ".join(c["tags"]), " ".join(c["methods"])])), c)
                    for c in _connectors()), key=lambda x: -x[0])
    agents = sorted(((score(" ".join([a["id"], a["name"], a["summary"], a["group"], " ".join(a["connectors"])])), a)
                     for a in _agents()), key=lambda x: -x[0])
    cid = _client_id(client)
    names = {k: v["name"] for k, v in _clients().items()}
    out_c = [{"id": c["id"], "name": c["name"], "kind": c["kind"], "status": c["status"], "version": c["version"],
              "auth": c["auth"], "acts_as": c["acts_as"], "secrets": _real_secrets(c), "match": s,
              **({"draft_reason": c["draft_reason"]} if c.get("draft_reason") else {})}
             for s, c in conns if s][:6]
    out_a = [{"id": a["id"], "name": a["name"], "client": names[a["client"]], "status": a["status"],
              "version": a["latest_version"], "shape": a["topology"]["shape"], "connectors": a["connectors"],
              "match": s, "reuse": "same client - modify" if cid and a["client"] == cid else "fork candidate"}
             for s, a in agents if s][:5]
    res = {"query_terms": terms, "connectors": out_c, "agents": out_a}
    if cid:
        c = _clients()[cid]
        res["client"] = {"id": cid, "name": c["name"], "kind": c["kind"], "time_zone": c["time_zone"],
                         "agents": [a["id"] for a in _agents() if a["client"] == cid]}
    elif client:
        res["client"] = {"name": client, "known": False, "note": "new client - an admin creates the client record"}
    return ok(**res)


@hive_tool("platform")
def forge_connector_detail(connector_id: str) -> dict:
    """Return one connector's full record: auth, base URL, methods, pagination, rate limits, secrets and usage.

    Args:
        connector_id: Connector id or name, e.g. 'tekmetric', 'shopify_admin', 'Google Sheets'.

    Returns:
        found, and the connector (official or custom, ready or draft, version, auth, methods the generated code may
        call, secret names), plus which agents and clients already use it.
    """
    c = _connector(connector_id)
    if not c:
        return ok(found=False, connector=connector_id,
                  note="not in the connector registry. A connector registered earlier in this same run is simulated "
                       "and not persisted - use the connector spec from your brief; otherwise build it with the "
                       "Connector Smith.", available=[x["id"] for x in _connectors()])
    used = [a for a in _agents() if c["id"] in a["connectors"]]
    names = {k: v["name"] for k, v in _clients().items()}
    return ok(found=True, **{k: v for k, v in c.items() if k not in ("tags", "status")},
              connector_status=c["status"],
              secrets_required=_real_secrets(c),
              used_by=[f"{a['id']} ({names[a['client']]})" for a in used],
              clients=sorted({names[a["client"]] for a in used}))


@hive_tool("platform")
def forge_agent_record(agent: str) -> dict:
    """Return a forge agent's record: client, status, versions, topology, connectors, current spec and test state.

    Args:
        agent: Agent id or name, e.g. 'shopify_order_support_tracker' or 'Employee Bay Time Tracker'.

    Returns:
        Client (name, time zone), status, latest / sandbox / client versions, next version number, the latest spec
        snapshot (tools, connectors, rules, settings, tests), last change request, recorded test result, standards
        gaps, the source of the function the last change touched (when the forge has it) and whether each secret
        is set in the test pane and in Secret Manager (names only, never values).
    """
    a = _agent(agent)
    if not a:
        return err(f"no forge agent matching {agent!r}", available=[x["id"] for x in _agents()])
    snaps = _snapshots(a["id"])
    last_v, snap = snaps[-1] if snaps else ({}, {})
    client = _clients()[a["client"]]
    std = fixture("forge_standards")["agents"].get(a["id"], {})
    secrets = {s: {"test_pane": client["test_pane"].get(s, "missing"),
                   "secret_manager": "present" if s in client["secret_manager"] else "missing"} for s in a["secrets"]}
    return ok(id=a["id"], name=a["name"], client=client["name"], client_id=a["client"], client_kind=client["kind"],
              time_zone=client["time_zone"], group=a["group"], summary=a["summary"], agent_status=a["status"],
              latest_version=a["latest_version"], sandbox_version=a["sandbox_version"],
              client_version=a["client_version"], next_version=f"v{_vnum(a['latest_version']) + 1}",
              topology=a["topology"], memory=a["memory"], builder=a["builder"],
              last_change={"version": last_v.get("version"), "request": last_v.get("request"),
                           "tests": last_v.get("tests"), "state": last_v.get("state", "released"),
                           "note": last_v.get("note"),
                           "code": last_v.get("code") or "not shown in this demo - write the changed function "
                                                         "from the spec and the change request"},
              spec=snap, secrets=secrets,
              standards={"version": std.get("standards_version"), "current": fixture("forge_standards")[
                  "current_version"], "gaps": sorted(std.get("fails", {}))})


# --- Forge Architect -----------------------------------------------------------------------------------------------

_SPEC_FIELDS = ("name", "client", "goal", "users", "inputs", "outputs", "topology", "connectors", "tools", "secrets",
                "memory", "test_cases", "acceptance_criteria")
_WRITE_VERB = re.compile(r"(^|_)(send|post|update|delete|write|create|append|draft|upload|acknowledge)(_|$)")


def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


@hive_tool("platform")
def forge_validate_spec(spec: dict) -> dict:
    """Validate an agent spec against forge standards before anything is built.

    Args:
        spec: The spec as an object with keys name, client, goal, users, inputs, outputs, topology ({"shape":
            "single"|"workflow", "sub_agents": [{"name", "role"}]}), connectors (ids), tools ([{"name", "connector",
            "purpose"}]), secrets (NAMES only), memory, time_zone, test_cases (list), acceptance_criteria (list) and
            optional open_questions.

    Returns:
        valid (no errors), issues (severity, field, message, standard), each connector's status in the registry
        (ready / draft / missing -> to build), required secret names, the client's time zone, similar agents that
        could be forked instead, and the suggested job type (create or fork).
    """
    if not isinstance(spec, dict) or not spec:
        return err("spec must be a non-empty object")
    issues: list[dict] = []

    def add(sev: str, field: str, msg: str, std: str = "") -> None:
        issues.append({"severity": sev, "field": field, "message": msg, **({"standard": std} if std else {})})

    for f in _SPEC_FIELDS:
        if f not in spec or spec[f] in (None, "", []) and f not in ("secrets",):
            add("error", f, "missing or empty")
    cid = _client_id(str(spec.get("client", "")))
    tz = spec.get("time_zone") or (_clients()[cid]["time_zone"] if cid else None)
    if spec.get("client") and not cid:
        add("warning", "client", "unknown client - an admin must create the client record first")

    topo = spec.get("topology") or {}
    shape = str(topo.get("shape", "") if isinstance(topo, dict) else topo).lower()
    subs = _as_list(topo.get("sub_agents")) if isinstance(topo, dict) else []
    if shape.startswith("workflow") and len(subs) < 2:
        add("error", "topology", "a workflow needs at least 2 ordered sub-agents, each with a name and role")
    elif shape.startswith("single") and subs:
        add("warning", "topology", "shape is single but sub_agents are listed - pick one")
    elif shape and not shape.startswith(("single", "workflow")):
        add("error", "topology", "shape must be 'single' or 'workflow'")

    conn_status, required, missing = [], [], []
    spec_conns = []
    for c in _as_list(spec.get("connectors")):
        cname = c.get("id") or c.get("name") if isinstance(c, dict) else str(c)
        rec = _connector(cname or "")
        if not rec:
            conn_status.append({"connector": cname, "status": "missing - to build with the Connector Smith"})
            missing.append(cname)
            continue
        spec_conns.append(rec["id"])
        conn_status.append({"connector": rec["id"], "kind": rec["kind"], "status": rec["status"], "auth": rec["auth"],
                            "version": rec["version"]})
        if rec["status"] == "draft":
            add("error", "connectors", f"{rec['id']} is a draft: {rec.get('draft_reason', 'not usable yet')}")
        required += [s for s in _real_secrets(rec) if s not in required]

    tools = _as_list(spec.get("tools"))
    tool_names = []
    for t in tools:
        name = t.get("name", "") if isinstance(t, dict) else str(t)
        name = name.split("(")[0].strip()
        tool_names.append(name)
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,60}", name):
            add("warning", "tools", f"tool name {name!r} should be snake_case")
        if isinstance(t, dict):
            tc = str(t.get("connector", "") or "")
            if tc and tc.lower() not in ("none", "pure", "-", "n/a") and _slug(tc.split(".")[0]) not in [
                    _slug(str(x)) for x in spec_conns + missing]:
                add("error", "tools", f"{name} uses connector {tc!r} that is not in the spec's connectors")
            if not t.get("purpose"):
                add("info", "tools", f"{name}: add a one-line purpose (it becomes the tool docstring)", "FS-01")

    secrets = [str(s) for s in _as_list(spec.get("secrets"))]
    for s in secrets:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", s):
            add("error", "secrets", f"{s[:12]}... is not a secret NAME (UPPER_SNAKE); never put values in a spec",
                "FS-02")
    for s in required:
        if s not in secrets:
            add("error", "secrets", f"connector needs secret {s} - list it by name", "FS-02")
    workspace = {"gmail", "google_drive", "google_sheets", "google_calendar", "google_slides", "google_docs"}
    for s in secrets:
        if _WORKSPACE_SECRET.search(s):
            add("error", "secrets", f"remove {s}: Workspace connectors act as the signed-in user via OAuth and need "
                "no secret", "FS-13")
    found = _scan(json.dumps(spec))
    if found:
        add("error", "spec", f"spec contains {len(found)} secret-like value(s): " +
            ", ".join(sorted({f['type'] for f in found})) + " - remove and rotate", "FS-02")

    mem = json.dumps(spec.get("memory", "")).lower()
    if re.search(r"full|raw|body|bodies|personal|contact details|entire", mem):
        add("warning", "memory", "keep ids, timestamps and short summaries only; 90-day retention", "FS-08")
    flat = json.dumps(spec).lower()
    writes = [n for n in tool_names if _WRITE_VERB.search(n)]
    if writes and not re.search(r"dry[_ ]?run|draft", flat):
        add("warning", "tools", f"{', '.join(writes)} write to client systems - state DRY_RUN/draft behaviour in "
            "sandbox", "FS-12")
    if re.search(r"daily|weekly|monday|tuesday|friday|schedule|date|morning|hour", flat) and not spec.get("time_zone"):
        add("warning", "time_zone", f"declare the time zone explicitly (client default: {tz or 'unknown'})", "FS-07")

    tests, acc = _as_list(spec.get("test_cases")), _as_list(spec.get("acceptance_criteria"))
    if len(tests) < max(3, len(acc)):
        add("error", "test_cases", f"{len(tests)} test cases for {len(acc)} acceptance criteria - need at least "
            f"max(3, criteria)", "FS-03")
    if tools and len(tests) < len(tools):
        add("warning", "test_cases", "fewer test cases than tools - each tool needs at least one test", "FS-03")
    if len(acc) < 2:
        add("warning", "acceptance_criteria", "give at least 2 measurable acceptance criteria", "FS-11")

    similar = []
    if spec_conns:
        for a in _agents():
            overlap = set(a["connectors"]) & set(spec_conns) - workspace
            if overlap and (not cid or a["client"] != cid):
                similar.append({"agent": a["id"], "client": _clients()[a["client"]]["name"],
                                "version": a["latest_version"], "shared_connectors": sorted(overlap)})
    order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: order[i["severity"]])
    return ok(valid=not any(i["severity"] == "error" for i in issues), issues=issues, connector_status=conn_status,
              missing_connectors=missing, required_secrets=required, client_time_zone=tz,
              similar_agents=similar[:3], suggested_job_type="fork" if similar else "create",
              open_questions=len(_as_list(spec.get("open_questions"))))


# --- Connector Smith -----------------------------------------------------------------------------------------------


@hive_tool("platform")
def forge_read_api_doc(source: str) -> dict:
    """Read API documentation the builder uploaded or pasted and extract the facts a connector needs.

    Args:
        source: A sample document key (e.g. 'forge_api_doc_fleetbeam') or the pasted documentation text. Live URLs
            cannot be fetched by this tool - research public docs with Google Search instead.

    Returns:
        Base URLs, authentication hints (headers, schemes), endpoints (method + path + description), pagination,
        rate-limit, error-code and webhook hints, each quoted from the document.
    """
    if re.match(r"https?://", (source or "").strip()):
        return err("this tool cannot fetch URLs in the demo - use Google Search grounding or paste the docs")
    text, src = _text(source)
    if len(text.strip()) < 40:
        return err("no documentation text found", hint="pass a sample doc key or paste the docs")
    lines = [ln.strip(" |-*>") for ln in text.splitlines() if ln.strip()]
    title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("#")), "API documentation")
    urls = list(dict.fromkeys(re.findall(r"https?://[^\s)`'\"|<>]+", text)))
    eps, seen = [], set()
    for ln in lines:
        for m in re.finditer(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`|]*)", ln):
            key = (m.group(1), m.group(2))
            if key in seen:
                continue
            seen.add(key)
            desc = re.sub(r"\s*\|\s*", " - ", ln[m.end():]).strip(" -|`")
            eps.append({"method": m.group(1), "path": m.group(2), "description": desc[:140],
                        "side_effect": m.group(1) != "GET"})

    def hints(rx: str, limit: int = 6) -> list[str]:
        return [ln[:200] for ln in lines if re.search(rx, ln, re.I)][:limit]

    return ok(source=src, title=title, base_urls=urls[:6],
              auth_hints=hints(r"api[ -]?key|bearer|oauth|basic auth|authori[sz]ation|header|access_key|token"),
              header_names=sorted(set(re.findall(r"\b(X-[A-Za-z0-9-]+|Authorization)\b", text))),
              endpoints=eps[:25], pagination_hints=hints(r"cursor|paginat|next_|page|offset"),
              rate_limit_hints=hints(r"rate limit|requests per|per minute|per second|429|retry-after|quota"),
              error_hints=hints(r"^\s*(4\d\d|5\d\d)\b|error", 8), webhook_hints=hints(r"webhook|signature", 3),
              chars=len(text))


_AUTH_TYPES = {"api_key_header", "api_key_query", "api_key", "bearer", "basic", "oauth2_client_credentials",
               "oauth2_authorization_code", "oauth_user", "none"}
_PAGINATION = {"cursor", "page", "offset", "link_header", "none"}


def _connector_issues(spec: dict) -> tuple[list[dict], dict]:
    issues: list[dict] = []

    def add(sev: str, field: str, msg: str) -> None:
        issues.append({"severity": sev, "field": field, "message": msg})

    for f in ("name", "base_url", "auth", "endpoints", "pagination", "rate_limit", "errors", "test_calls"):
        if not spec.get(f):
            add("error", f, "missing")
    base = str(spec.get("base_url", ""))
    if base and not base.startswith("https://"):
        add("error", "base_url", "must be https")
    auth = spec.get("auth") or {}
    atype = _slug(auth.get("type", "") if isinstance(auth, dict) else str(auth))
    secrets = [str(s) for s in _as_list(auth.get("secrets") if isinstance(auth, dict) else [])]
    if atype and atype not in _AUTH_TYPES:
        add("error", "auth.type", f"unknown auth type {atype!r}; use one of {sorted(_AUTH_TYPES)}")
    if atype not in ("none", "oauth_user", "") and not secrets:
        add("error", "auth.secrets", "list the secret NAMES the connector reads (e.g. VENDOR_API_KEY)")
    for s in secrets:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", s):
            add("error", "auth.secrets", f"{s[:10]}... is not a secret name (UPPER_SNAKE)")
    if atype == "api_key_query":
        add("warning", "auth.type", "keys in query strings leak into logs - prefer a header if the vendor allows it")
    side = []
    for i, e in enumerate(_as_list(spec.get("endpoints"))):
        if not isinstance(e, dict):
            add("error", f"endpoints[{i}]", "each endpoint needs method, path and purpose")
            continue
        m, p = str(e.get("method", "")).upper(), str(e.get("path", ""))
        if m not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            add("error", f"endpoints[{i}]", f"bad method {m!r}")
        if not p.startswith("/"):
            add("error", f"endpoints[{i}]", f"path {p!r} must start with /")
        if m in ("POST", "PUT", "PATCH", "DELETE"):
            side.append(f"{m} {p}")
    pag = spec.get("pagination") or {}
    style = _slug(pag.get("style", "") if isinstance(pag, dict) else str(pag).split()[0] if pag else "")
    if style and style not in _PAGINATION:
        add("warning", "pagination", f"style {style!r} - expected one of {sorted(_PAGINATION)}")
    errs = json.dumps(spec.get("errors", "")).lower()
    if spec.get("errors") and "429" not in errs and "retry" not in errs:
        add("warning", "errors", "say how 429/5xx are retried (backoff, Retry-After)")
    tcs = _as_list(spec.get("test_calls"))
    if len(tcs) < 2:
        add("error", "test_calls", "need at least 2 test calls: one read and one error case")
    found = _scan(json.dumps(spec))
    if found:
        add("error", "spec", "contains secret-like values: " + ", ".join(sorted({f['type'] for f in found})))
    if side:
        add("info", "endpoints", "write endpoints run as dry runs in sandbox and need approval: " + ", ".join(side))
    return issues, {"auth_type": atype, "secrets": secrets, "write_endpoints": side}


@hive_tool("platform")
def forge_validate_connector_spec(spec: dict) -> dict:
    """Validate a connector spec (the reusable API client) before it is registered.

    Args:
        spec: Object with name, base_url (https), auth ({"type": api_key_header|api_key_query|bearer|basic|
            oauth2_client_credentials|oauth2_authorization_code|oauth_user|none, "header": str, "secrets": [NAMES]}),
            endpoints ([{"method", "path", "purpose"}]), pagination ({"style": cursor|page|offset|link_header|none,
            ...}), rate_limit, errors (retry policy) and test_calls (list).

    Returns:
        valid flag, issues (severity, field, message), write endpoints that need sandbox guards, and whether a
        connector with the same name already exists (then it is a connector_modify job, not a new connector).
    """
    if not isinstance(spec, dict) or not spec:
        return err("spec must be a non-empty object")
    issues, facts = _connector_issues(spec)
    existing = _connector(spec.get("name", "")) if spec.get("name") else None
    return ok(valid=not any(i["severity"] == "error" for i in issues), issues=issues, **facts,
              existing_connector=existing["id"] if existing else None,
              job_type="connector_modify" if existing else "connector")


@hive_tool("platform", kind="action")
def forge_register_connector(spec: dict, client: str = "") -> dict:
    """Register a validated connector in the forge registry so any agent can attach it (simulated).

    Args:
        spec: The connector spec (same shape as forge_validate_connector_spec). It is validated again first.
        client: Client the connector is first built for (its test-pane session secrets decide ready vs draft).

    Returns:
        Connector id and version, status (ready when its secrets are set in the client's test pane and the test calls
        can run; draft otherwise), the recorded connector / connector_modify job and the test calls to run.
    """
    if not isinstance(spec, dict) or not spec.get("name"):
        return err("spec with at least a name is required")
    issues, facts = _connector_issues(spec)
    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
        return err("connector spec is not valid - fix these first", issues=errors)
    existing = _connector(spec["name"])
    cid = _client_id(client)
    pane = _clients()[cid]["test_pane"] if cid else {}
    missing = [s for s in facts["secrets"] if pane.get(s) != "set"]
    if existing:
        major, minor, _ = (existing["version"].split(".") + ["0", "0"])[:3]
        version, jtype, conn_id = f"{major}.{int(minor) + 1}.0", "connector_modify", existing["id"]
    else:
        version, jtype, conn_id = "0.1.0", "connector", _slug(spec["name"])
    status = "ready (sandbox)" if not missing else "draft - add " + ", ".join(missing) + " in the test pane"
    return ok(connector_id=conn_id, version=version, connector_status=status, kind="custom",
              client=_clients()[cid]["name"] if cid else (client or None), auth=facts["auth_type"],
              secrets=facts["secrets"],
              write_endpoints=facts["write_endpoints"],
              job={"id": "JOB-" + str(8000 + int(_token("J", conn_id, version)[2:], 16) % 1000), "type": jtype,
                   "status": "succeeded" if not missing else "waiting_for_input"},
              test_calls=[str(t)[:120] for t in _as_list(spec.get("test_calls"))][:5],
              note="Reusable by every agent and client once ready; secrets stay in the test pane / Secret Manager.",
              simulated=True)


# --- Forge Builder: static check (real, AST only - never executes the code) ----------------------------------------

_AGENT_CLASSES = {"Agent", "LlmAgent", "SequentialAgent", "ParallelAgent", "LoopAgent"}
_SECRET_NAME = re.compile(r"(?i)(api_?key|secret|token|password|passwd|pwd|credential|access_?key)")


def _split_code(text: str) -> tuple[str, str]:
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S)
    if not blocks:
        return text, ""
    tests = [b for b in blocks if re.search(r"^\s*def test_", b, re.M)]
    code = [b for b in blocks if b not in tests]
    return "\n\n".join(code), "\n\n".join(tests)


def _parse(text: str) -> tuple[ast.Module | None, str | None, SyntaxError | None]:
    """Parse source; if it only fails because quotes arrived JSON-escaped (\\"), parse the unescaped form."""
    try:
        return ast.parse(text), None, None
    except SyntaxError as e:
        fixed = text.replace('\\"', '"').replace("\\'", "'")
        if fixed != text:
            try:
                return ast.parse(fixed), "input quotes arrived escaped (\\\") - checked the unescaped source", None
            except SyntaxError:
                pass
        return None, None, e


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_call_name(node.value)}.{node.attr}"
    return ""


@hive_tool("platform")
def forge_static_check(code: str, tests: str = "", agent: str = "", version: str = "",
                       required_secrets: list[str] | None = None, partial: bool = False) -> dict:
    """Statically check generated ADK agent code and its pytest tests (AST and regex only - nothing is executed).

    Args:
        code: The agent module source (agent.py), or a sample doc key such as 'forge_code_price_tracker_draft'
            whose python blocks hold the code and the tests.
        tests: The pytest module source (test_agent.py). Optional when the doc key already contains the tests.
        agent: Agent id (snake_case). With version, a passing check returns the static_check_id the test bench needs.
        version: Version being built, e.g. 'v5'.
        required_secrets: Secret NAMES the spec lists; each must be read from the environment or Secret Manager.
        partial: True when checking only the changed functions of an existing agent (a change request): module
            structure (ADK import, root_agent, required secrets) is skipped and every public function is a tool.

    Returns:
        passed (no errors), errors and warnings (line, rule, message), tools found with docstring/type-hint status,
        test count and tools without a test, secrets read, and static_check_id when passed with agent and version.
    """
    src, origin = _text(code)
    test_src = _materialise(tests or "")
    if origin != "inline text" or "```" in src:
        c, t = _split_code(src)
        src, test_src = c, test_src or t
    if not src.strip():
        return err("no code to check")
    errors: list[dict] = []
    warnings: list[dict] = []

    def add(bucket: list, line: int, rule: str, msg: str) -> None:
        bucket.append({"line": line, "rule": rule, "message": msg})

    tree, note, e = _parse(src)
    if tree is None:
        return ok(passed=False, errors=[{"line": e.lineno, "rule": "syntax", "message": str(e.msg)}], warnings=[],
                  static_check_id=None, executed=False)
    if note:
        add(warnings, 1, "input", note)
        src = ast.unparse(tree)

    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    imported = {a.asname or a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                for a in n.names}
    if not partial and not any(isinstance(n, ast.ImportFrom) and (n.module or "").startswith("google.adk")
                               for n in ast.walk(tree)):
        add(errors, 1, "adk_import", "no import from google.adk (e.g. from google.adk.agents import Agent)")
    if not partial and not any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "root_agent"
                                                                 for t in n.targets) for n in tree.body):
        add(errors, 1, "root_agent", "no module-level root_agent = Agent(...) for the runtime to load")

    tool_refs: list[tuple[str, int]] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n.func).split(".")[-1] in _AGENT_CLASSES:
            cls = _call_name(n.func).split(".")[-1]
            kws = {k.arg: k.value for k in n.keywords if k.arg}
            if "name" not in kws and not partial:
                add(errors, n.lineno, "adk_structure", f"{cls}(...) needs name=")
            if cls in ("Agent", "LlmAgent"):
                if "instruction" not in kws and not partial:
                    add(errors, n.lineno, "adk_structure", f"{cls}(...) needs instruction=")
                if "model" not in kws:
                    add(warnings, n.lineno, "FS-10", "model not set - read it from the forge tier config")
                elif isinstance(kws["model"], ast.Constant) and isinstance(kws["model"].value, str):
                    add(warnings, n.lineno, "FS-10", f"hard-coded model id {kws['model'].value!r} - read it from the "
                        "tier config (e.g. os.environ['FORGE_MODEL'])")
            elif "sub_agents" not in kws and not partial:
                add(errors, n.lineno, "adk_structure", f"{cls}(...) needs sub_agents=")
            if isinstance(kws.get("tools"), ast.List):
                tool_refs += [(e.id, e.lineno) for e in kws["tools"].elts if isinstance(e, ast.Name)]

    if partial and not tool_refs:
        tool_refs = [(n, f.lineno) for n, f in funcs.items() if not n.startswith("_")]
    tools_out = []
    for name, line in dict.fromkeys(tool_refs):
        fn = funcs.get(name)
        if not fn:
            if name in imported:
                add(warnings, line, "FS-01", f"tool {name} is imported - its contract is checked in its own module")
            else:
                add(errors, line, "FS-01", f"tool {name} is not defined in the module")
            continue
        doc = ast.get_docstring(fn) or ""
        for d in fn.decorator_list:
            if re.search(r"tool|Agent", ast.unparse(d)):
                add(errors, d.lineno, "FS-01", f"{name}: ADK function tools are plain functions - remove "
                    f"@{ast.unparse(d)} and list the function in tools=[...]")
        params = [a for a in fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "tool_context")]
        untyped = [a.arg for a in params if a.annotation is None]
        if len(doc) < 30:
            add(errors, fn.lineno, "FS-01", f"{name}: docstring missing or under 30 chars - the model reads it")
        elif params and "Args:" not in doc:
            add(warnings, fn.lineno, "FS-01", f"{name}: docstring has no Args: section")
        if untyped:
            add(errors, fn.lineno, "FS-01", f"{name}: parameters without type hints: {', '.join(untyped)}")
        if fn.returns is None:
            add(warnings, fn.lineno, "FS-01", f"{name}: add a return type (dict)")
        returns = [r.value for r in ast.walk(fn) if isinstance(r, ast.Return) and isinstance(r.value, ast.Dict)]
        bad_status = sorted({str(v.value) for d in returns for key, v in zip(d.keys, d.values)
                             if isinstance(key, ast.Constant) and key.value == "status"
                             and isinstance(v, ast.Constant) and v.value not in ("ok", "error")})
        if bad_status:
            add(warnings, fn.lineno, "FS-01", f"{name}: status must be 'ok' or 'error' (found {', '.join(bad_status)}) "
                "- put other states in their own key")
        if fn.args.vararg or fn.args.kwarg:
            add(errors, fn.lineno, "FS-01", f"{name}: *args/**kwargs cannot be described to the model")
        tools_out.append({"tool": name, "line": fn.lineno, "docstring": len(doc) >= 30, "typed": not untyped})
    if not tool_refs:
        add(warnings, 1, "adk_structure", "no tools=[...] list found on any agent" if not partial else
            "no public functions to check")
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"gemini-[\w.-]+", n.value) and \
                not any(w["line"] == n.lineno and w["rule"] == "FS-10" for w in warnings):
            add(warnings, n.lineno, "FS-10", f"model id literal {n.value!r} (also as a fallback) - use the tier "
                "config only")

    secrets_read: list[str] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            name = _call_name(n.func)
            if name in ("eval", "exec", "compile", "__import__") or name.startswith("subprocess.") or name in (
                    "os.system", "os.popen", "pickle.loads", "shutil.rmtree"):
                add(errors, n.lineno, "safety", f"{name}() is not allowed in forge agents")
            if name.startswith("requests.") and name.split(".")[-1] in ("get", "post", "put", "patch", "delete",
                                                                        "request") and not any(
                    k.arg == "timeout" for k in n.keywords):
                add(warnings, n.lineno, "FS-05", f"{name}() without timeout= (and no retry/backoff)")
            if name in ("os.getenv", "os.environ.get") and n.args and isinstance(n.args[0], ast.Constant):
                secrets_read.append(str(n.args[0].value))
            if name in ("print", "logging.info", "logging.debug", "logger.info", "logger.debug") and any(
                    "environ" in ast.unparse(a) or _SECRET_NAME.search(ast.unparse(a)) for a in n.args):
                add(warnings, n.lineno, "FS-09", f"{name}() may log a secret")
        if isinstance(n, ast.Subscript) and _call_name(n.value) == "os.environ" and isinstance(n.slice, ast.Constant):
            secrets_read.append(str(n.slice.value))
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            for t in n.targets:
                if isinstance(t, ast.Name) and _SECRET_NAME.search(t.id) and len(n.value.value) >= 6 and \
                        not re.fullmatch(r"[A-Z][A-Z0-9_]+", n.value.value):
                    add(errors, n.lineno, "FS-02", f"hard-coded secret in {t.id} - read it from the environment / "
                        "Secret Manager")
        if isinstance(n, ast.keyword) and n.arg and _SECRET_NAME.search(n.arg) and isinstance(n.value, ast.Constant) \
                and isinstance(n.value.value, str) and len(n.value.value) >= 6:
            add(errors, n.lineno, "FS-02", f"hard-coded secret passed as {n.arg}=")
    if "secretmanager" in src or "access_secret_version" in src:
        secrets_read.append("(Secret Manager client)")
    for f in _scan(src):
        line = src.count("\n", 0, f["start"]) + 1
        if not any(e["line"] == line and e["rule"] == "FS-02" for e in errors):
            add(errors, line, "FS-02", f"{f['type']} literal in code")
    for s in [] if partial else required_secrets or []:
        if s not in secrets_read and s not in src:
            add(errors, 1, "FS-02", f"required secret {s} is never read from the environment / Secret Manager")

    tests_out: dict = {"count": 0}
    if test_src.strip():
        try:
            ttree, tnote, terr = _parse(test_src)
            if ttree is None:
                raise terr
            if tnote:
                test_src = ast.unparse(ttree)
            names = [n.name for n in ast.walk(ttree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name.startswith("test_")]
            uncovered = [t["tool"] for t in tools_out if t["tool"] not in test_src]
            tests_out = {"count": len(names), "names": names[:20], "tools_without_test": uncovered}
            if not names:
                add(errors, 1, "FS-03", "test module has no test_ functions")
            for t in uncovered:
                add(warnings, 1, "FS-03", f"no test exercises tool {t}")
            for f in _scan(test_src):     # dummy values in tests are fine; real key formats are not
                if f["type"] != "generic_secret_assignment":
                    add(errors, test_src.count("\n", 0, f["start"]) + 1, "FS-02", f"{f['type']} literal in tests")
        except SyntaxError as e:
            add(errors, e.lineno or 1, "syntax", f"tests: {e.msg}")
    else:
        add(errors, 1, "FS-03", "no tests supplied - every change ships with a passing test suite")

    passed = not errors
    aid, ver = _slug(agent), _ver(version)
    return ok(passed=passed, errors=errors[:20], warnings=warnings[:20], tools=tools_out, tests=tests_out,
              secrets_read=sorted(set(secrets_read)), lines=len(src.splitlines()),
              static_check_id=_token("SC", aid, ver, "pass") if passed and aid and ver else None,
              note=None if (aid and ver) or not passed else "pass agent and version to get a static_check_id",
              executed=False)


# --- Test Bench ----------------------------------------------------------------------------------------------------


@hive_tool("platform", kind="action")
def forge_run_tests(agent: str, version: str = "", client: str = "", static_check_id: str = "",
                    tests: list[str] | None = None, secrets: list[str] | None = None) -> dict:
    """Run an agent version's test suite in the forge test pane with session secrets (simulated, deterministic).

    Args:
        agent: Agent id, e.g. 'shopify_order_support_tracker' (or the new agent's id for a fresh build).
        version: Version to test, e.g. 'v4'. Defaults to the latest recorded version.
        client: Client of a NEW agent (existing agents already know their client).
        static_check_id: Required for a version that is not recorded yet - the id from a passing forge_static_check.
        tests: Names of tests added in this build (new agents or new versions).
        secrets: Secret NAMES a new agent needs; they must be set in the client's test pane.

    Returns:
        passed / failed / blocked counts, the release gate (pass only when every test passes), failures with
        expected, actual, trace, log and a fix hint, blocked tests with the missing session secret, session secrets
        by name (set / missing - never values) and test_run_id when the gate passes.
    """
    aid = _slug(agent)
    rec = _agent(aid)
    if rec:
        aid = rec["id"]
    cid = rec["client"] if rec else _client_id(client)
    if not cid:
        return err("unknown client - pass client for a new agent", clients=sorted(_clients()))
    pane = _clients()[cid]["test_pane"]
    suite = fixture("forge_tests")["suites"].get(aid)
    recorded = {v["version"]: v for v in _versions(aid)}
    ver = _ver(version) or (rec["latest_version"] if rec else "v1")
    new_version = ver not in recorded
    if rec and new_version and _vnum(ver) <= _vnum(rec["latest_version"]):
        return err(f"{ver} is older than the latest version {rec['latest_version']}")
    if new_version and static_check_id.strip().upper() != _token("SC", aid, ver, "pass"):
        return err(f"{aid} {ver} is not a recorded build - run forge_static_check(agent='{aid}', version='{ver}') "
                   "and pass its static_check_id", gate="fail")
    results, failures, blocked = [], [], []
    rows = [t for t in suite["tests"] if _vnum(t["since"]) <= _vnum(ver)] if suite else []
    if not suite and not new_version:
        m = re.fullmatch(r"(\d+)/(\d+)", str(recorded[ver].get("tests", "")))
        if not (m and m.group(1) == m.group(2)):
            return err(f"no test-pane results recorded for {aid} {ver}: {recorded[ver].get('tests')}", gate="fail")
        names = {v["version"]: s for v, s in _snapshots(aid)}[ver].get("tests", [])
        rows = [{"id": f"S{i:02d}", "name": n, "kind": "recorded", "ms": 300} for i, n in enumerate(names, 1)]
    known = {t["name"] for t in rows}
    rows += [{"id": f"N{i:02d}", "name": n, "kind": "new", "ms": 250} for i, n in enumerate(tests or [], 1)
             if n not in known]
    if not rows:
        return err("no tests to run - the build must supply its tests", gate="fail")
    recorded_results = (suite or {}).get("results", {}).get(ver, {}) if not new_version else {}
    ignored = [s for s in (secrets or []) if _WORKSPACE_SECRET.search(s)]
    secrets = [s for s in (secrets or []) if s not in ignored]
    missing_new = [s for s in secrets if pane.get(s) != "set"]
    for t in rows:
        need = t.get("needs_secret")
        if (need and pane.get(need) != "set") or (t["kind"] == "new" and missing_new):
            blocked.append({"test": t["name"], "missing_session_secret": need or ", ".join(missing_new)})
            results.append("blocked")
        elif t["id"] in recorded_results:
            failures.append({"test": t["name"], "kind": t["kind"], **recorded_results[t["id"]]})
            results.append("fail")
        else:
            results.append("pass")
    gate = "pass" if all(r == "pass" for r in results) else "fail"
    needed = {*(rec["secrets"] if rec else []), *(secrets or []), *[t["needs_secret"] for t in rows
                                                                       if t.get("needs_secret")]}
    session = {s: pane.get(s, "missing") for s in sorted(needed)}
    return ok(agent=aid, version=ver, client=_clients()[cid]["name"],
              mode="new build (simulated from the passing static check)" if new_version else "recorded test-pane run",
              total=len(rows), passed=results.count("pass"), failed=results.count("fail"),
              blocked=results.count("blocked"), gate=gate, failures=failures, blocked_tests=blocked,
              session_secrets=session, duration_s=round(sum(t["ms"] for t in rows) / 1000, 1),
              **({"ignored_secrets": ignored, "note": "Workspace connectors use the signed-in user's OAuth - no session "
                  "secret is needed for them"} if ignored else {}),
              test_run_id=_token("TR", aid, ver, "pass") if gate == "pass" else None, simulated=True)


# --- Release Manager -----------------------------------------------------------------------------------------------


@hive_tool("platform")
def forge_version_history(agent: str) -> dict:
    """List an agent's versions with the plain-English change request, tests, sandbox/client dates and reviewer.

    Args:
        agent: Agent id or name.

    Returns:
        Versions oldest to newest (version, date, kind, request, tests, sandbox, client, built_by, reviewer, job) and
        which version is live in sandbox and for the client.
    """
    a = _agent(agent)
    if not a:
        return err(f"no forge agent matching {agent!r}", available=[x["id"] for x in _agents()])
    rows = [{k: v.get(k) for k in ("version", "date", "kind", "request", "tests", "sandbox", "client", "built_by",
                                   "reviewer", "job")} | ({"state": v["state"]} if v.get("state") else {})
            for v in _versions(a["id"])]
    return ok(agent=a["id"], name=a["name"], client=_clients()[a["client"]]["name"], versions=rows,
              live={"sandbox": a["sandbox_version"], "client": a["client_version"]}, latest=a["latest_version"])


@hive_tool("platform")
def forge_diff_versions(agent: str, from_version: str = "", to_version: str = "") -> dict:
    """Diff two versions of an agent's spec: tools, connectors, rules, settings and tests added, removed or changed.

    Args:
        agent: Agent id or name.
        from_version: Older version, e.g. 'v1'. Defaults to the version live for the client (or the previous one).
        to_version: Newer version. Defaults to the latest version.

    Returns:
        Added / removed items per spec field, changed settings (old -> new) and the change requests in between.
    """
    a = _agent(agent)
    if not a:
        return err(f"no forge agent matching {agent!r}", available=[x["id"] for x in _agents()])
    snaps = {v["version"]: (v, s) for v, s in _snapshots(a["id"])}
    order = list(snaps)
    to_v = _ver(to_version) or order[-1]
    from_v = _ver(from_version) or (a["client_version"] if a["client_version"] and a["client_version"] != to_v
                                    else order[max(0, order.index(to_v) - 1)] if to_v in order else "")
    if to_v not in snaps and _vnum(to_v) > _vnum(order[-1]):
        return ok(agent=a["id"], recorded=False, to_version=to_v, latest_recorded=order[-1],
                  note=f"{to_v} is not in the version history yet (built in this run) - describe its change from the "
                       "change request and the test run instead of a diff")
    if from_v not in snaps or to_v not in snaps:
        return err("unknown version", versions=order)
    if _vnum(from_v) >= _vnum(to_v):
        return err("from_version must be older than to_version", versions=order)
    s0, s1 = snaps[from_v][1], snaps[to_v][1]
    diff = {}
    for f in ("connectors", "tools", "rules", "tests"):
        add = [x for x in s1.get(f, []) if x not in s0.get(f, [])]
        rem = [x for x in s0.get(f, []) if x not in s1.get(f, [])]
        if add or rem:
            diff[f] = {"added": add, "removed": rem}
    st0, st1 = s0.get("settings", {}), s1.get("settings", {})
    changed = {k: {"from": st0.get(k), "to": st1.get(k)} for k in sorted({*st0, *st1}) if st0.get(k) != st1.get(k)}
    if changed:
        diff["settings"] = changed
    if s0.get("topology") != s1.get("topology"):
        diff["topology"] = {"from": s0.get("topology"), "to": s1.get("topology")}
    steps = [{"version": v, "request": snaps[v][0]["request"], "tests": snaps[v][0]["tests"]}
             for v in order if _vnum(from_v) < _vnum(v) <= _vnum(to_v)]
    return ok(agent=a["id"], from_version=from_v, to_version=to_v, diff=diff, change_requests=steps)


def _refused(gate: str, reason: str) -> dict:
    return ok(deployed=False, refused_by_gate=gate, reason=reason, simulated=True)


@hive_tool("platform", kind="action")
def forge_deploy(agent: str, version: str, target: str = "sandbox", client: str = "", test_run_id: str = "",
                 sandbox_deploy_id: str = "", approved_by: str = "", secrets: list[str] | None = None) -> dict:
    """Deploy an agent version to the sandbox or promote it to the client, enforcing the release gate (simulated).

    Args:
        agent: Agent id.
        version: Version to deploy, e.g. 'v5'.
        target: 'sandbox' (review before release) or 'client' (live for the client).
        client: Client of a new agent that is not in the forge catalog yet.
        test_run_id: test_run_id from a passing forge_run_tests (not needed for recorded versions whose suite passed).
        sandbox_deploy_id: For target 'client' when the sandbox deploy happened in this session.
        approved_by: Reviewer email - required for 'client'; must be an active admin or builder other than the
            builder of the version.
        secrets: Secret NAMES of a new agent (existing agents already declare theirs).

    Returns:
        deployed=true with the deployment id, endpoint label, secret REFERENCES (never values), rollback version and
        deploy job - or deployed=false with refused_by_gate (tests, sandbox, approval, secrets, prospect) and reason.
    """
    tgt = _slug(target)
    if tgt not in ("sandbox", "client"):
        return err("target must be 'sandbox' or 'client'")
    rec = _agent(agent)
    aid = rec["id"] if rec else _slug(agent)
    cid = rec["client"] if rec else _client_id(client)
    if not cid:
        return err("unknown client - pass client for a new agent")
    cl = _clients()[cid]
    ver = _ver(version)
    if not ver:
        return err("version is required, e.g. 'v5'")
    vrec = next((v for v in _versions(aid) if v["version"] == ver), None)
    gates: dict[str, str] = {}
    t = str((vrec or {}).get("tests", ""))
    m = re.fullmatch(r"(\d+)/(\d+)", t)
    if test_run_id.strip().upper() == _token("TR", aid, ver, "pass"):
        gates["tests"] = "pass (test run " + test_run_id.strip().upper() + ")"
    elif m and m.group(1) == m.group(2):
        gates["tests"] = f"pass (recorded {t})"
    else:
        return _refused("tests", f"tests have not all passed for {aid} {ver}" + (f" (recorded {t})" if t else "")
                        + " - run the test bench, fix the failures as a new version, then deploy that version")
    secrets = rec["secrets"] if rec else [s for s in (secrets or []) if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", s)
                                          and not _WORKSPACE_SECRET.search(s)]
    job = "JOB-" + str(8000 + int(_token("D", aid, ver, tgt)[2:], 16) % 1000)
    if tgt == "sandbox":
        refs = {s: f"secret-manager://{cid}/sandbox/{s} (sandbox scope)" for s in secrets}
        return ok(deployed=True, deployment_id=_token("DEP-SBX", aid, ver), agent=aid, version=ver, target="sandbox",
                  client=cl["name"], endpoint=f"sandbox/{cid}/{aid}@{ver}", gates=gates, secret_references=refs,
                  dry_run="DRY_RUN=true - sends and writes become drafts", job={"id": job, "type": "deploy"},
                  next_step="review in sandbox, then promote to the client with an approver", simulated=True)
    if cl["kind"] == "prospect":
        return _refused("prospect", cl.get("sandbox_only_reason")
                        or f"{cl['name']} is a prospect - agents stay in the sandbox until the client signs")
    if sandbox_deploy_id.strip().upper() == _token("DEP-SBX", aid, ver):
        gates["sandbox"] = "deployed in this session"
    elif vrec and vrec.get("sandbox"):
        gates["sandbox"] = f"in sandbox since {vrec['sandbox']}"
    else:
        return _refused("sandbox", f"{ver} has not been deployed to the sandbox for review")
    u = _user(approved_by)
    if not u or u["status"] != "active" or u["role"] not in ("admin", "builder"):
        return _refused("approval", "client promotion needs approved_by = an active admin or builder")
    if vrec and u["email"] == vrec.get("built_by"):
        return _refused("approval", f"{u['email']} built {ver}; a different reviewer must approve (four-eyes)")
    iap = fixture("forge_access")["iap"]
    if u["email"].split("@")[-1] != iap["staff_domain"]:
        return _refused("approval", "approver must be " + (iap.get("staff_label") or f"staff on {iap['staff_domain']}"))
    gates["approval"] = f"{u['name']} ({u['role']})"
    missing = [s for s in secrets if s not in cl["secret_manager"]]
    if missing:
        return _refused("secrets", f"Secret Manager for {cl['name']} is missing {', '.join(missing)} - ask the "
                        "client admin to add them (never paste values into the forge)")
    gates["secrets"] = "all present in Secret Manager" if secrets else "none needed (OAuth as the signed-in user)"
    return ok(deployed=True, deployment_id=_token("DEP-CLI", aid, ver), agent=aid, version=ver, target="client",
              client=cl["name"],
              endpoint=f"client/{cid}/{aid}@{ver}", gates=gates,
              secret_references={s: f"secret-manager://{cid}/{s} (latest)" for s in secrets},
              rollback_to=rec["client_version"] if rec and rec["client_version"] and rec["client_version"] != ver
              else "none - first client release; rolling back means disabling this deployment",
              already_live=bool(rec and rec["client_version"] == ver), job={"id": job, "type": "deploy"},
              simulated=True)


# --- Jobs & Tune-up ------------------------------------------------------------------------------------------------


@hive_tool("platform")
def forge_job_log(job_type: str = "", status: str = "", target: str = "", client: str = "", since: str = "") -> dict:
    """Analyse the forge job log: job types, status, durations, failure reasons and jobs waiting for a builder.

    Args:
        job_type: Optional filter - create, modify, fork, deploy, connector, connector_modify or tune_up.
        status: Optional filter - queued, running, waiting_for_input, succeeded, failed, cancelled.
        target: Optional agent or connector id.
        client: Optional client name or id.
        since: Optional ISO date; only jobs started on or after it.

    Returns:
        Counts by type and status, median minutes per type, failures with reasons, jobs waiting for input (with
        what they wait on and their age), in-flight jobs and the most recent matching jobs (compact).
    """
    jobs = fixture("forge_jobs")["jobs"]
    jt, st = _slug(job_type), _slug(status)
    cid = _client_id(client) if client else None
    if client and not cid:
        return err(f"unknown client {client!r}", clients=sorted(_clients()))
    if jt and jt not in (*JOB_TYPES, "tune_up"):
        return err(f"unknown job type {job_type!r}", types=[*JOB_TYPES, "tune_up"])
    rows = [j for j in jobs
            if (not jt or j["type"] == jt or jt in j.get("tags", []))
            and (not st or j["status"] == st)
            and (not target or _slug(target) in j["target"])
            and (not cid or j["client"] == cid)
            and (not since or j["started"][:10] >= since[:10])]
    by_type: dict = {}
    for j in rows:
        by_type.setdefault(j["type"], []).append(j)
    names = {k: v["name"] for k, v in _clients().items()}

    def age(j: dict) -> float:
        return round((NOW - dt.datetime.fromisoformat(j["started"])).total_seconds() / 3600, 1)

    return ok(window=fixture("forge_jobs")["window"], matched=len(rows),
              by_type={k: len(v) for k, v in sorted(by_type.items())},
              by_status={s: sum(1 for j in rows if j["status"] == s) for s in JOB_STATUSES
                         if any(j["status"] == s for j in rows)},
              median_minutes={k: statistics.median([j["minutes"] for j in v if j["minutes"] is not None])
                              for k, v in sorted(by_type.items()) if any(j["minutes"] is not None for j in v)},
              failures=[{"id": j["id"], "type": j["type"], "target": j["target"], "started": j["started"][:10],
                         "reason": j.get("reason")} for j in rows if j["status"] == "failed"],
              waiting_for_input=[{"id": j["id"], "type": j["type"], "target": j["target"], "client": names[j["client"]],
                                  "waiting_on": j.get("waiting_on"), "age_hours": age(j)}
                                 for j in rows if j["status"] == "waiting_for_input"],
              in_flight=[{"id": j["id"], "type": j["type"], "target": j["target"], "status": j["status"],
                          "age_hours": age(j)} for j in rows if j["status"] in ("running", "queued")],
              cancelled=[{"id": j["id"], "target": j["target"], "reason": j.get("reason")}
                         for j in rows if j["status"] == "cancelled"],
              recent=[{"id": j["id"], "type": j["type"] + ("/tune_up" if "tune_up" in j.get("tags", []) else ""),
                       "target": j["target"], "version": j["version"], "status": j["status"],
                       "started": j["started"], "minutes": j["minutes"]}
                      for j in sorted(rows, key=lambda x: x["started"], reverse=True)[:12]])


_TUNE_CHANGE = {
    "FS-01": "add docstrings, type hints and status dicts to every tool",
    "FS-02": "move secret literals to environment / Secret Manager references",
    "FS-03": "generate the missing tests (builder reviews the expected values)",
    "FS-04": "pin each connector to its current minor version",
    "FS-05": "add 3 retries with exponential backoff and a 30 s timeout to connector calls",
    "FS-06": "follow pagination to the last page with a declared cap",
    "FS-07": "compute and show dates in the client's time zone",
    "FS-08": "trim memory to ids, timestamps and short summaries with 90-day retention",
    "FS-09": "switch to structured logs without payload bodies; redact secrets",
    "FS-10": "read the model from the forge tier config",
    "FS-11": "add an acceptance test for the declared output format",
    "FS-12": "guard sends and writes with DRY_RUN in sandbox",
    "FS-13": "move Workspace access to OAuth as the signed-in user",
    "FS-14": "replace raw errors with plain-English messages",
}


@hive_tool("platform")
def forge_tune_up_check(agent: str) -> dict:
    """Check an existing agent against the current forge standards and list what a tune-up job would change.

    Args:
        agent: Agent id or name, e.g. 'weekly_status_recap_generator'.

    Returns:
        Standards version the agent was built to vs current, each failing standard with the finding, the change a
        tune-up would make (auto or needs builder approval), what must not change (rules, outputs, schedule,
        connectors' scopes), tests to re-run, the next version and any tune-up job already queued.
    """
    a = _agent(agent)
    if not a:
        return err(f"no forge agent matching {agent!r}", available=[x["id"] for x in _agents()])
    stds = fixture("forge_standards")
    by_id = {s["id"]: s for s in stds["standards"]}
    info = stds["agents"].get(a["id"], {"standards_version": "unknown", "fails": {}})
    snap = _snapshots(a["id"])[-1][1] if _versions(a["id"]) else {}
    tz = _clients()[a["client"]]["time_zone"]
    changes = []
    touched = {"model", "retries", "logging"} | {k for sid, keys in (("FS-08", ("memory",)), ("FS-07", (
        "date_time_zone", "time_zone")), ("FS-12", ("dry_run",))) if sid in info["fails"] for k in keys}
    for sid, finding in sorted(info["fails"].items()):
        change = _TUNE_CHANGE[sid] + (f" ({tz})" if sid == "FS-07" else "")
        if sid == "FS-04":
            pins = [f"{c.split('@')[0].split(' ')[0]} -> {(_connector(c) or {}).get('version', '?')[:3]}.x"
                    for c in snap.get("connectors", [])]
            change += ": " + ", ".join(pins)
        changes.append({"standard": sid, "title": by_id[sid]["title"], "finding": finding, "change": change,
                        "auto": by_id[sid]["auto_fix"], "behaviour_change": "none" if by_id[sid]["auto_fix"]
                        else "none intended - needs builder review"})
    queued = [j["id"] + " (" + j["status"] + ")" for j in fixture("forge_jobs")["jobs"]
              if j["target"] == a["id"] and "tune_up" in j.get("tags", []) and j["status"] in ("queued", "running")]
    return ok(agent=a["id"], name=a["name"], client=_clients()[a["client"]]["name"],
              built_to=info["standards_version"], current=stds["current_version"], compliant=not changes,
              tune_up=changes, must_not_change={"rules": snap.get("rules", []),
                                                "settings": {k: v for k, v in snap.get("settings", {}).items()
                                                             if k not in touched},
                                                "tools": snap.get("tools", [])},
              full_suite_tests_to_rerun=len(snap.get("tests", [])), next_version=f"v{_vnum(a['latest_version']) + 1}",
              job_type="modify (tune_up)", already_queued=queued)


@hive_tool("platform", kind="action")
def forge_record_job(job_type: str, target: str, prompt: str, client: str = "", version: str = "",
                     status: str = "queued") -> dict:
    """Record a forge job in the durable job log (simulated); the prompt is secret-redacted before it is stored.

    Args:
        job_type: create, modify, fork, deploy, connector, connector_modify, or tune_up (stored as modify/tune_up).
        target: Agent or connector id the job acts on.
        prompt: The builder's plain-English request (one or two lines).
        client: Client name or id.
        version: Version the job produces, e.g. 'v5'.
        status: queued, running, waiting_for_input, succeeded or failed.

    Returns:
        Job id, stored (redacted) prompt, redaction findings by type, status and recorded time. In-flight jobs
        survive a page reload.
    """
    jt = _slug(job_type)
    tags = []
    if jt == "tune_up":
        jt, tags = "modify", ["tune_up"]
    if jt not in JOB_TYPES:
        return err(f"unknown job type {job_type!r}", types=[*JOB_TYPES, "tune_up"])
    st = _slug(status) or "queued"
    if st not in JOB_STATUSES or st == "cancelled":
        return err(f"status must be one of {JOB_STATUSES[:-1]}")
    if not target or not prompt:
        return err("target and prompt are required")
    cid = _client_id(client)
    redacted, findings = _redact(_materialise(prompt))
    jid = "JOB-" + str(8000 + int(_token("J", jt, target, version, prompt[:80])[2:], 16) % 1000)
    return ok(job_id=jid, type=jt, tags=tags, target=_slug(target), client=_clients()[cid]["name"] if cid else
              (client or None), version=_ver(version) or None, job_status=st, prompt_stored=redacted[:400],
              redactions=sorted({f["type"] for f in findings}), recorded_at=NOW.isoformat(timespec="minutes"),
              survives_reload=True, simulated=True)


# --- Forge Governance ----------------------------------------------------------------------------------------------


@hive_tool("platform")
def forge_access_review(client: str = "") -> dict:
    """Review forge access: roles, client-scoped demo access, stale accounts, external users and IAP settings.

    Args:
        client: Optional client name or id to review only the users who can see that client.

    Returns:
        Role counts, users (role, clients, last active, expiry), findings by severity with a recommended action
        and the IAP configuration in front of the forge.
    """
    acc = fixture("forge_access")
    staff = acc["iap"]["staff_domain"]
    cid = _client_id(client) if client else None
    if client and not cid:
        return err(f"unknown client {client!r}", clients=sorted(_clients()))
    users = [u for u in acc["users"] if not cid or not _scoped(u["role"]) or cid in u["clients"]]
    low_role = next((r for r in acc["roles"] if _scoped(r)), "demo")
    org = acc.get("org_label", "organisation")
    names = {k: v["name"] for k, v in _clients().items()}
    findings = []

    def add(sev: str, who: str, issue: str, action: str) -> None:
        findings.append({"severity": sev, "user": who, "issue": issue, "action": action})

    for u in users:
        dom = u["email"].split("@")[-1]
        idle = (TODAY - dt.date.fromisoformat(u["last_active"])).days
        if u["role"] in ("admin", "builder") and dom != staff:
            add("high", u["email"], f"external account with the {u['role']} role (can deploy and see every client)",
                f"downgrade to {low_role} or time-box with an expiry and named sponsor")
        if u["role"] in ("admin", "builder") and idle > 60 and u["status"] == "active":
            add("medium", u["email"], f"{u['role']} inactive for {idle} days" + (f" - {u['note']}" if u.get("note")
                                                                                  else ""),
                "disable or remove the role")
        if _scoped(u["role"]):
            exp = u.get("assignment_expires")
            if exp and exp < TODAY.isoformat() and u["status"] == "active":
                add("high", u["email"], f"{u['role']} assignment expired {exp} but the account is active",
                    "remove the client assignment and the IAP grant")
            if not u["clients"]:
                add("low", u["email"], f"{u['role']} user with no client assigned (sees nothing)",
                    "assign a client or remove the IAP grant")
            foreign = [c for c in u["clients"] if acc["client_domains"].get(c) != dom]
            if foreign:
                add("high", u["email"], f"can see another {org}'s agents: " +
                    ", ".join(names.get(c, c) for c in foreign), "remove cross-client assignment unless the "
                    "client owner approved it in writing")
            elif exp and exp <= (TODAY + dt.timedelta(days=30)).isoformat() and exp >= TODAY.isoformat():
                add("info", u["email"], f"assignment expires {exp}", "renew or let it lapse")
    admins = [u for u in acc["users"] if u["role"] == "admin"]
    if acc["iap"].get("context_aware_access") == "not configured":
        add("low", "(all admins)", "no context-aware access level on the forge for admins",
            "require a managed device / access level for admin actions")
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    findings.sort(key=lambda f: order[f["severity"]])
    return ok(scope=names[cid] if cid else "all clients",
              roles={r: sum(1 for u in users if u["role"] == r) for r in acc["roles"]}, admins=len(admins),
              users=[{"email": u["email"], "role": u["role"], "clients": ["all"] if u["clients"] == ["*"] else
                      [names.get(c, c) for c in u["clients"]], "last_active": u["last_active"],
                      "expires": u.get("assignment_expires")} for u in users],
              findings=findings, iap=acc["iap"],
              role_definitions={r: v["description"] for r, v in acc["roles"].items()})


@hive_tool("platform")
def forge_check_access(user: str, client: str, action: str = "view") -> dict:
    """Decide whether a user may perform an action on a client's agents in the forge (role and client scope).

    Args:
        user: User email.
        client: Client name or id.
        action: view, try_in_sandbox, build, test, deploy_sandbox, deploy_client, manage_connectors, manage_users or
            view_jobs.

    Returns:
        allowed (true/false), the reason (role, client assignment, expiry, account status), the user's role, the
        clients a demo user is assigned to and notes such as a cross-client assignment or an external staff account.
    """
    acc = fixture("forge_access")
    u = _user(user)
    if not u:
        return ok(allowed=False, user=user, reason="no forge account - IAP denies sign-in")
    cid = _client_id(client)
    if not cid:
        return err(f"unknown client {client!r}", clients=sorted(_clients()))
    act = _slug(action)
    act = {"deploy": "deploy_client", "promote": "deploy_client", "see": "view", "try": "try_in_sandbox",
           "edit": "build", "modify": "build", "create": "build", "admin": "manage_users"}.get(act, act)
    allowed_actions = {a for r in acc["roles"].values() for a in r["actions"]}
    if act not in allowed_actions:
        return err(f"unknown action {action!r}", actions=sorted(allowed_actions))
    name = _clients()[cid]["name"]
    dom = u["email"].split("@")[-1]
    notes = []
    if _scoped(u["role"]) and cid in u["clients"] and acc["client_domains"].get(cid) != dom:
        notes.append(f"cross-client assignment: this user belongs to another {acc.get('org_label', 'organisation')} "
                     f"but is assigned to {name} "
                     "- flagged high in the access review")
    if dom != acc["iap"]["staff_domain"] and not _scoped(u["role"]):
        notes.append("external account with a staff role - flagged in the access review")
    base = {"user": u["email"], "role": u["role"], "client": name, "action": act, "notes": notes,
            **({"assigned_clients": [_clients()[c]["name"] for c in u["clients"] if c in _clients()]}
               if _scoped(u["role"]) else {})}
    if u["status"] != "active":
        return ok(allowed=False, reason="account disabled", **base)
    if act not in acc["roles"][u["role"]]["actions"]:
        return ok(allowed=False, reason=f"the {u['role']} role cannot {act}", **base)
    if _scoped(u["role"]):
        if cid not in u["clients"]:
            return ok(allowed=False, reason=f"{u['role']} access is scoped to assigned clients; {name} is not assigned",
                      **base)
        if u.get("assignment_expires", "9999") < TODAY.isoformat():
            return ok(allowed=False, reason=f"assignment expired {u['assignment_expires']}", **base)
    return ok(allowed=True, reason=f"{u['role']} role" + (" with client assignment" if _scoped(u["role"]) else
                                                            " (all clients)"), **base)


@hive_tool("platform")
def forge_redact_secrets(text: str) -> dict:
    """Detect and redact secrets in a job prompt, build log or spec before it is stored or shared.

    Args:
        text: The text to scan, or a sample doc key such as 'forge_job_prompt_leaky'.

    Returns:
        The redacted text ([REDACTED:<type>] markers), findings (type, line, masked preview - never the value),
        counts by type and the rotation advice for each exposed key type.
    """
    src, origin = _text(text)
    if not src.strip():
        return err("no text to scan")
    redacted, findings = _redact(src)
    counts: dict = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return ok(source=origin, clean=not findings, findings=findings[:40], counts=counts, total=len(findings),
              redacted_text=redacted[:6000], truncated=len(redacted) > 6000,
              rotate=sorted({_ROTATE[t] for t in counts if t in _ROTATE}),
              detectors=[n for n, _, _ in _DETECTORS])

"""Platform Core tools: knowledge curation, Pantheon specialists, Workspace productivity, briefing, CodeMender."""
from __future__ import annotations

import datetime as dt
import hashlib
import re

from ._base import err, fixture, hive_tool, offline, ok

# --- Context Librarian -------------------------------------------------------------------------------------------


@hive_tool("platform")
def list_knowledge_sources(topic: str = "") -> dict:
    """List curated knowledge sources with owner, last review date and status, optionally filtered by topic.

    Args:
        topic: Optional keyword (e.g. 'migration', 'security', 'agents').

    Returns:
        Knowledge sources with owner, last_reviewed, status (current / stale / ownerless) and topics.
    """
    rows = fixture("platform_knowledge_sources")["sources"]
    if topic:
        rows = [r for r in rows if topic.lower() in (r["title"] + " " + " ".join(r["topics"])).lower()]
    return ok(sources=rows, count=len(rows))


@hive_tool("platform")
def check_document_freshness(title: str) -> dict:
    """Check whether a knowledge document is current: last review, owner, and superseding documents.

    Args:
        title: Document title or a distinctive part of it.

    Returns:
        Freshness verdict (current / stale / superseded), days since review, owner and replacement if any.
    """
    rows = fixture("platform_knowledge_sources")["sources"]
    hit = next((r for r in rows if title.lower() in r["title"].lower()), None)
    if not hit:
        return err(f"no knowledge source matching {title!r}")
    days = (dt.date.fromisoformat("2026-11-06") - dt.date.fromisoformat(hit["last_reviewed"])).days
    verdict = "superseded" if hit.get("superseded_by") else "stale" if days > 365 or not hit["owner"] else "current"
    return ok(title=hit["title"], verdict=verdict, days_since_review=days, owner=hit["owner"] or None,
              superseded_by=hit.get("superseded_by"))


# --- Hermes -------------------------------------------------------------------------------------------------------


@hive_tool("platform", kind="action")
def compile_engagement_report(client: str, executive_summary: str, sections: list[dict]) -> dict:
    """Compile the engagement deliverable (client-ready report) from the final synthesised sections.

    Args:
        client: Client or opportunity name.
        executive_summary: The executive summary text.
        sections: List of {"title": str, "content": str} in the order they should appear.

    Returns:
        Report id, page estimate and table of contents (rendering to PDF is simulated in the demo).
    """
    if not sections:
        return err("sections must not be empty")
    words = len(executive_summary.split()) + sum(len(str(s.get("content", "")).split()) for s in sections)
    rid = "RPT-" + hashlib.sha1(f"{client}{executive_summary[:50]}".encode()).hexdigest()[:8].upper()
    return ok(report_id=rid, client=client, pages_estimate=max(2, round(words / 350) + 2),
              table_of_contents=["Executive summary", *[s.get("title", "Section") for s in sections]],
              format="PDF (simulated)", simulated=True)


# --- Xenophon ----------------------------------------------------------------------------------------------------


@hive_tool("platform")
def estimate_story_points(stories: list[str]) -> dict:
    """Estimate story points for user stories from Wursta's historical reference stories (reference-class sizing).

    Args:
        stories: User story sentences.

    Returns:
        Points per story (Fibonacci), the reference story each was matched to, and the sprint capacity assumption.
    """
    refs = fixture("platform_story_reference")["reference_stories"]
    out = []
    for s in stories:
        words = set(re.findall(r"[a-z]+", s.lower()))
        best = max(refs, key=lambda r: len(words & set(r["keywords"])))
        complexity = 1 + sum(1 for k in (r"integrat", r"migrat", r"offline", r"secur", r"sync", r"report", r"\bai\b",
                                         r"\bml\b") if re.search(k, s.lower()))
        pts = min(13, max(best["points"], [1, 2, 3, 5, 8, 13][min(complexity, 5)]))
        out.append({"story": s[:160], "points": pts, "matched_reference": best["story"]})
    return ok(estimates=out, total_points=sum(e["points"] for e in out),
              team_velocity_points_per_sprint=fixture("platform_story_reference")["velocity"])


@hive_tool("platform", kind="action")
def create_jira_issues(project_key: str, issues: list[dict]) -> dict:
    """Create Jira issues (epics/stories) using Wursta's taxonomy. Simulated — no real Jira call is made.

    Args:
        project_key: Jira project key, e.g. 'WRS'.
        issues: List of {"type": "Epic"|"Story", "summary": str, "epic": str, "points": int, "priority": str}.

    Returns:
        Created issue keys and the labels applied.
    """
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", project_key or ""):
        return err("project_key must be 2-10 uppercase letters/digits")
    created = []
    for i, it in enumerate(issues, start=101):
        created.append({"key": f"{project_key}-{i}", "type": it.get("type", "Story"), "summary": it.get("summary", ""),
                        "labels": ["wursta", "pantheon", it.get("priority", "should").lower()]})
    return ok(project=project_key, created=created, simulated=True)


# --- Daedalus ----------------------------------------------------------------------------------------------------


@hive_tool("platform")
def estimate_gcp_monthly_cost(components: list[dict]) -> dict:
    """Estimate monthly Google Cloud run cost from illustrative list-price approximations.

    Args:
        components: List of {"service": str, "quantity": number, "unit": str}. Supported services and units are in
            the returned 'price_sheet' (e.g. cloud_run vCPU-hours, bigquery_storage GB, bigquery_query TB).

    Returns:
        Line items, monthly total in USD and the illustrative price sheet used. Validate with the Google Cloud
        Pricing Calculator before quoting.
    """
    sheet = fixture("platform_gcp_prices")["prices"]
    lines, unknown = [], []
    for c in components:
        key = str(c.get("service", "")).lower().replace(" ", "_")
        p = sheet.get(key)
        if not p:
            unknown.append(c.get("service"))
            continue
        qty = float(c.get("quantity", 0))
        lines.append({"service": key, "quantity": qty, "unit": p["unit"], "unit_price_usd": p["usd"],
                      "monthly_usd": round(qty * p["usd"], 2)})
    total = round(sum(l["monthly_usd"] for l in lines), 2)
    return ok(line_items=lines, monthly_total_usd=total, unknown_services=unknown,
              price_sheet={k: v["unit"] for k, v in sheet.items()},
              disclaimer="Illustrative list-price approximations for demos; validate with the official calculator.")


@hive_tool("platform")
def render_architecture_diagram(title: str, components: list[dict], flows: list[dict]) -> dict:
    """Render an editable architecture diagram as Mermaid code (diagram-as-code).

    Args:
        title: Diagram title.
        components: List of {"id": str, "label": str, "layer": str} (layer e.g. edge, compute, data, ai, security).
        flows: List of {"from": id, "to": id, "label": str}.

    Returns:
        Mermaid flowchart code grouped by layer.
    """
    ids = {c["id"] for c in components}
    bad = [f for f in flows if f.get("from") not in ids or f.get("to") not in ids]
    if bad:
        return err("flows reference unknown component ids", bad_flows=bad)
    lines = ["flowchart LR", f"  %% {title}"]
    layers: dict[str, list] = {}
    for c in components:
        layers.setdefault(c.get("layer", "other"), []).append(c)
    for layer, cs in layers.items():
        lines.append(f"  subgraph {re.sub(r'[^A-Za-z0-9]', '_', layer)}[{layer.title()}]")
        lines += [f"    {c['id']}[\"{c['label']}\"]" for c in cs]
        lines.append("  end")
    lines += [f"  {f['from']} -->|{f.get('label', '')}| {f['to']}" if f.get("label") else f"  {f['from']} --> {f['to']}"
              for f in flows]
    return ok(mermaid="\n".join(lines), components=len(components), flows=len(flows))


# --- Ariadne -----------------------------------------------------------------------------------------------------


@hive_tool("platform")
def profile_source_systems(domain: str) -> dict:
    """Profile the source systems for a data domain: tables, row counts, keys and data-quality issues.

    Args:
        domain: Domain key — one of 'claims', 'retail', 'service_requests', 'crm'.

    Returns:
        Source tables with columns, volumes, candidate keys and detected quality issues.
    """
    data = fixture("platform_source_profiles")
    prof = data.get(domain.lower())
    if not prof:
        return err(f"unknown domain {domain!r}", available=sorted(data))
    return ok(domain=domain, **prof)


@hive_tool("platform")
def render_erd(entities: list[dict], relationships: list[dict]) -> dict:
    """Render an entity-relationship diagram as Mermaid erDiagram code.

    Args:
        entities: List of {"name": str, "attributes": [{"name": str, "type": str, "key": "PK"|"FK"|""}]}.
        relationships: List of {"from": str, "to": str, "cardinality": "one-to-many"|"one-to-one"|"many-to-many", "label": str}.

    Returns:
        Mermaid erDiagram code.
    """
    card = {"one-to-many": "||--o{", "one-to-one": "||--||", "many-to-many": "}o--o{"}
    lines = ["erDiagram"]
    for e in entities:
        lines.append(f"  {e['name']} {{")
        for a in e.get("attributes", []):
            key = f" {a['key']}" if a.get("key") else ""
            lines.append(f"    {a.get('type', 'string')} {a['name']}{key}")
        lines.append("  }")
    for r in relationships:
        lines.append(f"  {r['from']} {card.get(r.get('cardinality'), '||--o{')} {r['to']} : \"{r.get('label', 'has')}\"")
    return ok(mermaid="\n".join(lines), entities=len(entities))


@hive_tool("platform")
def validate_ddl(ddl: str) -> dict:
    """Validate BigQuery DDL: statement order vs foreign-key-like references, partitioning, descriptions, naming.

    Args:
        ddl: One or more CREATE TABLE statements separated by semicolons.

    Returns:
        Issues found (severity, message) and the detected table creation order.
    """
    stmts = [s.strip() for s in ddl.split(";") if s.strip()]
    order, issues = [], []
    for s in stmts:
        m = re.search(r"CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([\w.\-]+)`?", s, re.I)
        if not m:
            issues.append({"severity": "error", "message": f"not a CREATE TABLE statement: {s[:60]}..."})
            continue
        name = m.group(1).split(".")[-1]
        order.append(name)
        if name.startswith("fact") or name.startswith("fct"):
            if "PARTITION BY" not in s.upper():
                issues.append({"severity": "warning", "message": f"{name}: fact table without PARTITION BY"})
            if "CLUSTER BY" not in s.upper():
                issues.append({"severity": "info", "message": f"{name}: consider CLUSTER BY on common filters"})
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            issues.append({"severity": "warning", "message": f"{name}: use lower_snake_case table names"})
        for ref in re.findall(r"REFERENCES\s+`?([\w.\-]+)`?", s, re.I):
            if ref.split(".")[-1] not in order[:-1]:
                issues.append({"severity": "error", "message": f"{name} references {ref} before it is created"})
        if "description" not in s.lower():
            issues.append({"severity": "info", "message": f"{name}: add OPTIONS(description=...) for the catalog"})
    return ok(valid=not any(i["severity"] == "error" for i in issues), creation_order=order, issues=issues)


# --- Prometheus / Proteus ----------------------------------------------------------------------------------------


@hive_tool("platform")
def score_risk_register(risks: list[dict]) -> dict:
    """Score a risk register (likelihood x impact on 1-5 scales), rank it and flag risks without owners.

    Args:
        risks: List of {"risk": str, "likelihood": 1-5, "impact": 1-5, "owner": str, "mitigation": str}.

    Returns:
        Ranked risks with score, rating (low/medium/high/critical) and register health checks.
    """
    out = []
    for r in risks:
        try:
            score = int(r.get("likelihood", 0)) * int(r.get("impact", 0))
        except (TypeError, ValueError):
            return err(f"likelihood/impact must be integers: {r}")
        rating = "critical" if score >= 20 else "high" if score >= 12 else "medium" if score >= 6 else "low"
        out.append({**r, "score": score, "rating": rating})
    out.sort(key=lambda r: -r["score"])
    return ok(register=out, no_owner=[r["risk"] for r in out if not r.get("owner")],
              no_mitigation=[r["risk"] for r in out if not r.get("mitigation")],
              heat={k: sum(1 for r in out if r["rating"] == k) for k in ("critical", "high", "medium", "low")})


@hive_tool("platform")
def competitive_battlecard(category: str) -> dict:
    """Return the competitive battlecard for a solution category (synthetic field intelligence).

    Args:
        category: One of 'enterprise_ai_assistant', 'data_platform', 'workspace_collaboration', 'contact_center_ai'.

    Returns:
        Positioning, strengths, landmines to set, objection handling and proof points.
    """
    cards = fixture("platform_battlecards")
    card = cards.get(category)
    if not card:
        return err(f"unknown category {category!r}", available=sorted(cards))
    return ok(category=category, **card, note="Synthetic field intelligence for demo purposes.")


# --- Workspace Pro -----------------------------------------------------------------------------------------------


@hive_tool("platform")
def workspace_inbox(only_unread: bool = True, limit: int = 15) -> dict:
    """Read the (synthetic) Gmail inbox.

    Args:
        only_unread: Return unread messages only.
        limit: Maximum number of messages.

    Returns:
        Messages with id, from, subject, received time, snippet, labels and whether a reply is expected.
    """
    msgs = fixture("platform_workspace")["inbox"]
    if only_unread:
        msgs = [m for m in msgs if m.get("unread")]
    return ok(messages=msgs[: max(1, min(limit, 50))], total=len(msgs))


@hive_tool("platform")
def workspace_find_free_slots(attendees: list[str], duration_minutes: int = 30, days_ahead: int = 5) -> dict:
    """Find meeting slots when all attendees are free (working hours 09:00-17:00, synthetic calendars).

    Args:
        attendees: Attendee first names or emails (e.g. ['Ana', 'Diego']). The user is always included.
        duration_minutes: Meeting length.
        days_ahead: How many business days to search.

    Returns:
        Up to 5 candidate slots (ISO start/end) and attendees that were not found.
    """
    ws = fixture("platform_workspace")
    people = ws["people"]
    found, missing = ["me"], []
    for a in attendees:
        wanted = a.strip().lower()
        key = next((p for p in people if wanted in (p, people[p]["email"].lower())
                    or wanted.split()[0] == p or wanted.split("@")[0].split(".")[0] == p), None) if wanted else None
        if key and key not in found:
            found.append(key)
        elif not key:
            missing.append(a)
    busy = [b for p in found for b in people[p]["busy"]]
    start_day = dt.date.fromisoformat(ws["today"])
    slots, day, checked = [], start_day, 0
    while len(slots) < 5 and checked < days_ahead:
        if day.weekday() < 5:
            checked += 1
            t = dt.datetime.combine(day, dt.time(9))
            end_of_day = dt.datetime.combine(day, dt.time(17))
            while t + dt.timedelta(minutes=duration_minutes) <= end_of_day and len(slots) < 5:
                s, e = t, t + dt.timedelta(minutes=duration_minutes)
                clash = any(dt.datetime.fromisoformat(b[0]) < e and dt.datetime.fromisoformat(b[1]) > s for b in busy)
                if not clash:
                    slots.append({"start": s.isoformat(timespec="minutes"), "end": e.isoformat(timespec="minutes")})
                    t = e + dt.timedelta(minutes=60)
                else:
                    t += dt.timedelta(minutes=30)
        day += dt.timedelta(days=1)
    return ok(slots=slots, attendees=[people[p]["email"] for p in found], not_found=missing,
              timezone=ws["timezone"])


@hive_tool("platform", kind="action")
def workspace_draft_email(to: list[str], subject: str, body: str, reply_to_id: str = "") -> dict:
    """Save an email draft in Gmail (simulated — never sent).

    Args:
        to: Recipient emails.
        subject: Subject line.
        body: Plain-text body.
        reply_to_id: Inbox message id when replying.

    Returns:
        Draft id and a preview.
    """
    if not to or not subject or not body:
        return err("to, subject and body are required")
    did = "draft-" + hashlib.sha1((subject + body).encode()).hexdigest()[:6]
    return ok(draft_id=did, to=to, subject=subject, preview=body[:200], reply_to_id=reply_to_id or None,
              simulated=True)


@hive_tool("platform", kind="action")
def workspace_create_event(title: str, start: str, end: str, attendees: list[str], agenda: str = "") -> dict:
    """Create a Google Calendar event with a Meet link (simulated).

    Args:
        title: Event title.
        start: ISO start datetime.
        end: ISO end datetime.
        attendees: Attendee emails.
        agenda: Optional agenda text for the description.

    Returns:
        Event id, Meet link placeholder and invitation summary.
    """
    try:
        s, e = dt.datetime.fromisoformat(start), dt.datetime.fromisoformat(end)
    except ValueError:
        return err("start and end must be ISO datetimes")
    if e <= s:
        return err("end must be after start")
    eid = "evt-" + hashlib.sha1((title + start).encode()).hexdigest()[:6]
    return ok(event_id=eid, title=title, start=start, end=end, attendees=attendees,
              meet_link="https://meet.google.com/xxx-demo-xxx", agenda=agenda, simulated=True)


@hive_tool("platform")
def workspace_search_drive(query: str) -> dict:
    """Search the (synthetic) Google Drive by keyword.

    Args:
        query: Keywords, e.g. 'SOW draft northwind'.

    Returns:
        Matching files with id, name, owner, last modified and a content excerpt.
    """
    files = fixture("platform_workspace")["drive"]
    terms = [t for t in query.lower().split() if len(t) > 2]
    scored = []
    for f in files:
        hay = (f["name"] + " " + f["excerpt"]).lower()
        score = sum(1 for t in terms if t in hay)
        if score:
            scored.append((score, f["modified"], f))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)   # best match first, then most recently modified
    return ok(files=[f for _, _, f in scored[:8]], query=query)


# --- Brief Me ----------------------------------------------------------------------------------------------------


@hive_tool("platform")
def brief_calendar_today() -> dict:
    """Return today's meetings with attendees, account and the last interaction notes (synthetic calendar + CRM)."""
    b = fixture("platform_brief")
    return ok(date=b["date"], meetings=b["meetings"])


@hive_tool("platform")
def brief_priority_emails() -> dict:
    """Return emails that need a decision or reply today, ranked by urgency (synthetic mailbox)."""
    return ok(emails=fixture("platform_brief")["emails"])


@hive_tool("platform")
def brief_account_signals() -> dict:
    """Return account signals from the CRM: pipeline changes, renewals, support escalations, usage trends."""
    return ok(signals=fixture("platform_brief")["signals"])


# --- CodeMender ----------------------------------------------------------------------------------------------------


@hive_tool("platform")
def run_python_in_sandbox(code: str) -> dict:
    """Run Python code (e.g. a module plus its unit tests) in Gemini's Google-hosted code-execution sandbox.

    Args:
        code: Complete, self-contained Python source to execute (include the tests and a call that runs them).

    Returns:
        The executed code outcome (OK / FAILED) and captured stdout/stderr.
    """
    if offline():
        return ok(outcome="SKIPPED", output="offline mode")
    from google.genai import types

    from ._base import _genai_client
    from ..models import tier

    if len(code) > 20000:
        return err("code too long for the sandbox demo (20k chars max)")
    try:
        resp = _genai_client().models.generate_content(
            model=tier("flash").model_id,
            contents="Execute the following Python code exactly as written, once, using the code execution tool. "
                     "Do not modify it. Then reply with nothing else.\n\n```python\n" + code + "\n```",
            config=types.GenerateContentConfig(tools=[types.Tool(code_execution=types.ToolCodeExecution())],
                                               temperature=0),
        )
    except Exception as e:  # noqa: BLE001
        return err(f"sandbox call failed: {type(e).__name__}: {e}"[:300])
    results = []
    for part in (resp.candidates[0].content.parts if resp.candidates and resp.candidates[0].content else []):
        if part.code_execution_result:
            results.append({"outcome": str(part.code_execution_result.outcome).split(".")[-1],
                            "output": (part.code_execution_result.output or "")[:4000]})
    if not results:
        return err("sandbox did not execute the code", model_text=(resp.text or "")[:500])
    last = results[-1]
    return ok(outcome=last["outcome"], output=last["output"], runs=len(results), sandbox="Gemini code execution")


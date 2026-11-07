"""Wursta Delivery Engine (WurstaBots) — client delivery, sales & marketing and innovation-pipeline tools.

Deterministic, stdlib-only functions over synthetic fixtures (fixtures/ops_*.json and fixtures/docs/ops_*.md).
Every organisation and person is fictional. Tools with side effects are simulated and return simulated=True.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import unicodedata

from ._base import doc_text, err, fixture, hive_tool, ok

MODULE = "delivery"
TODAY = dt.date(2026, 11, 6)          # demo "today" — keeps every tool deterministic
STOP = {"the", "and", "for", "with", "from", "into", "that", "this", "our", "your", "their", "will", "shall", "must",
        "all", "any", "are", "was", "has", "have", "per", "out", "of", "to", "a", "an", "in", "on", "by", "at", "or",
        "be", "is", "it", "we", "i", "us", "up", "as", "next", "send", "run", "make", "get", "do", "new"}


# --- helpers -----------------------------------------------------------------------------------------------------

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().replace("’", "'").strip()


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", _norm(s)) if len(w) > 2 and w not in STOP}


def _sid(prefix: str, *parts: object, n: int = 6) -> str:
    return f"{prefix}-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:n].upper()


def _kw_hit(kw: str, text: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(_norm(kw)) + r"(?:s|es|ed|ing|d)?(?![\w])", text) is not None


def _business_days(start: dt.date, n: int) -> dt.date:
    d = start
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _account(ref: str) -> dict | None:
    key = _norm(ref)
    for a in fixture("ops_accounts")["accounts"]:
        if key in (_norm(a["id"]), _norm(a["name"])) or (len(key) > 3 and key in _norm(a["name"])):
            return a
    return None


def _meeting(ref: str) -> dict | None:
    key = _norm(ref)
    for m in fixture("ops_meetings")["meetings"]:
        if key in (_norm(m["id"]), _norm(m.get("transcript_doc") or "-")):
            return m
    return None


# --- client delivery: meetings (Janus, Helios, Athena, Oracle) ----------------------------------------------------


@hive_tool(MODULE)
def ops_meeting_registry(account: str = "", meeting_id: str = "") -> dict:
    """Look up recorded client meetings: transcript document key, recording URI, attendance and sentiment history.

    Args:
        account: Account name or id (e.g. 'Tallbridge Logistics' or 'ACC-1042'); empty lists every account.
        meeting_id: A meeting id (e.g. 'MTG-2026-1104-TBL') or a transcript document key
            (e.g. 'ops_transcript_tallbridge_steerco'); takes precedence over account.

    Returns:
        Meetings (newest first) with transcript_doc, recording_uri, absentees, whether the executive sponsor attended,
        sentiment score and KB-indexing status, plus the account's chronological sentiment trend.
    """
    rows = fixture("ops_meetings")["meetings"]
    if meeting_id:
        m = _meeting(meeting_id)
        if not m:
            return err(f"unknown meeting {meeting_id!r}", available=[r["id"] for r in rows])
        rows = [m]
        account = m["account_id"]
    elif account:
        acc = _account(account)
        if not acc:
            return err(f"unknown account {account!r}",
                       available=sorted({r["account"] for r in rows}))
        rows = [r for r in rows if r["account_id"] == acc["id"]]
    out = []
    for r in sorted(rows, key=lambda r: r["date"], reverse=True):
        absent = [p for p in r["invited"] if p not in r["attended"]]
        out.append({**{k: v for k, v in r.items() if k not in ("invited", "attended")},
                    "invited_count": len(r["invited"]), "attended_count": len(r["attended"]),
                    "attended": r["attended"], "absent": absent,
                    "exec_sponsor_present": r["exec_sponsor"] in r["attended"],
                    "attendance_rate": round(len(r["attended"]) / max(1, len(r["invited"])), 2)})
    trend = []
    if account:
        acc = _account(account)
        hist = sorted((m for m in fixture("ops_meetings")["meetings"] if acc and m["account_id"] == acc["id"]),
                      key=lambda m: m["date"])
        trend = [{"meeting_id": m["id"], "date": m["date"], "sentiment": m["sentiment_score"],
                  "exec_sponsor_present": m["exec_sponsor"] in m["attended"]} for m in hist]
    return ok(meetings=out, count=len(out), sentiment_trend=trend,
              note="Sentiment scale -1 (very negative) to +1 (very positive).")


@hive_tool(MODULE, kind="action")
def ops_send_pm_alert(meeting_id: str, severity: str, headline: str, body: str,
                      recommended_actions: list[str] | None = None) -> dict:
    """Send a meeting-health alert to the project manager in Google Chat (simulated), escalating red alerts.

    Args:
        meeting_id: Meeting id or transcript document key the alert is about.
        severity: 'amber' or 'red' (per the Client Health & Escalation Playbook); 'green' is logged only.
        headline: One-line alert headline.
        body: Alert text (what happened, evidence quotes, why it matters).
        recommended_actions: Up to 5 recommended actions with owners.

    Returns:
        Alert id, recipients, acknowledgement deadline and the delivered preview.
    """
    m = _meeting(meeting_id)
    if not m:
        return err(f"unknown meeting {meeting_id!r}")
    sev = severity.lower().strip()
    if sev not in ("green", "amber", "red"):
        return err("severity must be green, amber or red")
    if not headline.strip() or len(body.strip()) < 20:
        return err("headline and a body of at least 20 characters are required")
    acc = _account(m["account_id"]) or {}
    recipients = [f"{m['pm']} (PM)"]
    if sev == "red":
        recipients += [f"{acc.get('csm', 'CSM')} (CSM)", f"{acc.get('account_exec', 'AE')} (Account Executive)",
                       "Delivery Director"]
    elif sev == "amber":
        recipients.append(f"{acc.get('csm', 'CSM')} (CSM)")
    ack = {"red": _business_days(TODAY, 0).isoformat() + " (within 4 business hours)",
           "amber": _business_days(TODAY, 1).isoformat() + " (next business day)",
           "green": "no acknowledgement required"}[sev]
    return ok(alert_id=_sid("ALR", m["id"], sev, headline), meeting_id=m["id"], account=m["account"],
              severity=sev, channel="Google Chat direct message" if sev != "green" else "health log only",
              recipients=recipients if sev != "green" else [], acknowledge_by=ack,
              recommended_actions=(recommended_actions or [])[:5], preview=f"[{sev.upper()}] {headline}\n{body[:280]}",
              simulated=True)


@hive_tool(MODULE)
def ops_pm_project_roster(project_key: str) -> dict:
    """Read a project in the PM system: team members (Wursta and client), open tasks with overdue flags, decision log.

    Args:
        project_key: Project key, e.g. 'TBL' (Tallbridge Logistics), 'CFI' (Calder & Finch) or 'VAC' (Verdant Agro).

    Returns:
        Members with PM usernames and org, open tasks (overdue and client-owned flagged) and recent decisions.
    """
    pm = fixture("ops_pm")
    proj = pm["projects"].get(project_key.upper().strip())
    if not proj:
        return err(f"unknown project {project_key!r}", available=sorted(pm["projects"]))
    orgs = {m["name"]: m["org"] for m in proj["members"]}
    tasks = []
    for t in proj["open_tasks"]:
        overdue = t["status"] != "Done" and t["due"] < TODAY.isoformat()
        tasks.append({**t, "overdue": overdue, "client_owned": orgs.get(t["owner"], "Wursta") != "Wursta",
                      "days_overdue": (TODAY - dt.date.fromisoformat(t["due"])).days if overdue else 0})
    return ok(project=project_key.upper(), name=proj["name"], account=proj["account"], pm=proj["pm"],
              last_meeting=proj["last_meeting"], last_meeting_date=proj["last_meeting_date"],
              members=proj["members"], open_tasks=tasks, overdue_count=sum(t["overdue"] for t in tasks),
              decision_log=proj["decision_log"], today=TODAY.isoformat())


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_WEEKDAYS = {d: i for i, d in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])}


def _parse_due(text: str, ref: dt.date) -> tuple[dt.date | None, str]:
    t = _norm(text)
    if not t or t in ("tbd", "unknown", "n/a", "none"):
        return None, "no due date stated"
    if m := re.search(r"\d{4}-\d{2}-\d{2}", t):
        try:
            return dt.date.fromisoformat(m.group(0)), "explicit date"
        except ValueError:
            pass
    if m := re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})", t):
        d = dt.date(ref.year, _MONTHS[m.group(1)], int(m.group(2)))
        return (d if d >= ref - dt.timedelta(days=30) else d.replace(year=ref.year + 1)), "month and day"
    if m := re.search(r"\b(\d{1,2})(st|nd|rd|th)\b", t):
        day = int(m.group(1))
        d = ref.replace(day=min(day, 28)) if day > 28 else ref.replace(day=day)
        if d < ref:
            nxt = (ref.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
            d = nxt.replace(day=min(day, 28))
        return d, "day of month"
    if "tomorrow" in t:
        return ref + dt.timedelta(days=1), "tomorrow"
    if m := re.search(r"in (\d+) days", t):
        return ref + dt.timedelta(days=int(m.group(1))), "in N days"
    if "end of next week" in t or t.strip() == "next week" or "by next week" in t:
        return ref + dt.timedelta(days=(4 - ref.weekday()) % 7 + 7), "end of next week"
    if "end of week" in t or "this week" in t or "eow" in t:
        return ref + dt.timedelta(days=(4 - ref.weekday()) % 7), "end of this week"
    if "end of month" in t or "eom" in t:
        nxt = (ref.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        return nxt - dt.timedelta(days=1), "end of month"
    for name, idx in _WEEKDAYS.items():
        if name in t or re.search(rf"\b{name[:3]}\b", t):
            delta = (idx - ref.weekday()) % 7 or 7
            if "next " + name in t:
                delta += 7 if delta < 7 else 0
            return ref + dt.timedelta(days=delta), f"next {name.title()} after the meeting"
    return None, f"could not parse {text!r}"


def _member(owner: str, members: list[dict]) -> dict | None:
    o = _norm(owner)
    if not o:
        return None
    for m in members:
        if o == _norm(m["name"]) or o == _norm(m["user"]):
            return m
    first = [m for m in members if _norm(m["name"]).split()[0] == o.split()[0]]
    if len(first) == 1:
        return first[0]
    last = [m for m in members if _norm(m["name"]).split()[-1] == o.split()[-1]]
    return last[0] if len(last) == 1 else None


@hive_tool(MODULE, kind="action")
def ops_create_pm_tasks(project_key: str, tasks: list[dict], decisions: list[str] | None = None,
                        meeting_id: str = "", reference_date: str = "", skip_duplicates: bool = True) -> dict:
    """Create tasks (and log decisions) in the PM system from meeting action items. Simulated — nothing is written.

    Owners are resolved against the project roster (full or first name); relative due dates such as 'Friday',
    'by Monday the 9th', 'November 20th', 'end of next week' are resolved from the meeting date. Likely duplicates of
    open tasks are reported instead of created.

    Args:
        project_key: Project key, e.g. 'TBL'.
        tasks: List of {"task": str, "owner": str, "due": str, "priority": "P1"|"P2"|"P3"} (owner may list several
            people, the first becomes assignee and the rest watchers).
        decisions: Decisions to append to the project decision log.
        meeting_id: Source meeting id or transcript key (used for traceability and the reference date).
        reference_date: Date the relative due dates are counted from (YYYY-MM-DD); default = meeting date.
        skip_duplicates: When true, likely duplicates of open tasks are not created.

    Returns:
        Created task keys with assignee, resolved due date and rule used; duplicates with the existing task key;
        items that need an owner; decision-log ids.
    """
    pm = fixture("ops_pm")
    proj = pm["projects"].get(project_key.upper().strip())
    if not proj:
        return err(f"unknown project {project_key!r}", available=sorted(pm["projects"]))
    if not tasks:
        return err("tasks must not be empty")
    mt = _meeting(meeting_id) if meeting_id else None
    try:
        ref = dt.date.fromisoformat(reference_date) if reference_date else \
            dt.date.fromisoformat(mt["date"] if mt else proj["last_meeting_date"])
    except ValueError:
        return err("reference_date must be YYYY-MM-DD")
    nums = [int(t["key"].split("-")[1]) for t in proj["open_tasks"]]
    next_num = max(nums, default=100) + 1
    created, dupes, needs_owner = [], [], []
    open_tasks = [t for t in proj["open_tasks"] if t["status"] != "Done"]
    for item in tasks:
        title = str(item.get("task") or item.get("title") or "").strip()
        if not title:
            continue
        tw = _words(title)
        dup = None
        for ex in open_tasks:
            ew = _words(ex["title"])
            inter = tw & ew
            if len(inter) >= 2 and len(inter) / max(1, min(len(tw), len(ew))) >= 0.6:
                dup = ex
                break
        owners = [o.strip() for o in re.split(r",| and | & |/", str(item.get("owner", ""))) if o.strip()]
        resolved = [m for m in (_member(o, proj["members"]) for o in owners) if m]
        due, rule = _parse_due(str(item.get("due", "")), ref)
        if dup and skip_duplicates:
            dupes.append({"task": title, "existing_key": dup["key"], "existing_title": dup["title"],
                          "existing_owner": dup["owner"], "existing_due": dup["due"],
                          "suggestion": "update the existing task (owner / due date / status) instead of creating a new one",
                          "proposed_due": due.isoformat() if due else None})
            continue
        assignee = resolved[0] if resolved else next(m for m in proj["members"] if m["name"] == proj["pm"])
        key = f"{project_key.upper()}-{next_num}"
        next_num += 1
        rec = {"key": key, "title": title, "assignee": assignee["name"], "assignee_user": assignee["user"],
               "assignee_org": assignee["org"], "watchers": [m["name"] for m in resolved[1:]],
               "due": due.isoformat() if due else None, "due_rule": rule,
               "priority": item.get("priority", "P2"),
               "labels": ["meeting-action", (mt or {}).get("id", "manual")]
               + (["client-owned"] if assignee["org"] != "Wursta" else [])
               + ([] if resolved else ["needs-owner"]) + ([] if due else ["needs-due-date"])}
        if assignee["org"] != "Wursta":
            rec["watchers"].append(proj["pm"])
        if not resolved:
            needs_owner.append({"key": key, "task": title, "stated_owner": item.get("owner") or "none",
                                "parked_with": proj["pm"]})
        created.append(rec)
    dec_nums = [int(d["id"].rsplit("-", 1)[1]) for d in proj["decision_log"]]
    logged = [{"id": f"DEC-{project_key.upper()}-{max(dec_nums, default=0) + i:03d}", "date": ref.isoformat(),
               "decision": d} for i, d in enumerate(decisions or [], start=1)]
    return ok(project=project_key.upper(), reference_date=ref.isoformat(), created=created,
              duplicates_not_created=dupes, needs_owner=needs_owner, decisions_logged=logged,
              summary={"created": len(created), "duplicates": len(dupes), "needs_owner": len(needs_owner),
                       "decisions": len(logged)}, simulated=True)


@hive_tool(MODULE, kind="action")
def ops_index_knowledge_asset(meeting_id: str, title: str, summary: str, tags: list[str],
                              chapters: list[dict] | None = None, qa_pairs: list[dict] | None = None,
                              access: str = "project_team") -> dict:
    """Index a meeting's Open Knowledge Framework (OKF) record into the delivery knowledge base (simulated).

    Args:
        meeting_id: Meeting id or transcript document key the record was built from.
        title: Record title.
        summary: 3-6 sentence summary.
        tags: Search tags (account, topics, products).
        chapters: List of {"start": "mm:ss", "title": str} chapter markers.
        qa_pairs: List of {"question": str, "answer": str} reusable Q&A pairs.
        access: Who can find it: 'project_team', 'account_team' or 'company' (company-wide only for content with
            no client-confidential details).

    Returns:
        Asset id, data-store target, access list, chunk estimate and deep links to chapters.
    """
    m = _meeting(meeting_id)
    if not m:
        return err(f"unknown meeting {meeting_id!r}")
    if access not in ("project_team", "account_team", "company"):
        return err("access must be project_team, account_team or company")
    if len(summary.split()) < 15 or not tags:
        return err("summary (15+ words) and at least one tag are required")
    pm = fixture("ops_pm")["projects"].get(m["project_key"], {})
    acl = {"project_team": [p["name"] for p in pm.get("members", []) if p["org"] == "Wursta"] or [m["pm"]],
           "account_team": ["Account team (PM, CSM, AE, engagement lead)"],
           "company": ["All Wursta employees"]}[access]
    warnings = []
    if access == "company" and m["type"] in ("steering_committee", "monthly_review"):
        warnings.append("Steering/commercial meetings usually contain client-confidential details — prefer account_team.")
    chapters = chapters or []
    words = len(summary.split()) + sum(len(str(c.get("title", "")).split()) for c in chapters) + \
        sum(len(str(q.get("question", "")).split()) + len(str(q.get("answer", "")).split()) for q in (qa_pairs or []))
    return ok(asset_id=_sid("OKF", m["id"], title), meeting_id=m["id"], account=m["account"], title=title,
              data_store="Delivery knowledge base (Vertex AI Search) — meeting records", access=access, acl=acl,
              tags=sorted({t.lower() for t in tags} | {m["account"].lower(), m["type"]}),
              chunks_estimate=max(1, round(words / 120) + len(chapters)),
              chapter_links=[{"start": c.get("start"), "title": c.get("title"),
                              "link": f"{m['recording_uri']}#t={c.get('start')}"} for c in chapters],
              qa_pairs=len(qa_pairs or []), warnings=warnings, simulated=True)


# --- client delivery: presentations (Scribe) ----------------------------------------------------------------------

_INTERNAL_TERMS = ["margin", "rate card", "internal only", "internal note", "do not share", "strictly confidential",
                   "company confidential", "discount", "cost to serve", "exclusivity"]
_CLAIM_TERMS = ["guarantee", "guaranteed", "100%", "best-in-class", "world-class", "#1", "risk-free", "never fails"]


@hive_tool(MODULE)
def ops_content_library(kind: str = "", query: str = "", external_only: bool = False) -> dict:
    """Search the content & evidence library: case studies, blogs, Hive agent capabilities, past SOWs, capabilities.

    Args:
        kind: Optional filter — 'case_study', 'blog', 'agent', 'past_sow' or 'capability'.
        query: Free-text or id (e.g. 'CS-021', 'logistics', 'claims', 'transit').
        external_only: Return only items approved for client-facing / public use.

    Returns:
        Matching items (best first) with approval flags ('named_reference', 'approved_external') and key outcomes.
    """
    lib = fixture("ops_content")
    sources = {"case_study": "case_studies", "blog": "blogs", "agent": "agent_capabilities", "past_sow": "past_sows",
               "capability": "capabilities"}
    if kind and kind not in sources:
        return err(f"unknown kind {kind!r}", available=sorted(sources))
    q = _words(query)
    out = []
    for k, src in sources.items():
        if kind and k != kind:
            continue
        for it in lib[src]:
            if external_only and not it.get("approved_external", k in ("past_sow", "capability")):
                continue
            blob = _norm(json.dumps(it, ensure_ascii=False))
            if query and _norm(query) == _norm(it["id"]):
                score = 100
            else:
                score = sum(1 for w in q if w in blob)
            if query and score == 0:
                continue
            out.append({"kind": k, "score": score, **it})
    out.sort(key=lambda x: -x["score"])
    for o in out:
        o.pop("score")
    return ok(items=out[:10], count=len(out),
              rule="Name a client only if named_reference is true AND approved_external is true; otherwise use the "
                   "anonymised descriptor.")


@hive_tool(MODULE)
def ops_brand_deck_check(slides: list[dict], audience: str = "client") -> dict:
    """Check a slide-by-slide deck outline against Wursta's presentation & brand standards.

    Args:
        slides: List of {"title": str, "bullets": [str], "notes": str, "source": str} in slide order
            (notes = speaker notes; source = footnote for figures).
        audience: 'client' (6-15 slides) or 'executive' (max 10 slides).

    Returns:
        Errors, warnings and info per slide, a 0-100 brand score and pass/fail (pass = no errors and score >= 80).
    """
    if not slides:
        return err("slides must not be empty")
    issues: list[dict] = []

    def add(level: str, slide: int | None, msg: str) -> None:
        issues.append({"level": level, "slide": slide, "issue": msg})

    n = len(slides)
    lo, hi = (3, 10) if audience == "executive" else (6, 15)
    if not lo <= n <= hi:
        add("warning", None, f"{n} slides — {audience} decks should have {lo}-{hi}")
    titles = [_norm(s.get("title", "")) for s in slides]
    if len(slides[0].get("bullets") or []) > 1:
        add("warning", 1, "slide 1 should be the title slide (title, subtitle, date — no bullet list)")
    if not any(re.search(r"agenda|today|what we will cover", t) for t in titles[:3]):
        add("warning", None, "add an agenda slide within the first 3 slides")
    if not re.search(r"next step|call to action|let's|how we start|proposed plan", titles[-1]):
        add("warning", n, "last slide should be 'Next steps' with a clear call to action")
    lib = fixture("ops_content")["case_studies"]
    restricted = [c["client"] for c in lib if not (c["named_reference"] and c["approved_external"])
                  and not c["client"].startswith("a ")]
    for i, s in enumerate(slides, start=1):
        title = str(s.get("title", ""))
        bullets = [str(b) for b in (s.get("bullets") or [])]
        notes = str(s.get("notes", ""))
        blob = _norm(" ".join([title, *bullets, notes]))
        if not title.strip():
            add("error", i, "missing slide title")
        elif len(title.split()) > 10:
            add("warning", i, f"title has {len(title.split())} words (max 10)")
        if len(bullets) > 5:
            add("error", i, f"{len(bullets)} bullets (max 5) — split the slide")
        for b in bullets:
            if len(b.split()) > 14:
                add("warning", i, f"bullet over 14 words: '{b[:60]}...'")
        if i > 1 and not notes.strip():
            add("error", i, "missing speaker notes")
        elif i > 1 and len(notes.split()) < 15:
            add("warning", i, "speaker notes under 15 words — say what the presenter should add beyond the slide")
        for term in _INTERNAL_TERMS:
            if term in blob:
                add("error", i, f"internal-only content ('{term}') must not appear in a client deck")
        for term in _CLAIM_TERMS:
            if term in blob:
                add("warning", i, f"unsupported claim language ('{term}')")
        for client in restricted:
            if _norm(client) in blob:
                add("error", i, f"'{client}' is not approved as a named reference — anonymise it")
        if re.search(r"\d+(\.\d+)?\s?%|\d+x\b|−\d+|-\d+%", " ".join(bullets)) and not str(s.get("source", "")).strip():
            add("info", i, "figures without a source footnote — add the case study id or report")
    e = sum(1 for x in issues if x["level"] == "error")
    w = sum(1 for x in issues if x["level"] == "warning")
    info = sum(1 for x in issues if x["level"] == "info")
    score = max(0, 100 - 15 * e - 5 * w - 1 * info)
    return ok(slides=n, audience=audience, brand_score=score, passed=e == 0 and score >= 80,
              counts={"error": e, "warning": w, "info": info}, issues=issues,
              standards="Presentation & Brand Standards (knowledge base)")


@hive_tool(MODULE, kind="action")
def ops_create_slides_deck(title: str, slides: list[dict], template: str = "wursta_client_2026",
                           share_with: list[str] | None = None) -> dict:
    """Create the Google Slides deck from an approved outline (simulated). Refuses decks with brand-check errors.

    Args:
        title: Deck title.
        slides: Slide outline, same shape as for ops_brand_deck_check.
        template: Slides template: 'wursta_client_2026', 'wursta_executive_2026' or 'wursta_workshop_2026'.
        share_with: Optional editor emails (internal only).

    Returns:
        Deck id, simulated link, slide count, template and the brand score.
    """
    if template not in ("wursta_client_2026", "wursta_executive_2026", "wursta_workshop_2026"):
        return err("unknown template", available=["wursta_client_2026", "wursta_executive_2026", "wursta_workshop_2026"])
    check = ops_brand_deck_check(slides, "executive" if "executive" in template else "client")
    if check["status"] != "ok":
        return check
    if check["counts"]["error"]:
        return err("deck has brand-check errors — fix them before creating the file",
                   issues=[i for i in check["issues"] if i["level"] == "error"])
    external = [e for e in (share_with or []) if not e.lower().endswith("@wursta.example")]
    if external:
        return err("drafts can only be shared internally; share with the client after review", external=external)
    deck_id = _sid("DECK", title, len(slides))
    return ok(deck_id=deck_id, title=title, link=f"slides://simulated/{deck_id}", template=template,
              slide_count=len(slides), brand_score=check["brand_score"], shared_with=share_with or [],
              speaker_notes_included=sum(1 for s in slides if s.get("notes")), simulated=True)


# --- client delivery: partner content (Cataloger) -----------------------------------------------------------------


@hive_tool(MODULE)
def ops_partner_content_inbox(batch: str = "partner_portal_week45", audience: str = "") -> dict:
    """List a batch of new partner-portal content with abstracts, key takeaways, audiences and motion.

    Args:
        batch: Batch key, e.g. 'partner_portal_week45' or 'partner_portal_week44'.
        audience: Optional audience filter (e.g. 'sales', 'presales', 'delivery', 'marketing', 'leadership').

    Returns:
        Items with id, title, audiences, motion (sell/build/service), abstract and 2-3 key takeaways. Use the
        partner_advantage_cataloger skill on the same batch for AI-readiness grading.
    """
    data = fixture("ops_partner_inbox")["batches"]
    b = data.get(batch)
    if not b:
        return err(f"unknown batch {batch!r}", available=sorted(data))
    items = b["items"]
    if audience:
        items = [i for i in items if any(_norm(audience) in _norm(a) for a in i["audiences"])]
    return ok(batch=batch, received=b["received"], items=items, count=len(items),
              audiences=sorted({a for i in b["items"] for a in i["audiences"]}))


_SPACES = {"sales": "#sales-intel", "presales": "#presales-guild", "delivery": "#delivery-guild",
           "marketing": "#marketing", "leadership": "#leadership", "partner": "#partner-updates",
           "customer-success": "#customer-success"}


@hive_tool(MODULE, kind="action")
def ops_publish_digest(channel: str, title: str, body: str) -> dict:
    """Post a digest (partner content, competitive intel, weekly summary) to a team's Google Chat space (simulated).

    Args:
        channel: Team space — 'sales', 'presales', 'delivery', 'marketing', 'leadership', 'partner' or
            'customer-success'.
        title: Digest title.
        body: Markdown body (max 4,000 characters).

    Returns:
        Message id, space, character count and preview.
    """
    space = _SPACES.get(channel.lower().strip().lstrip("#"))
    if not space:
        return err(f"unknown channel {channel!r}", available=sorted(_SPACES))
    if not title.strip() or not body.strip():
        return err("title and body are required")
    if len(body) > 4000:
        return err(f"body is {len(body)} characters; Chat messages are limited to 4,000 — shorten or link a doc")
    return ok(message_id=_sid("MSG", space, title), space=f"Google Chat · {space}", title=title, chars=len(body),
              preview=body[:240], simulated=True)


# --- sales & marketing: RFPs (Mercator) ---------------------------------------------------------------------------

_REQ_CATEGORIES = [
    ("Innovation", ["predictive"]),
    ("Collaboration & migration", ["workspace", "mailbox", "migration", "migrate", "cutover", "sign-on", "multi-factor"]),
    ("Support & service levels", ["support", "24x7", "on-site"]),
    ("Data platform", ["bigquery", "data platform", "dashboard", "data classification", "role-based"]),
    ("AI assistant", ["assistant"]),
    ("Security & compliance", ["iso", "wcag", "accessibility", "united states", "stored and processed"]),
    ("Experience & references", ["reference"]),
    ("Enablement", ["knowledge-transfer", "certification"]),
]


def _rfp(rfp: str) -> tuple[str, list[dict]] | None:
    text = doc_text(rfp.strip()) if re.fullmatch(r"[a-z0-9_]+", rfp.strip()) else rfp
    if not text:
        return None
    reqs = []
    for m in re.finditer(r"R-(\d+)\s*\((M|D)\)\**\s*[—–:-]+\s*(.+)", text):
        body = m.group(3).strip()
        low = _norm(body)
        cat = next((c for c, kws in _REQ_CATEGORIES if any(k in low for k in kws)), "General")
        reqs.append({"id": f"R-{m.group(1)}", "mandatory": m.group(2) == "M", "category": cat, "text": body})
    return text, reqs


@hive_tool(MODULE)
def ops_rfp_requirements(rfp: str = "ops_rfp_harborview_transit") -> dict:
    """Parse an RFP into numbered requirements (mandatory/desirable, category), key dates, budget and evaluation weights.

    Args:
        rfp: Sample document key (e.g. 'ops_rfp_harborview_transit') or the pasted RFP text with requirements written
            as 'R-01 (M) — ...' / 'R-02 (D) — ...'.

    Returns:
        Requirements list, counts, issuer, deadlines, budget ceiling, evaluation criteria and commercial terms.
    """
    parsed = _rfp(rfp)
    if not parsed:
        return err(f"no RFP {rfp!r}", hint="call list_sample_documents with prefix 'ops_rfp'")
    text, reqs = parsed
    if not reqs:
        return err("no requirements found — expected lines like 'R-01 (M) — requirement text'")
    dates = {k: (m.group(1) if (m := re.search(rf"{k}:\s*(\d{{4}}-\d{{2}}-\d{{2}})", text)) else None)
             for k in ("Issued", "Questions due", "Proposals due")}
    budget = m.group(1) if (m := re.search(r"Budget ceiling:\s*([^\n(]+)", text)) else None
    criteria = [{"criterion": a.strip(), "points": int(b)} for a, b in re.findall(r"^- (.+?):\s*(\d+) points", text, re.M)]
    terms_sec = text.split("## 5.", 1)[1].split("##", 1)[0] if "## 5." in text else ""
    terms = [ln[2:].strip() for ln in terms_sec.splitlines() if ln.startswith("- ")]
    title = text.splitlines()[0].lstrip("# ").strip()
    by_cat: dict[str, int] = {}
    for r in reqs:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    return ok(rfp=title, deadlines=dates, budget_ceiling=budget, requirements=reqs,
              counts={"total": len(reqs), "mandatory": sum(r["mandatory"] for r in reqs),
                      "desirable": sum(not r["mandatory"] for r in reqs)},
              by_category=by_cat, evaluation_criteria=criteria, commercial_terms=terms,
              lots=re.findall(r"^- (Lot [A-Z]: [^\n]+)", text, re.M))


def _evidence_pool() -> list[dict]:
    lib = fixture("ops_content")
    pool = []
    for c in lib["case_studies"]:
        if c["approved_external"]:
            pool.append({"id": c["id"], "type": "case_study", "title": c["title"], "client": c["client"],
                         "named_reference": c["named_reference"], "strength": "full", "keywords": c["keywords"],
                         "year": c["year"], "sector": c["sector"]})
    for s in lib["past_sows"]:
        pool.append({"id": s["id"], "type": "past_sow", "title": s["title"], "client": s["client"],
                     "named_reference": False, "strength": "full", "keywords": s["keywords"]})
    for c in lib["capabilities"]:
        pool.append({"id": c["id"], "type": "capability", "title": c["title"], "named_reference": False,
                     "strength": c["strength"], "keywords": c["keywords"], "limits": c.get("limits")})
    return pool


def _match(text: str, pool: list[dict]) -> tuple[str, list[dict], str]:
    low = _norm(text)
    hits = []
    for ev in pool:
        kws = [k for k in ev["keywords"] if _kw_hit(k, low)]
        if kws:
            hits.append({**{k: v for k, v in ev.items() if k != "keywords"}, "matched_terms": kws, "hits": len(kws)})
    hits.sort(key=lambda h: (-(h["hits"] >= 2 and h["strength"] == "full"), -h["hits"]))
    note = ""
    if any(h["hits"] >= 2 and h["strength"] == "full" for h in hits):
        status = "met"
    elif hits:
        status = "partial"
        lim = next((h.get("limits") for h in hits if h.get("limits")), None)
        note = lim or "Only indirect evidence — strengthen with a reference or method statement."
    else:
        status = "gap"
        note = "No evidence in the library — consider a partner, a clarification question or an exception."
    m = re.search(r"at least (two|three|four|\d+) references", low)
    if m:
        need = {"two": 2, "three": 3, "four": 4}.get(m.group(1)) or int(m.group(1))
        named = [h for h in hits if h["type"] == "case_study" and h["named_reference"]]
        if len(named) < need:
            status = "partial"
            anon = [h["id"] for h in hits if h["type"] == "case_study" and not h["named_reference"]]
            note = (f"Only {len(named)} named reference(s) approved ({', '.join(h['id'] for h in named) or 'none'}); "
                    f"{need} required. Ask the client behind {', '.join(anon) or 'another engagement'} for permission "
                    "to be named before the questions deadline.")
    return status, hits[:3], note


@hive_tool(MODULE)
def ops_match_evidence(rfp: str = "ops_rfp_harborview_transit", requirement_ids: list[str] | None = None,
                       requirement_text: str = "") -> dict:
    """Build the RFP compliance matrix: requirement → best evidence (case studies, past SOWs, capabilities) → status.

    Args:
        rfp: Sample RFP key or pasted RFP text (see ops_rfp_requirements).
        requirement_ids: Optional subset, e.g. ['R-09', 'R-12']; default = all requirements.
        requirement_text: Optional single ad-hoc requirement to match instead of the RFP list.

    Returns:
        Matrix rows (status met / partial / gap, top evidence with matched terms, gap note), coverage summary and a
        bid signal (go / conditional go / no-go) computed from mandatory coverage.
    """
    pool = _evidence_pool()
    if requirement_text.strip():
        status, ev, note = _match(requirement_text, pool)
        return ok(matrix=[{"id": "ADHOC", "mandatory": True, "text": requirement_text, "status": status,
                           "evidence": ev, "note": note}])
    parsed = _rfp(rfp)
    if not parsed or not parsed[1]:
        return err(f"no RFP requirements found for {rfp!r}")
    reqs = parsed[1]
    if requirement_ids:
        wanted = {r.upper().strip() for r in requirement_ids}
        reqs = [r for r in reqs if r["id"] in wanted]
        if not reqs:
            return err("none of the requirement_ids exist", requested=sorted(wanted))
    rows = []
    for r in reqs:
        status, ev, note = _match(r["text"], pool)
        rows.append({**r, "status": status, "evidence": ev, "note": note})

    def cnt(mand: bool, st: str) -> int:
        return sum(1 for x in rows if x["mandatory"] == mand and x["status"] == st)

    summary = {"mandatory": {s: cnt(True, s) for s in ("met", "partial", "gap")},
               "desirable": {s: cnt(False, s) for s in ("met", "partial", "gap")}}
    total = len(rows)
    coverage = round(100 * sum(1 if x["status"] == "met" else 0.5 if x["status"] == "partial" else 0
                               for x in rows) / max(1, total), 1)
    m = summary["mandatory"]
    if m["gap"]:
        bid = "no-go"
        why = "At least one mandatory requirement has no evidence — disqualification risk."
    elif m["partial"]:
        bid = "conditional go"
        why = "All mandatory requirements have evidence, but some are partial — close them before the questions deadline."
    else:
        bid = "go"
        why = "Every mandatory requirement is met with direct evidence."
    return ok(matrix=rows, summary=summary, coverage_pct=coverage, bid_signal=bid, bid_rationale=why,
              rule="Bid/no-bid thresholds are defined in the RFP Response Library (knowledge base).")


# --- sales & marketing: competitive intel (Argus) -----------------------------------------------------------------


@hive_tool(MODULE)
def ops_competitor_watchlist(days: int = 7, competitor: str = "", change_type: str = "") -> dict:
    """Read the competitive watchlist: changes observed on competitor sites, pricing pages, press, forums and job posts.

    Args:
        days: Look-back window in days from today (1-90).
        competitor: Optional competitor name or alias (e.g. 'Cobalt Cloud Partners' or 'Competitor A').
        change_type: Optional filter — 'pricing', 'offering', 'hiring', 'partnership', 'messaging', 'reputation'.

    Returns:
        Events (highest impact first) with source, confidence and suggested response; competitor profiles with
        last-known pricing and how we win. All competitors are fictional.
    """
    data = fixture("ops_competitors")
    days = max(1, min(int(days), 90))
    since = TODAY - dt.timedelta(days=days)
    comps = data["competitors"]
    name = None
    if competitor:
        name = next((n for n, p in comps.items()
                     if _norm(competitor) in (_norm(n), _norm(p["alias"])) or _norm(competitor) in _norm(n)), None)
        if not name:
            return err(f"unknown competitor {competitor!r}",
                       available=[f"{n} ({p['alias']})" for n, p in comps.items()])
    rank = {"high": 0, "medium": 1, "low": 2}
    ev = [e for e in data["events"] if dt.date.fromisoformat(e["date"]) >= since
          and (not name or e["competitor"] == name) and (not change_type or e["change_type"] == change_type.lower())]
    ev = sorted(ev, key=lambda e: (rank[e["impact"]], -dt.date.fromisoformat(e["date"]).toordinal()))
    profiles = {n: p for n, p in comps.items() if not name or n == name}
    return ok(window=f"{since.isoformat()} to {TODAY.isoformat()}", events=ev, count=len(ev),
              by_impact={k: sum(1 for e in ev if e["impact"] == k) for k in ("high", "medium", "low")},
              profiles=profiles, note="Synthetic watchlist; competitor names are invented.")


# --- sales & marketing: social (Stentor) --------------------------------------------------------------------------


def _next_slot(channel: str, taken: list[dt.datetime], cfg: dict) -> dt.datetime | None:
    win = cfg["posting_windows"][channel]
    day = TODAY + dt.timedelta(days=1)
    for _ in range(30):
        if day.strftime("%a") in win["days"]:
            for t in win["times"]:
                cand = dt.datetime.fromisoformat(f"{day.isoformat()}T{t}")
                if all(abs((cand - x).total_seconds()) >= 20 * 3600 for x in taken):
                    return cand
        day += dt.timedelta(days=1)
    return None


@hive_tool(MODULE, kind="action")
def ops_schedule_social_posts(posts: list[dict], dry_run: bool = True) -> dict:
    """Validate social posts against the social media policy and schedule them on LinkedIn / X (simulated).

    Args:
        posts: List of {"channel": "linkedin"|"x", "text": str, "slot": "YYYY-MM-DDTHH:MM" (optional — a free
            posting window is suggested when empty), "content_id": "CS-014"|"BLOG-112"|... (optional),
            "image_alt_text": str (required when an image is attached), "has_image": bool}.
        dry_run: True = validate and propose slots only; False = schedule every post that has no errors.

    Returns:
        Per post: errors, warnings, character and hashtag counts, slot (given or suggested) and, when scheduled,
        the post id.
    """
    cfg = fixture("ops_social")
    lib = fixture("ops_content")
    if not posts:
        return err("posts must not be empty")
    content = {c["id"]: c for k in ("case_studies", "blogs", "agent_capabilities") for c in lib[k]}
    restricted = [c["client"] for c in lib["case_studies"] if not (c["named_reference"] and c["approved_external"])
                  and not c["client"].startswith("a ")]
    competitors = list(fixture("ops_competitors")["competitors"])
    taken = {ch: [dt.datetime.fromisoformat(p["slot"]) for p in cfg["scheduled"] if p["channel"] == ch]
             for ch in cfg["channels"]}
    results = []
    for i, p in enumerate(posts, start=1):
        ch = str(p.get("channel", "")).lower().replace("twitter", "x")
        text = str(p.get("text", ""))
        errors, warnings = [], []
        if ch not in cfg["channels"]:
            results.append({"post": i, "errors": [f"unknown channel {ch!r} (linkedin or x)"], "warnings": []})
            continue
        rules = cfg["channels"][ch]
        low = _norm(text)
        tags = re.findall(r"#\w+", text)
        links = re.findall(r"https?://\S+", text)
        if not text.strip():
            errors.append("empty post")
        if len(text) > rules["max_chars"]:
            errors.append(f"{len(text)} characters (max {rules['max_chars']})")
        elif not rules["recommended_chars"][0] <= len(text) <= rules["recommended_chars"][1]:
            warnings.append(f"{len(text)} characters (recommended {rules['recommended_chars'][0]}-"
                            f"{rules['recommended_chars'][1]})")
        if len(tags) > rules["max_hashtags"]:
            errors.append(f"{len(tags)} hashtags (max {rules['max_hashtags']})")
        unapproved = [t for t in tags if t.lower() not in {a.lower() for a in cfg["approved_hashtags"]}]
        if unapproved:
            warnings.append(f"hashtags not on the approved list: {', '.join(unapproved)}")
        if len(links) > rules["max_links"]:
            errors.append(f"{len(links)} links (max {rules['max_links']})")
        for b in cfg["banned_phrases"]:
            if _norm(b) in low:
                errors.append(f"banned claim '{b}'")
        for c in restricted:
            if _norm(c) in low:
                errors.append(f"'{c}' is not approved to be named publicly")
        for c in competitors:
            if _norm(c) in low:
                errors.append(f"competitor '{c}' must not be mentioned")
        cid = p.get("content_id")
        if cid and cid in content and not content[cid].get("approved_external", False):
            errors.append(f"{cid} is not approved for external use")
        elif cid and cid not in content:
            warnings.append(f"unknown content_id {cid}")
        if p.get("has_image") and not str(p.get("image_alt_text", "")).strip():
            errors.append("image attached without alt text")
        slot_s = str(p.get("slot", "")).strip()
        if slot_s:
            try:
                slot = dt.datetime.fromisoformat(slot_s)
            except ValueError:
                errors.append("slot must be YYYY-MM-DDTHH:MM")
                slot = None
            if slot:
                win = cfg["posting_windows"][ch]
                if slot.date() <= TODAY:
                    errors.append("slot is not in the future")
                if slot.strftime("%a") not in win["days"] or slot.strftime("%H:%M") not in win["times"]:
                    warnings.append(f"outside the {ch} posting windows ({'/'.join(win['days'])} at "
                                    f"{', '.join(win['times'])} {cfg['timezone']})")
                clash = [x for x in taken[ch] if abs((slot - x).total_seconds()) < 20 * 3600]
                if clash:
                    warnings.append(f"within 20 h of another {ch} post at {clash[0].isoformat(timespec='minutes')}")
            suggested = False
        else:
            slot = _next_slot(ch, taken[ch], cfg)
            suggested = True
        if slot:
            taken[ch].append(slot)
        r = {"post": i, "channel": ch, "account": rules["account"], "chars": len(text), "hashtags": tags,
             "slot": slot.isoformat(timespec="minutes") if slot else None, "slot_suggested": suggested,
             "timezone": cfg["timezone"], "errors": errors, "warnings": warnings,
             "status": "invalid" if errors else ("valid (dry run)" if dry_run else "scheduled")}
        if not errors and not dry_run:
            r["post_id"] = _sid("POST", ch, text, r["slot"], n=4)
        results.append(r)
    return ok(dry_run=dry_run, results=results,
              summary={"valid": sum(1 for r in results if not r["errors"]),
                       "invalid": sum(1 for r in results if r["errors"]),
                       "scheduled": sum(1 for r in results if r.get("post_id"))},
              already_scheduled=cfg["scheduled"], simulated=True)


# --- innovation: enterprise sync (Vulcan) -------------------------------------------------------------------------

_SYS = {"hubspot": "hubspot", "hs": "hubspot", "salesforce": "salesforce", "sfdc": "salesforce", "sf": "salesforce",
        "procore": "procore"}


@hive_tool(MODULE)
def ops_map_fields(source_system: str, object_name: str = "", tenant: str = "redev_tenant_01") -> dict:
    """Propose the field mapping from a source system (HubSpot, Salesforce, Procore) into Vulcan's canonical model.

    Args:
        source_system: 'hubspot', 'salesforce' or 'procore'.
        object_name: Optional object, e.g. 'deals', 'companies', 'Opportunity', 'Account', 'projects', 'change_orders'.
        tenant: Tenant key — 'redev_tenant_01' (a real-estate developer) or 'homebuilder_tenant_02'.

    Returns:
        Mapping rows (source → canonical field, transform, confidence), rows needing review (confidence < 0.85),
        unmapped source fields, canonical coverage and the stage map used.
    """
    cfg = fixture("ops_sync")
    t = cfg["tenants"].get(tenant)
    if not t:
        return err(f"unknown tenant {tenant!r}", available=sorted(cfg["tenants"]))
    sysname = _SYS.get(_norm(source_system))
    if not sysname:
        return err(f"unknown source system {source_system!r}", available=["hubspot", "salesforce", "procore"])
    if sysname not in t["systems"]:
        return err(f"{sysname} is not connected for tenant {tenant}", connected=t["systems"])
    objs = [k for k in cfg["mappings"] if k.startswith(sysname + ".")
            and (not object_name or _norm(k.split(".", 1)[1]) == _norm(object_name).replace(" ", "_"))]
    if not objs:
        return err(f"unknown object {object_name!r} for {sysname}",
                   available=[k.split(".", 1)[1] for k in cfg["mappings"] if k.startswith(sysname + ".")])
    out, review, coverage = [], [], {}
    for o in objs:
        rows = cfg["mappings"][o]
        out.append({"object": o, "records": t["volumes"].get(o), "mappings": rows,
                    "unmapped": cfg["unmapped"].get(o, [])})
        review += [{"object": o, **r} for r in rows if r["confidence"] < 0.85]
        for r in rows:
            ent, fld = r["target"].split(".")
            coverage.setdefault(ent, set()).add(fld)
    cov = {e: {"mapped": sorted(f), "missing": [x for x in cfg["canonical_model"][e] if x not in f],
               "coverage_pct": round(100 * len(f) / len(cfg["canonical_model"][e]))} for e, f in coverage.items()}
    return ok(tenant=tenant, tenant_label=t["label"], source_system=sysname, objects=out, needs_review=review,
              canonical_coverage=cov, stage_map=cfg["stage_maps"][sysname],
              note="'source_system' and 'source_updated_at' are set by the middleware, not mapped.")


def _canon_stage(sysname: str, rec: dict, cfg: dict) -> str | None:
    raw = rec.get("dealstage") or rec.get("StageName")
    return cfg["stage_maps"][sysname].get(raw) if raw else None


@hive_tool(MODULE)
def ops_resolve_sync_conflicts(project_code: str = "", tenant: str = "redev_tenant_01") -> dict:
    """Resolve conflicting records for the same project across HubSpot, Salesforce and Procore using the tenant rules.

    Rules: stage = most advanced CRM stage (won vs lost → manual review); amount = Procore contract value once won,
    else the most recently updated CRM; CRM amounts differing by more than 10% → manual review; sources not updated
    in 90+ days are flagged stale; names come from Procore when the project exists.

    Args:
        project_code: Project code, e.g. 'PRJ-2207'; empty resolves every conflicting project.
        tenant: Tenant key (default 'redev_tenant_01', a real-estate developer).

    Returns:
        Per project: winning value and winning system per field with the rule applied, write-backs to push to each
        source, manual-review items and stale sources.
    """
    cfg = fixture("ops_sync")
    if tenant not in cfg["tenants"]:
        return err(f"unknown tenant {tenant!r}", available=sorted(cfg["tenants"]))
    if tenant != "redev_tenant_01":
        return ok(tenant=tenant, resolutions=[], note="No open conflicts for this tenant in the demo data.")
    recs = cfg["records"]
    codes = [project_code.upper().strip()] if project_code else sorted(recs)
    rules = cfg["rules"]
    order = rules["stage_order"]
    now = dt.datetime(2026, 11, 6, 15, 0, tzinfo=dt.timezone.utc)
    out = []
    for code in codes:
        r = recs.get(code)
        if not r:
            return err(f"unknown project {code!r}", available=sorted(recs))
        crm = {s: r[s] for s in ("hubspot", "salesforce") if s in r}
        upd = {s: dt.datetime.fromisoformat(v["updated"].replace("Z", "+00:00")) for s, v in r.items() if s != "label"}
        stale = [s for s, u in upd.items() if (now - u).days >= rules["stale_source_days"]]
        stages = {s: _canon_stage(s, v, cfg) for s, v in crm.items()}
        manual, fields, writebacks = [], {}, []
        if "lost" in stages.values() and any(v in ("contracting", "won") for v in stages.values()):
            manual.append(f"Stage conflict: {stages} — one CRM says lost while another is active.")
            fields["stage"] = {"value": None, "winner": "manual review", "rule": "won/active vs lost"}
        else:
            live = {s: v for s, v in stages.items() if v in order and s not in stale} or \
                   {s: v for s, v in stages.items() if v in order}
            win_sys = max(live, key=lambda s: (order.index(live[s]), upd[s]))
            fields["stage"] = {"value": live[win_sys], "winner": win_sys, "rule": "most advanced CRM stage"}
        amounts = {s: v.get("amount", v.get("Amount")) for s, v in crm.items()}
        amount_conflict = False
        if len(amounts) == 2:
            a, b = amounts.values()
            delta = abs(a - b) / max(a, b) * 100
            if delta > rules["amount_manual_review_delta_pct"]:
                amount_conflict = True
                manual.append(f"CRM amounts differ by {delta:.1f}% ({amounts}) — above the "
                              f"{rules['amount_manual_review_delta_pct']}% threshold.")
        if amount_conflict:
            fields["amount_usd"] = {"value": None, "winner": "manual review", "rule": "CRM delta above threshold"}
        elif fields["stage"]["value"] == "won" and "procore" in r:
            pc = r["procore"]
            fields["amount_usd"] = {"value": pc["total_value"], "winner": "procore",
                                    "rule": "post-contract amount = Procore contract value (incl. approved change orders)",
                                    "approved_change_orders_usd": pc.get("approved_change_orders_usd", 0)}
        else:
            fresh = [s for s in amounts if s not in stale] or list(amounts)
            latest = max(fresh, key=lambda s: upd[s])
            fields["amount_usd"] = {"value": amounts[latest], "winner": latest, "rule": "most recently updated CRM"}
        close_sys = fields["stage"]["winner"] if fields["stage"]["winner"] in crm else max(crm, key=lambda s: upd[s])
        cd = crm[close_sys].get("closedate") or crm[close_sys].get("CloseDate")
        fields["close_date"] = {"value": cd, "winner": close_sys, "rule": "from the system holding the winning stage"}
        name_src = "procore" if "procore" in r else max(crm, key=lambda s: upd[s])
        name = r[name_src].get("name") or r[name_src].get("Name") or r[name_src].get("dealname")
        fields["name"] = {"value": name, "winner": name_src, "rule": "Procore name when the project exists"}
        for s, v in crm.items():
            cur_amt = v.get("amount", v.get("Amount"))
            cur_name = v.get("dealname") or v.get("Name")
            if fields["amount_usd"]["value"] and cur_amt != fields["amount_usd"]["value"]:
                writebacks.append({"system": s, "field": "amount", "from": cur_amt, "to": fields["amount_usd"]["value"]})
            if fields["stage"]["value"] and stages[s] != fields["stage"]["value"]:
                writebacks.append({"system": s, "field": "stage", "from": stages[s], "to": fields["stage"]["value"]})
            if cur_name != name:
                writebacks.append({"system": s, "field": "name", "from": cur_name, "to": name})
        out.append({"project_code": code, "label": r["label"], "systems": [s for s in r if s != "label"],
                    "resolved": fields, "write_backs": writebacks, "manual_review": manual, "stale_sources": stale,
                    "auto_resolved": not manual})
    return ok(tenant=tenant, resolutions=out,
              summary={"projects": len(out), "auto_resolved": sum(o["auto_resolved"] for o in out),
                       "manual_review": sum(not o["auto_resolved"] for o in out)})


@hive_tool(MODULE, kind="action")
def ops_simulate_sync_run(tenant: str = "redev_tenant_01", systems: list[str] | None = None,
                          mode: str = "initial_load", dry_run: bool = True) -> dict:
    """Plan or simulate a Vulcan sync run into BigQuery: record counts, API-call budget, tables, schedule.

    Args:
        tenant: Tenant key ('redev_tenant_01' = a real-estate developer, 'homebuilder_tenant_02').
        systems: Subset of connected systems (default: all connected).
        mode: 'initial_load' (full extract) or 'incremental' (daily change volume).
        dry_run: True = plan only (default). False = simulated execution with run id.

    Returns:
        Per object: records, API calls and BigQuery target tables; daily API utilisation vs tenant limits,
        Pub/Sub message estimate, conflict queue size and the recommended schedule.
    """
    cfg = fixture("ops_sync")
    t = cfg["tenants"].get(tenant)
    if not t:
        return err(f"unknown tenant {tenant!r}", available=sorted(cfg["tenants"]))
    if mode not in ("initial_load", "incremental"):
        return err("mode must be initial_load or incremental")
    chosen = [_SYS.get(_norm(s), s) for s in (systems or t["systems"])]
    bad = [s for s in chosen if s not in t["systems"]]
    if bad:
        return err(f"systems not connected for {tenant}: {bad}", connected=t["systems"])
    objs, api = [], {}
    for key, vol in t["volumes"].items():
        sysname, obj = key.split(".")
        if sysname not in chosen:
            continue
        recs = vol if mode == "initial_load" else max(1, round(vol * t["daily_change_rate"].get(key, 0.02)))
        reads = -(-recs // 100)
        writes = 0 if mode == "initial_load" else -(-recs // 50)      # write-backs of resolved fields
        api[sysname] = api.get(sysname, 0) + reads + writes
        ent = next((m["target"].split(".")[0] for m in cfg["mappings"].get(key, [])), "Other")
        objs.append({"object": key, "records": recs, "api_reads": reads, "api_writes": writes,
                     "raw_table": f"raw_{sysname}_{obj.lower()}", "canonical_table": f"canonical_{ent.lower()}"})
    util = {s: {"calls": c, "daily_limit": t["api_limits_per_day"][s],
                "utilisation_pct": round(100 * c / t["api_limits_per_day"][s], 2)} for s, c in api.items()}
    conflicts = 0
    if tenant == "redev_tenant_01":
        res = ops_resolve_sync_conflicts(tenant=tenant)
        conflicts = res["summary"]["manual_review"] if res["status"] == "ok" else 0
    plan = ok(tenant=tenant, tenant_label=t["label"], mode=mode, systems=chosen, objects=objs,
              totals={"records": sum(o["records"] for o in objs), "api_calls": sum(api.values()),
                      "pubsub_messages": sum(o["records"] for o in objs) * 2},
              api_utilisation=util, conflict_queue=conflicts, warehouse=t["warehouse"],
              schedule="Webhooks + 15-minute CDC polling for CRM objects; hourly Procore polling; nightly "
                       "reconciliation job; conflicts routed to a manual-review queue.",
              dry_run=dry_run, simulated=True)
    if not dry_run:
        plan["run_id"] = _sid("SYNC", tenant, mode, ",".join(chosen))
        plan["result"] = "completed (simulated)"
    return plan


# --- innovation: onboarding (Chiron) ------------------------------------------------------------------------------


def _hire(ref: str) -> dict | None:
    key = _norm(ref)
    for h in fixture("ops_onboarding")["new_hires"]:
        if key in (_norm(h["id"]), _norm(h["name"])) or (len(key) > 3 and key in _norm(h["name"])):
            return h
    return None


def _role_systems(role: str, systems: dict) -> list[str]:
    return [k for k, v in systems.items() if "roles" not in v or role in v["roles"]]


@hive_tool(MODULE)
def ops_onboarding_status(new_hire: str) -> dict:
    """Show a new hire's 90-day onboarding status: day number, benefits deadline, tool access, certifications, next steps.

    Args:
        new_hire: New-hire id or name (e.g. 'NH-311' or 'Sofia Marín'), or a role name (e.g. 'Data Engineer') to get
            that role's standard path.

    Returns:
        Day N of 90, current 30/60/90 milestone, benefits enrollment deadline and days left, access status per
        required system, certification path with target dates, and prioritised next actions.
    """
    ob = fixture("ops_onboarding")
    role_hit = next((r for r in ob["role_paths"] if _norm(r) in _norm(new_hire)), None)
    h = _hire(new_hire)
    if not h and role_hit:
        p = ob["role_paths"][role_hit]
        return ok(role=role_hit, certifications=p["certifications"], milestones=p["milestones"],
                  required_systems=[ob["systems"][s]["label"] for s in _role_systems(role_hit, ob["systems"])],
                  note="Exam voucher and retake rules are in the New-Hire Academy Guide (knowledge base).")
    if not h:
        return err(f"unknown new hire {new_hire!r}",
                   available=[f"{x['id']} {x['name']}" for x in ob["new_hires"]], roles=sorted(ob["role_paths"]))
    start = dt.date.fromisoformat(h["start_date"])
    day = (TODAY - start).days + 1
    path = ob["role_paths"][h["role"]]
    window = "pre-start" if day < 1 else "1-30" if day <= 30 else "31-60" if day <= 60 else "61-90" if day <= 90 else "done"
    milestone = path["milestones"].get({"1-30": "30", "31-60": "60", "61-90": "90"}.get(window, "30"))
    deadline = start + dt.timedelta(days=ob["benefits_enrollment_days"])
    benefits = {"deadline": deadline.isoformat(), "days_left": (deadline - TODAY).days,
                "status": "enrolled" if h["benefits_enrolled"] else
                ("overdue" if TODAY > deadline else "open")}
    access = []
    for s in _role_systems(h["role"], ob["systems"]):
        meta = ob["systems"][s]
        access.append({"system": s, "label": meta["label"], "status": h["access"].get(s, "not requested"),
                       "approver": meta["approver"], "sla_hours": meta["sla_hours"]})
    certs = []
    for c in path["certifications"]:
        target = start + dt.timedelta(days=c["target_day"])
        done = c["name"] in h["certifications_done"]
        booked = bool(h["exam_booked"] and c["name"] in h["exam_booked"])
        weeks_left = max(1, (target - TODAY).days // 7)
        st = "done" if done else "booked" if booked else ("at risk" if (target - TODAY).days < 21 else "on track")
        certs.append({"name": c["name"], "target_date": target.isoformat(), "status": st,
                      "study_hours": c["study_hours"],
                      "suggested_hours_per_week": None if done else round(c["study_hours"] / weeks_left, 1)})
    actions = []
    if benefits["status"] != "enrolled":
        actions.append(f"Complete benefits enrollment by {benefits['deadline']} ({benefits['days_left']} days left).")
    missing = [a["label"] for a in access if a["status"] == "not requested"]
    pending = [a["label"] for a in access if a["status"] == "pending"]
    if missing:
        actions.append("Request access: " + ", ".join(missing) + ".")
    if pending:
        actions.append("Follow up on pending access: " + ", ".join(pending) + ".")
    nxt = next((c for c in certs if c["status"] not in ("done", "booked")), None)
    if nxt:
        actions.append(f"Study for {nxt['name']} (~{nxt['suggested_hours_per_week']} h/week) and book the exam "
                       f"before {nxt['target_date']}.")
    actions.append(f"Milestone for days {window}: {milestone}")
    on_track = benefits["status"] != "overdue" and not any(c["status"] == "at risk" for c in certs)
    return ok(id=h["id"], name=h["name"], role=h["role"], start_date=h["start_date"], day=max(day, 0),
              window=window, manager=h["manager"], buddy=h["buddy"], benefits=benefits, access=access,
              courses_done=h["courses_done"], certifications=certs, next_actions=actions, on_track=on_track)


@hive_tool(MODULE, kind="action")
def ops_request_tool_access(new_hire: str, systems: list[str]) -> dict:
    """Raise access requests for a new hire's tools with the right approver and SLA (simulated tickets).

    Args:
        new_hire: New-hire id or name (e.g. 'NH-314' or 'Kwame Mensah').
        systems: System keys or labels, e.g. ['jira', 'hubspot', 'workspace_admin_lab', 'expense_tool'].

    Returns:
        Ticket per system (approver, SLA, expected by), systems skipped because already granted or pending, and
        requests flagged as outside the role's standard access (need manager justification).
    """
    ob = fixture("ops_onboarding")
    h = _hire(new_hire)
    if not h:
        return err(f"unknown new hire {new_hire!r}")
    if not systems:
        return err("systems must not be empty", available=sorted(ob["systems"]))
    std = set(_role_systems(h["role"], ob["systems"]))
    created, skipped, unknown = [], [], []
    for s in systems:
        key = next((k for k, v in ob["systems"].items()
                    if _norm(s) in (_norm(k), _norm(v["label"])) or _norm(s).replace(" ", "_") == k
                    or (len(_norm(s)) > 3 and _norm(s) in _norm(v["label"]))), None)
        if not key:
            unknown.append(s)
            continue
        status = h["access"].get(key, "not requested")
        if status in ("granted", "pending"):
            skipped.append({"system": key, "status": status})
            continue
        meta = ob["systems"][key]
        created.append({"ticket": _sid("REQ", h["id"], key, n=5), "system": key, "label": meta["label"],
                        "approver": meta["approver"], "sla_hours": meta["sla_hours"],
                        "expected_by": _business_days(TODAY, max(1, -(-meta["sla_hours"] // 24))).isoformat(),
                        "needs_manager_justification": key not in std})
    if unknown and not created and not skipped:
        return err(f"unknown systems {unknown}", available=sorted(ob["systems"]))
    return ok(new_hire=f"{h['id']} {h['name']}", role=h["role"], requests=created, skipped=skipped,
              unknown=unknown, notified=[h["manager"], h["buddy"]], simulated=True)


# --- innovation: churn (Oracle) -----------------------------------------------------------------------------------

_WEIGHTS = {"attendance": 0.10, "sponsor": 0.15, "sentiment_level": 0.15, "sentiment_trend": 0.10,
            "support": 0.12, "adoption": 0.10, "finance": 0.10, "delivery": 0.10, "nps": 0.08}
_BANDS = [(70, "critical"), (50, "high"), (30, "watch"), (0, "healthy")]
_PLAYS = {
    "critical": "Executive save plan within 5 business days: Wursta executive call with the sponsor, recovery plan "
                "with dated milestones, commercial goodwill review, weekly health check until green.",
    "high": "Account review (CSM + engagement lead) within 10 business days; re-engage the sponsor; fix the top two "
            "drivers and re-score after the next meeting.",
    "watch": "CSM monitors bi-weekly; address the top driver; confirm the sponsor's priorities at the next QBR.",
    "healthy": "Business as usual — ask for a reference or case study and explore expansion.",
}


def _churn(a: dict, override: float | None) -> dict:
    m = a["metrics"]
    meets = sorted((x for x in fixture("ops_meetings")["meetings"] if x["account_id"] == a["id"]),
                   key=lambda x: x["date"])
    sents = [x["sentiment_score"] for x in meets if x["sentiment_score"] is not None]
    if not sents and a.get("sentiment_latest") is not None:
        sents = [a["sentiment_latest"]]
    if override is not None and sents:
        sents = sents[:-1] + [max(-1.0, min(1.0, override))]
    elif override is not None:
        sents = [max(-1.0, min(1.0, override))]
    latest = sents[-1] if sents else 0.3
    prev = sents[-4:-1]
    trend = latest - (sum(prev) / len(prev)) if prev else 0.0
    feats = {
        "attendance": (_clip((0.95 - m["meeting_attendance_rate"]) / 0.35),
                       f"Meeting attendance {round(m['meeting_attendance_rate'] * 100)}% (target 95%)"),
        "sponsor": (_clip((0.9 - m["exec_sponsor_attendance_90d"]) / 0.7),
                    f"Executive sponsor attended {round(m['exec_sponsor_attendance_90d'] * 100)}% of meetings in 90 days"),
        "sentiment_level": (_clip((0.5 - latest) / 1.0), f"Latest meeting sentiment {latest:+.2f}"),
        "sentiment_trend": (_clip(-trend / 0.6), f"Sentiment trend {trend:+.2f} vs previous meetings"
                            if prev else "No sentiment history to trend"),
        "support": (0.4 * _clip(m["support_tickets_open"] / 12) + 0.4 * _clip(m["p1_tickets_90d"] / 3)
                    + 0.2 * _clip(m["avg_ticket_age_days"] / 15),
                    f"{m['support_tickets_open']} open tickets, {m['p1_tickets_90d']} P1 in 90 days, "
                    f"avg age {m['avg_ticket_age_days']} days"),
        "adoption": (_clip((80 - m["product_adoption_pct"]) / 60), f"Adoption {m['product_adoption_pct']}% (target 80%)"),
        "finance": (_clip(m["invoice_days_overdue"] / 60), f"Invoice {m['invoice_days_overdue']} days overdue"),
        "delivery": (_clip(m["milestones_slipped"] / 3), f"{m['milestones_slipped']} milestone(s) slipped this quarter"),
        "nps": (_clip((50 - m["nps"]) / 60), f"NPS {m['nps']}"),
    }
    contrib = {k: round(_WEIGHTS[k] * v[0] * 100, 1) for k, v in feats.items()}
    score = round(sum(contrib.values()))
    band = next(b for t, b in _BANDS if score >= t)
    drivers = sorted(({"driver": k, "points": contrib[k], "risk_0_1": round(feats[k][0], 2), "evidence": feats[k][1]}
                      for k in feats), key=lambda d: -d["points"])
    renewal = (dt.date.fromisoformat(a["renewal_date"]) - TODAY).days
    return {"account_id": a["id"], "account": a["name"], "score": score, "band": band,
            "previous_crm_score": a.get("crm_churn_score"), "delta_vs_crm": score - a.get("crm_churn_score", score),
            "renewal_date": a["renewal_date"], "renewal_in_days": renewal, "arr_usd": a["arr_usd"],
            "top_drivers": drivers[:4], "protective_factors": [d for d in drivers if d["points"] <= 1.0][:3],
            "sentiment_used": {"latest": latest, "history": sents, "override_applied": override is not None},
            "recommended_play": _PLAYS[band], "urgent": band in ("critical", "high") and renewal <= 120}


@hive_tool(MODULE)
def ops_churn_risk_score(account: str = "", sentiment_override: float | None = None) -> dict:
    """Score churn risk (0-100) with an explainable weighted model over engagement, sentiment, support and finance.

    Weights: sponsor attendance 15, latest sentiment 15, support load 12, attendance 10, sentiment trend 10,
    adoption 10, overdue invoices 10, slipped milestones 10, NPS 8. Bands: >=70 critical, 50-69 high, 30-49 watch,
    <30 healthy.

    Args:
        account: Account name or id (e.g. 'Tallbridge Logistics' or 'ACC-1042'); empty ranks every account.
        sentiment_override: Optional latest-meeting sentiment (-1 to +1), e.g. Helios's fresh score, replacing the
            stored score of the most recent meeting.

    Returns:
        Score, band, point contribution and evidence per driver, protective factors, days to renewal, change vs the
        CRM's current score and the recommended play — or a ranked portfolio when no account is given.
    """
    accts = fixture("ops_accounts")["accounts"]
    if account:
        a = _account(account)
        if not a:
            return err(f"unknown account {account!r}", available=[x["name"] for x in accts])
        return ok(**_churn(a, sentiment_override), model="weighted explainable score v1 (synthetic demo data)")
    ranked = sorted((_churn(a, None) for a in accts), key=lambda r: -r["score"])
    return ok(portfolio=[{k: r[k] for k in ("account_id", "account", "score", "band", "renewal_in_days", "arr_usd",
                                             "urgent")} | {"top_driver": r["top_drivers"][0]["evidence"]}
                         for r in ranked],
              arr_at_risk_usd=sum(r["arr_usd"] for r in ranked if r["band"] in ("critical", "high")),
              model="weighted explainable score v1 (synthetic demo data)")


@hive_tool(MODULE, kind="action")
def ops_update_account_risk(account: str, score: int, band: str, drivers: list[str], save_plan: str = "") -> dict:
    """Write the churn-risk score to the CRM account and open a save-plan task for the CSM when high/critical (simulated).

    Args:
        account: Account name or id.
        score: Score 0-100 from ops_churn_risk_score (never invented).
        band: 'critical', 'high', 'watch' or 'healthy'.
        drivers: Top drivers in plain words.
        save_plan: Save-plan summary (required for high/critical).

    Returns:
        CRM record id, previous vs new score, the CSM task (owner, due date) and who was notified.
    """
    a = _account(account)
    if not a:
        return err(f"unknown account {account!r}")
    band = band.lower().strip()
    if band not in _PLAYS or not 0 <= int(score) <= 100:
        return err("band must be critical/high/watch/healthy and score 0-100")
    if band in ("critical", "high") and len(save_plan.split()) < 8:
        return err("a save plan (8+ words) is required for high and critical accounts")
    task = None
    if band in ("critical", "high"):
        due = _business_days(TODAY, 5 if band == "critical" else 10)
        task = {"task_id": _sid("CSM", a["id"], score), "owner": a["csm"], "title": f"Save plan — {a['name']}",
                "due": due.isoformat(), "plan": save_plan}
    notified = [a["csm"]] + ([a["account_exec"], a["pm"], "VP Customer Success"] if band == "critical" else
                             [a["account_exec"]] if band == "high" else [])
    return ok(crm_record=_sid("CRM", a["id"]), account=a["name"], previous_score=a.get("crm_churn_score"),
              new_score=int(score), band=band, drivers=drivers[:5], task=task, notified=notified, simulated=True)


# --- innovation: guardrails (Aegis) -------------------------------------------------------------------------------

_INJECTION = [
    (r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?)", 0.6, "instruction override"),
    (r"disregard (the |your |all )?(system|previous|prior) (prompt|instructions)", 0.6, "instruction override"),
    (r"(reveal|print|show) (your|the) (system prompt|hidden instructions|instructions)", 0.4, "system-prompt extraction"),
    (r"you are now|developer mode|jailbreak|\bdan\b", 0.3, "role hijack"),
    (r"(send|upload|post|exfiltrate)[^.]{0,80}https?://", 0.4, "data exfiltration to URL"),
    (r"(full|entire|all) (customer|client|user) (list|database|records)", 0.2, "bulk data request"),
    (r"[A-Za-z0-9+/]{120,}={0,2}", 0.2, "long encoded blob"),
]
_SECRETS = [
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"\b[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com\b", "service-account identity"),
    (r"(?i)\b[\w-]*(api[_-]?key|secret|token|passw(?:or)?d)\s*[=:]\s*\S+", "credential assignment"),
]


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _scan(prompt: str) -> dict:
    findings, red = [], prompt
    counters: dict[str, int] = {}

    def sub(pattern: str, label: str, kind: str, check=None, flags: int = 0) -> None:
        nonlocal red

        def rep(m: re.Match) -> str:
            val = m.group(0)
            if check and not check(val):
                return val
            counters[label] = counters.get(label, 0) + 1
            masked = val[:2] + "***" + val[-4:] if len(val) > 8 else "***"
            findings.append({"type": label, "category": kind, "masked": masked})
            return f"[{label.upper().replace(' ', '_').replace('-', '_')}_{counters[label]}]"

        red = re.sub(pattern, rep, red, flags=flags)

    for pat, label in _SECRETS:
        sub(pat, label, "secret")
    sub(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", "payment card", "pii", check=lambda v: _luhn(re.sub(r"\D", "", v)))
    sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "email", "pii")
    sub(r"\b\d{3}-\d{2}-\d{4}\b", "national id", "pii")
    sub(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)", "phone", "pii")
    sub(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}\b", "iban", "pii")
    inj, rules = 0.0, []
    for pat, w, label in _INJECTION:
        if re.search(pat, prompt, re.I):
            inj += w
            rules.append(label)
    inj = round(min(1.0, inj), 2)
    secrets = [f for f in findings if f["category"] == "secret"]
    pii = [f for f in findings if f["category"] == "pii"]
    if inj >= 0.6 or secrets:
        verdict = "block"
    elif pii:
        verdict = "redact"
    elif inj > 0:
        verdict = "allow_with_warning"
    else:
        verdict = "allow"
    return {"verdict": verdict, "injection_score": inj, "injection_rules": rules, "findings": findings,
            "pii_count": len(pii), "secret_count": len(secrets),
            "redacted_prompt": red if verdict in ("redact", "allow_with_warning") else None}


@hive_tool(MODULE)
def ops_guardrail_scan(prompt: str, caller: str = "") -> dict:
    """Scan an outbound model prompt for PII, secrets and prompt injection; return a verdict and the redacted prompt.

    Deterministic regex/heuristic pre-check that mirrors the production control (Model Armor templates plus
    Sensitive Data Protection on the Vertex AI call path).

    Args:
        prompt: The prompt text, or an intercepted call id from the log (e.g. 'CALL-9005').
        caller: Calling agent (optional; adds the caller's cost-anomaly status).

    Returns:
        Verdict (allow / allow_with_warning / redact / block), findings with masked values, injection score and
        matched rules, the redacted prompt when redaction applies, and the caller's spend vs baseline.
    """
    data = fixture("ops_aegis")
    call = next((c for c in data["calls"] if c["id"].lower() == prompt.strip().lower()), None)
    text = call["prompt"] if call else prompt
    if not text.strip():
        return err("prompt is empty")
    res = _scan(text)
    caller = caller or (call or {}).get("caller", "")
    usage = None
    if caller in data["baselines_hourly"]:
        b, c = data["baselines_hourly"][caller], data["current_hour"][caller]
        ratio = round(c["tokens"] / max(1, b["tokens"]), 1)
        usage = {"caller": caller, "tokens_vs_baseline": ratio, "calls_this_hour": c["calls"],
                 "cost_usd_this_hour": c["cost_usd"],
                 "anomaly": ratio >= data["thresholds"]["cost_anomaly_multiplier"]
                 or c["cost_usd"] >= data["thresholds"]["hourly_cost_alert_usd"]}
    return ok(call_id=(call or {}).get("id"), caller=caller or None, **res, caller_usage=usage,
              production_control="Model Armor (prompt-injection & jailbreak, sensitive data, malicious URLs) + "
                                 "Sensitive Data Protection infoTypes; this tool is the demo pre-check.")


@hive_tool(MODULE)
def ops_outbound_call_log(caller: str = "") -> dict:
    """Read the last hour of intercepted outbound model calls with Aegis verdicts and per-agent spend vs baseline.

    Args:
        caller: Optional calling-agent filter (e.g. 'stentor_agent').

    Returns:
        Calls (id, time, caller, tier, tokens, prompt preview, verdict), verdict counts, per-caller usage with
        anomaly flags (tokens or calls >= 3x baseline, or hourly cost >= alert threshold) and recommended actions.
    """
    data = fixture("ops_aegis")
    calls = [c for c in data["calls"] if not caller or c["caller"] == caller]
    if caller and not calls and caller not in data["baselines_hourly"]:
        return err(f"unknown caller {caller!r}", available=sorted(data["baselines_hourly"]))
    th = data["thresholds"]
    rows = []
    for c in calls:
        s = _scan(c["prompt"])
        rows.append({"id": c["id"], "time": c["time"], "caller": c["caller"], "tier": c["model_tier"],
                     "prompt_tokens": c["prompt_tokens"], "preview": c["prompt"][:70] + "…", "verdict": s["verdict"],
                     "reasons": sorted({f["type"] for f in s["findings"]} | set(s["injection_rules"]))})
    usage, actions = [], []
    for name, b in data["baselines_hourly"].items():
        if caller and name != caller:
            continue
        cur = data["current_hour"][name]
        tr, cr = cur["tokens"] / max(1, b["tokens"]), cur["calls"] / max(1, b["calls"])
        anomaly = tr >= th["cost_anomaly_multiplier"] or cr >= th["cost_anomaly_multiplier"] \
            or cur["cost_usd"] >= th["hourly_cost_alert_usd"]
        usage.append({"caller": name, "calls": cur["calls"], "baseline_calls": b["calls"], "tokens": cur["tokens"],
                      "tokens_vs_baseline": round(tr, 1), "calls_vs_baseline": round(cr, 1),
                      "cost_usd": cur["cost_usd"], "anomaly": anomaly})
        if anomaly:
            actions.append(f"Throttle {name} to 2x baseline and page its owner — {round(cr)}x calls, {round(tr)}x "
                           "tokens (likely retry loop).")
    for r in rows:
        if r["verdict"] == "block":
            actions.append(f"{r['id']} blocked ({', '.join(r['reasons'])}) — notify the {r['caller']} owner.")
    return ok(window=data["window"], calls=rows,
              verdicts={v: sum(1 for r in rows if r["verdict"] == v)
                        for v in ("allow", "allow_with_warning", "redact", "block")},
              usage=usage, recommended_actions=actions, thresholds=th)


# --- innovation: offboarding (Charon) -----------------------------------------------------------------------------


def _case(ref: str) -> tuple[str, dict] | None:
    key = _norm(ref)
    for cid, c in fixture("ops_offboarding")["cases"].items():
        if key in (_norm(cid), _norm(c["name"]), _norm(c["account"])) or (len(key) > 3 and key in _norm(c["name"])):
            return cid, c
    return None


def _applicable(step: str, c: dict) -> tuple[bool, str]:
    inv = c["inventory"]
    if step == "S2":
        return bool(inv["client_tenants_delegated_admin"]), ", ".join(inv["client_tenants_delegated_admin"]) or "none"
    if step == "S3":
        g = inv["gcp"]
        return bool(g["projects_with_personal_bindings"] or g["user_managed_sa_keys"]), \
            f"{len(g['projects_with_personal_bindings'])} projects, {g['user_managed_sa_keys']} user-managed keys"
    if step == "S4":
        return inv["github"]["member"], f"member; repos owned: {', '.join(inv['github']['repos_owned']) or 'none'}"
    if step == "S7":
        return bool(inv["recurring_events_organised"] or inv["chat_spaces_owned"]), \
            f"{inv['recurring_events_organised']} recurring events, {inv['chat_spaces_owned']} Chat spaces"
    if step == "S8":
        return bool(inv["saas"]), ", ".join(inv["saas"])
    if step == "S5":
        return True, f"{inv['drive_files_owned']} files; sole manager of: " + \
            (", ".join(inv["shared_drives_sole_manager"]) or "none")
    if step == "S6":
        return True, f"{inv['gmail_size_gb']} GB mailbox"
    if step == "S9":
        hw = inv["hardware"]
        return True, f"laptop {hw['laptop']}, security key {hw['security_key']}, returned: {hw['returned']}"
    return True, "account " + c["account"]


@hive_tool(MODULE)
def ops_offboarding_inventory(employee: str) -> dict:
    """Inventory a leaver's access and data and build the policy-ordered deprovisioning checklist with deadlines.

    Args:
        employee: Offboarding case id or name (e.g. 'OFF-077' or 'Ryan Caldwell').

    Returns:
        Inventory (Drive, mail, OAuth apps, GitHub, Google Cloud bindings and keys, client tenants, SaaS, hardware),
        applicable steps S1-S10 with due time and overdue flag, legal-hold restrictions and risk flags.
    """
    ob = fixture("ops_offboarding")
    found = _case(employee)
    if not found:
        return err(f"unknown offboarding case {employee!r}",
                   available=[f"{k} {v['name']}" for k, v in ob["cases"].items()])
    cid, c = found
    term = dt.datetime.fromisoformat(c["termination_time"])
    now = dt.datetime.fromisoformat(ob["now"])
    steps = []
    for s in ob["policy_steps"]:
        appl, detail = _applicable(s["id"], c)
        due = term + dt.timedelta(hours=s["sla_hours"])
        restriction = None
        if c["legal_hold"] and s["id"] == "S10":
            restriction = "BLOCKED — no deletion while the legal hold is active"
        elif c["legal_hold"] and s["id"] == "S9":
            restriction = "Image the device for Legal before any wipe"
        elif c["legal_hold"] and s["id"] == "S6":
            restriction = "Apply the legal Vault hold (indefinite) instead of standard retention"
        steps.append({**s, "applicable": appl, "detail": detail, "due": due.isoformat(timespec="minutes"),
                      "overdue": appl and now > due, "restriction": restriction})
    inv = c["inventory"]
    flags = []
    if inv["shared_drives_sole_manager"]:
        flags.append("Sole manager of shared drives — add a co-manager before suspension to avoid orphaned drives.")
    if inv["client_tenants_delegated_admin"]:
        flags.append("Delegated admin in a client tenant — revoke within 4 hours and notify the client PM.")
    if inv["gcp"]["user_managed_sa_keys"]:
        flags.append(f"{inv['gcp']['user_managed_sa_keys']} user-managed service-account key(s) — disable, do not "
                     "just remove the user.")
    if inv["oauth_apps"] >= 4:
        flags.append(f"{inv['oauth_apps']} third-party OAuth grants — revoke tokens with S1.")
    if now > term:
        flags.append(f"Termination time {term.isoformat(timespec='minutes')} has passed — same-day steps are due now.")
    return ok(case=cid, name=c["name"], role=c["role"], manager=c["manager"], type=c["type"],
              termination_time=c["termination_time"], now=ob["now"], legal_hold=c["legal_hold"],
              legal_hold_reason=c.get("legal_hold_reason"), inventory=inv, steps=steps,
              overdue_steps=[s["id"] for s in steps if s["overdue"]], risk_flags=flags)


@hive_tool(MODULE, kind="action")
def ops_execute_deprovisioning(employee: str, steps: list[str] | None = None, dry_run: bool = True) -> dict:
    """Execute (or dry-run) deprovisioning steps for a leaver and write a hash-chained evidence log (simulated).

    Args:
        employee: Offboarding case id or name (e.g. 'OFF-083').
        steps: Step ids such as ['S1', 'S2', 'S3'] or ['same_day'] (all steps with SLA <= 8 hours);
            default = every applicable step.
        dry_run: True = show what would happen (default); False = simulate execution and record evidence.

    Returns:
        Per step: actions, status (planned / done / scheduled / blocked / pending return), evidence ids and a
        hash-chained audit log; blocked steps are explained (e.g. legal hold).
    """
    ob = fixture("ops_offboarding")
    found = _case(employee)
    if not found:
        return err(f"unknown offboarding case {employee!r}")
    cid, c = found
    pol = {s["id"]: s for s in ob["policy_steps"]}
    wanted = [s.upper() for s in (steps or [])]
    if not wanted:
        ids = list(pol)
    elif "SAME_DAY" in wanted:
        ids = [k for k, v in pol.items() if v["sla_hours"] <= 8]
    else:
        ids = [s for s in wanted if s in pol]
        if not ids:
            return err("no valid step ids", available=list(pol) + ["same_day"])
    inv = c["inventory"]
    actions_for = {
        "S1": ["Suspend " + c["account"], "Reset password and sign out all sessions",
               f"Revoke {inv['oauth_apps']} OAuth tokens and app passwords"],
        "S2": [f"Remove delegated admin in {t}" for t in inv["client_tenants_delegated_admin"]]
              + ["Notify the client PM and the account CSM"],
        "S3": [f"Remove personal IAM bindings in: {p}" for p in inv["gcp"]["projects_with_personal_bindings"]]
              + ([f"Disable {inv['gcp']['user_managed_sa_keys']} user-managed service-account key(s) created by the user"]
                 if inv["gcp"]["user_managed_sa_keys"] else []),
        "S4": ["Remove from GitHub organisation"] + [f"Transfer repo {r} to the team" for r in inv["github"]["repos_owned"]],
        "S5": [f"Transfer {inv['drive_files_owned']} Drive files to {c['manager']}"]
              + [f"Reassign manager role on shared drive '{d}'" for d in inv["shared_drives_sole_manager"]],
        "S6": [f"Delegate mailbox to {c['manager']} for 30 days",
               "Place mail, Drive and Chat under " + ("legal Vault hold" if c["legal_hold"] else "standard Vault retention")],
        "S7": [f"Transfer {inv['recurring_events_organised']} recurring events and {inv['chat_spaces_owned']} Chat spaces"],
        "S8": [f"Reclaim licence: {s}" for s in inv["saas"]],
        "S9": [f"Recover laptop {inv['hardware']['laptop']} and security key {inv['hardware']['security_key']}"],
        "S10": ["Convert to archived user at day 30; delete after the retention period"],
    }
    term = dt.datetime.fromisoformat(c["termination_time"])
    now = dt.datetime.fromisoformat(ob["now"])
    stamp = max(now, term)
    log, results, prev = [], [], "GENESIS"
    for i, sid in enumerate(ids):
        appl, _ = _applicable(sid, c)
        if not appl:
            results.append({"step": sid, "name": pol[sid]["name"], "status": "not applicable", "actions": []})
            continue
        acts = actions_for[sid]
        if c["legal_hold"] and sid == "S10":
            status = "blocked — legal hold " + c.get("legal_hold_reason", "")[-25:].strip(" ().")
        elif c["legal_hold"] and sid == "S9":
            status = "pending — device imaging for Legal before any wipe"
        elif sid == "S10":
            status = "scheduled " + (term + dt.timedelta(days=30)).date().isoformat()
        elif sid == "S9" and not inv["hardware"]["returned"]:
            status = "pending return — remote wipe scheduled if not returned by " + \
                     (term + dt.timedelta(hours=pol[sid]["sla_hours"])).date().isoformat()
        elif not dry_run and now < term:
            status = "scheduled at termination time " + term.isoformat(timespec="minutes") + \
                     " (never before the leaver's last working hour)"
        else:
            status = "planned (dry run)" if dry_run else "done (simulated)"
        res = {"step": sid, "name": pol[sid]["name"], "status": status, "actions": acts}
        if not dry_run and status.startswith("done"):
            ts = (stamp + dt.timedelta(minutes=2 * i)).isoformat(timespec="minutes")
            entry = {"case": cid, "step": sid, "actions": acts, "status": status, "actor": "charon_agent",
                     "timestamp": ts, "prev_hash": prev}
            h = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()[:16]
            entry["hash"], entry["evidence_id"] = h, f"EV-{cid}-{sid}-{h[:6].upper()}"
            prev = h
            log.append(entry)
            res["evidence_id"] = entry["evidence_id"]
        results.append(res)
    return ok(case=cid, name=c["name"], dry_run=dry_run, legal_hold=c["legal_hold"], results=results,
              evidence_log=log, log_head_hash=prev if log else None,
              summary={s: sum(1 for r in results if r["status"].startswith(s))
                       for s in ("planned", "done", "scheduled", "pending", "blocked", "not applicable")},
              simulated=True)


# --- innovation: dream-to-demo (Morpheus) -------------------------------------------------------------------------


def _component(spec: str) -> str:
    kind, _, body = str(spec).partition(":")
    kind, body = kind.strip().lower(), body.strip()
    e = html.escape
    if not body:
        return f"<p>{e(kind)}</p>"
    if kind == "kpi":
        tiles = []
        for part in body.split("|"):
            label, _, val = part.partition("=")
            tiles.append(f"<div class='kpi'><b>{e(val.strip() or '—')}</b><span>{e(label.strip())}</span></div>")
        return f"<div class='kpis'>{''.join(tiles)}</div>"
    if kind == "list":
        return "<ul class='list'>" + "".join(f"<li>{e(x.strip())}</li>" for x in body.split("|")) + "</ul>"
    if kind == "form":
        fields = []
        for f in body.split(","):
            f = f.strip()
            lf = f.lower()
            if "photo" in lf or "upload" in lf or "file" in lf or "document" in lf:
                inp = "<input type='file'>"
            elif "date" in lf:
                inp = "<input type='date'>"
            elif "note" in lf or "description" in lf or "comment" in lf:
                inp = "<textarea rows='2'></textarea>"
            else:
                inp = f"<input placeholder='{e(f)}'>"
            fields.append(f"<label>{e(f)}{inp}</label>")
        return f"<form class='form' onsubmit='return false'>{''.join(fields)}</form>"
    if kind == "table":
        rows = [r.split(",") for r in body.split(";")]
        head = "".join(f"<th>{e(c.strip())}</th>" for c in rows[0])
        body_rows = "".join("<tr>" + "".join(f"<td>{e(c.strip())}</td>" for c in r) + "</tr>" for r in rows[1:])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table>"
    if kind == "chat":
        msgs = []
        for m in body.split("|"):
            who, _, txt = m.partition(":")
            cls = "me" if who.strip().lower() in ("user", "me", "member", "you") else "bot"
            msgs.append(f"<div class='msg {cls}'><small>{e(who.strip())}</small>{e(txt.strip())}</div>")
        return f"<div class='chat'>{''.join(msgs)}</div>"
    if kind in ("map", "chart", "image", "photo"):
        return f"<div class='ph'>{e(kind.title())}: {e(body)}</div>"
    return f"<p>{e(body)}</p>"


@hive_tool(MODULE)
def ops_render_clickable_prototype(title: str, screens: list[dict], accent_color: str = "#13906a") -> dict:
    """Render a self-contained clickable HTML prototype (no external assets) from a screen spec, with journey checks.

    Args:
        title: Prototype title.
        screens: Ordered list of {"id": str, "name": str, "purpose": str, "components": [str],
            "actions": [{"label": str, "goto": screen_id}]}. Component strings: 'kpi: Label=Value | Label=Value',
            'list: a | b | c', 'form: Field, Field, Photo', 'table: Col, Col ; v, v ; v, v',
            'chat: Assistant: text | User: text', 'map: label', 'chart: label', 'text: paragraph'.
        accent_color: Hex brand colour for buttons and the header (e.g. '#13906a').

    Returns:
        The HTML document, prototype id, size, and journey checks (broken links = errors; dead-end or unreachable
        screens and screen-count issues = warnings).
    """
    if not screens:
        return err("screens must not be empty")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent_color):
        return err("accent_color must be a hex colour like #13906a")
    ids = [str(s.get("id", f"s{i}")) for i, s in enumerate(screens, start=1)]
    if len(set(ids)) != len(ids):
        return err("screen ids must be unique")
    checks = []
    for s, sid in zip(screens, ids):
        for a in s.get("actions") or []:
            if a.get("goto") not in ids:
                checks.append({"level": "error", "screen": sid, "issue": f"action '{a.get('label')}' goes to unknown "
                                                                        f"screen {a.get('goto')!r}"})
        if not s.get("actions") and sid != ids[-1]:
            checks.append({"level": "warning", "screen": sid, "issue": "dead end — no action leads forward"})
        if not s.get("components"):
            checks.append({"level": "warning", "screen": sid, "issue": "no components"})
    seen, stack = {ids[0]}, [ids[0]]
    graph = {sid: [a.get("goto") for a in (s.get("actions") or [])] for s, sid in zip(screens, ids)}
    while stack:
        for nxt in graph.get(stack.pop(), []):
            if nxt in ids and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    for sid in ids:
        if sid not in seen:
            checks.append({"level": "warning", "screen": sid, "issue": "not reachable from the first screen via actions"})
    if not 3 <= len(screens) <= 7:
        checks.append({"level": "warning", "screen": None, "issue": f"{len(screens)} screens — aim for 3-7"})
    e = html.escape
    nav = "".join(f"<button class='tab' data-s='{e(sid)}' onclick=\"go('{e(sid)}')\">{e(str(s.get('name', sid)))}"
                  "</button>" for s, sid in zip(screens, ids))
    secs = []
    for s, sid in zip(screens, ids):
        comps = "".join(_component(c) for c in (s.get("components") or []))
        acts = "".join(f"<button class='cta' onclick=\"go('{e(str(a.get('goto')))}')\">{e(str(a.get('label')))}"
                       "</button>" for a in (s.get("actions") or []))
        secs.append(f"<section id='{e(sid)}'><h2>{e(str(s.get('name', sid)))}</h2>"
                    f"<p class='purpose'>{e(str(s.get('purpose', '')))}</p>{comps}<div class='acts'>{acts}</div></section>")
    doc = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{e(title)}</title><style>"
        f":root{{--a:{accent_color}}}*{{box-sizing:border-box}}body{{margin:0;font:15px/1.45 system-ui,sans-serif;"
        "background:#f6f7f8;color:#1d2125}}header{background:var(--a);color:#fff;padding:12px 16px}"
        "header small{opacity:.8}nav{display:flex;gap:6px;flex-wrap:wrap;padding:8px 16px;background:#fff;"
        "border-bottom:1px solid #e3e5e8}.tab{border:0;background:none;padding:6px 10px;border-radius:6px;"
        "cursor:pointer}.tab.on{background:var(--a);color:#fff}main{max-width:880px;margin:0 auto;padding:16px}"
        "section{display:none;background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px #0001}"
        "section.on{display:block}.purpose{color:#5b636b;margin-top:-6px}.kpis{display:grid;"
        "grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}.kpi{border:1px solid #e3e5e8;"
        "border-radius:8px;padding:10px}.kpi b{display:block;font-size:22px}.kpi span{color:#5b636b;font-size:13px}"
        ".list{padding-left:18px}.form{display:grid;gap:10px}.form label{display:grid;gap:4px;font-size:13px}"
        "input,textarea{padding:8px;border:1px solid #cfd3d7;border-radius:6px;font:inherit}"
        "table{width:100%;border-collapse:collapse;margin:8px 0}th,td{text-align:left;padding:6px;"
        "border-bottom:1px solid #eceef0}.chat{display:grid;gap:6px}.msg{padding:8px 10px;border-radius:10px;"
        "max-width:80%;background:#eef1f3}.msg.me{justify-self:end;background:var(--a);color:#fff}"
        ".msg small{display:block;opacity:.7;font-size:11px}.ph{border:2px dashed #cfd3d7;border-radius:8px;"
        "padding:28px;text-align:center;color:#5b636b;margin:8px 0}.acts{display:flex;gap:8px;flex-wrap:wrap;"
        "margin-top:14px}.cta{background:var(--a);color:#fff;border:0;border-radius:6px;padding:9px 14px;"
        "cursor:pointer}footer{text-align:center;color:#8a9199;font-size:12px;padding:16px}"
        f"</style></head><body><header><b>{e(title)}</b><br><small>Clickable prototype · synthetic data</small>"
        f"</header><nav>{nav}</nav><main>{''.join(secs)}</main>"
        "<footer>Prototype generated by Morpheus · Wursta Agent Hive · not a production system</footer>"
        "<script>function go(id){document.querySelectorAll('section').forEach(s=>s.classList.toggle('on',s.id===id));"
        "document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on',t.dataset.s===id));"
        "history.replaceState(null,'','#'+id);}"
        f"go((location.hash||'#{e(ids[0])}').slice(1));</script></body></html>"
    )
    return ok(prototype_id=_sid("PRO", title, *ids), title=title, screens=[{"id": sid, "name": s.get("name")}
                                                                         for s, sid in zip(screens, ids)],
              html=doc, size_bytes=len(doc.encode()), checks=checks,
              passed=not any(c["level"] == "error" for c in checks))


@hive_tool(MODULE)
def ops_draft_sow_outline(concept_title: str, screens: int = 4, integrations: list[str] | None = None,
                          pilot_users: int = 50) -> dict:
    """Draft a SOW outline (phases, deliverables, roles, effort and an estimate range) for a prototyped concept.

    Args:
        concept_title: Name of the concept / product.
        screens: Number of distinct screens or user journeys in the MVP.
        integrations: Systems the MVP must integrate with (e.g. ['Procore', 'Google Workspace']).
        pilot_users: Pilot size (max 50 in the standard pilot phase).

    Returns:
        Phases with weeks, deliverables and role hours; fee estimate range from the illustrative demo rate card
        (+15% contingency); standard assumptions, out-of-scope items and acceptance language.
    """
    ref = fixture("ops_delivery_reference")
    if screens < 1 or screens > 20:
        return err("screens must be between 1 and 20")
    integ = [i for i in (integrations or []) if str(i).strip()]
    sz = ref["sizing"]
    extra = max(0, screens - sz["screens_included"]) * sz["weeks_per_extra_screen"] + len(integ) * sz["weeks_per_integration"]
    phases, total_fee, total_hours = [], 0.0, 0.0
    for p in ref["phases"]:
        weeks = p["base_weeks"] + (extra if p["id"] == "P2" else 0)
        roles = {r: round(h * weeks) for r, h in p["roles_hours_per_week"].items()}
        fee = sum(ref["rate_card_hourly"][r] * h for r, h in roles.items())
        total_fee += fee
        total_hours += sum(roles.values())
        phases.append({"id": p["id"], "name": p["name"], "weeks": weeks, "deliverables": p["deliverables"],
                       "role_hours": roles, "fee_usd": round(fee)})
    low, high = round(total_fee, -3), round(total_fee * (1 + sz["contingency_pct"] / 100), -3)
    notes = []
    if pilot_users > 50:
        notes.append(f"Pilot of {pilot_users} users exceeds the standard 50 — scope a rollout change request.")
    return ok(concept=concept_title, phases=phases, duration_weeks=sum(p["weeks"] for p in phases),
              total_hours=round(total_hours), estimate_usd={"low": low, "high": high},
              integrations=integ, assumptions=ref["standard_assumptions"], out_of_scope=ref["standard_out_of_scope"],
              acceptance="Deliverables are reviewed within 10 business days against the acceptance criteria and are "
                         "deemed accepted if no material non-conformity is reported.",
              notes=notes, disclaimer="Estimate from an illustrative demo rate card — not a quote; run it through Thoth "
                                      "and commercial review before sending.")


# --- innovation: SOW risk (Thoth) ---------------------------------------------------------------------------------


@hive_tool(MODULE)
def ops_sow_clause_scan(sow: str) -> dict:
    """Split a draft SOW into clauses and flag risky or ambiguous language against the legal-playbook rule set.

    Args:
        sow: Sample document key (e.g. 'ops_sow_draft_kestrel') or pasted SOW / clause text. Numbered clauses
            ('1.1 ...') are graded one by one; unnumbered text is treated as a single clause.

    Returns:
        Per clause: section, text, matched rules (risk red/amber/green, category, why, preferred language); missing
        standard sections; counts by risk and a preliminary grade (A-F) for the reviewer to confirm.
    """
    text = doc_text(sow.strip()) if re.fullmatch(r"[a-z0-9_]+", sow.strip()) else sow
    if not text or len(text.strip()) < 20:
        return err("pass a SOW document key (e.g. 'ops_sow_draft_kestrel') or clause text")
    cfg = fixture("ops_sow_rules")
    clauses, section, cur = [], "", None
    for line in text.splitlines():
        if m := re.match(r"^#+\s*(\d+)\.\s*(.+)", line):
            section = f"{m.group(1)}. {m.group(2).strip()}"
            cur = None
            continue
        if m := re.match(r"^\s*(\d+\.\d+)\s+(.+)", line):
            cur = {"clause": m.group(1), "section": section, "text": m.group(2).strip()}
            clauses.append(cur)
        elif cur and line.strip() and not line.startswith("#"):
            cur["text"] += " " + line.strip()
        elif not line.strip():
            cur = None
    if not clauses:
        clauses = [{"clause": "C1", "section": "pasted text", "text": " ".join(text.split())}]
    rank = {"red": 3, "amber": 2, "green": 1}
    for c in clauses:
        low = _norm(c["text"])
        hits = []
        for r in cfg["rules"]:
            if re.search(r["pattern"], low) and not (r.get("unless") and re.search(r["unless"], low)):
                hits.append({k: r[k] for k in ("id", "risk", "category", "why", "preferred")})
        c["flags"] = hits
        c["risk"] = max((h["risk"] for h in hits), key=lambda x: rank[x], default="none")
    full = _norm(text)
    missing = [s["name"] for s in cfg["required_sections"] if not re.search(s["pattern"], full)]
    counts = {k: sum(1 for c in clauses if c["risk"] == k) for k in ("red", "amber", "green", "none")}
    red = counts["red"]
    grade = "F" if red >= 5 else "D" if red >= 3 else "C" if red >= 1 else ("B" if counts["amber"] > 2 else "A")
    return ok(document=text.splitlines()[0].lstrip("# ").strip()[:120], clauses=clauses, counts=counts,
              missing_sections=missing, preliminary_grade=grade,
              grading_rule="F: 5+ red · D: 3-4 red · C: 1-2 red · B: no red, 3+ amber · A: no red, <=2 amber",
              note="Deterministic pre-scan; the reviewer confirms each grade against the SOW Legal Playbook.")


# --- innovation: compliance (Nomos) -------------------------------------------------------------------------------


@hive_tool(MODULE)
def ops_control_lookup(query: str = "", framework: str = "") -> dict:
    """Look up Wursta's internal security controls (synthetic) and their SOC 2 / ISO 27001 reference mapping.

    Args:
        query: Keyword, control id or framework reference, e.g. 'access review', 'offboarding', 'WC-AI-01',
            'CC6.2', 'A.6.5'. Empty lists every control.
        framework: Optional filter — 'soc2' or 'iso27001'.

    Returns:
        Matching controls with owner, frequency, description (our own words), evidence, policy document title and
        the framework identifiers they map to (illustrative mapping).
    """
    ctrls = fixture("ops_controls")["controls"]
    fw = framework.lower().replace(" ", "").replace("-", "").replace("/", "")
    if fw and fw not in ("soc2", "iso27001"):
        return err("framework must be 'soc2' or 'iso27001'")
    q = _norm(query)
    out = []
    for c in ctrls:
        refs = [r.lower() for k, v in c["frameworks"].items() for r in v if not fw or k == fw]
        blob = _norm(" ".join([c["id"], c["name"], c["description"], c["policy"], " ".join(c["evidence"])]))
        if not q:
            score = 1
        elif q in refs or q == c["id"].lower():
            score = 10
        else:
            score = sum(1 for w in _words(q) if w in blob)
        if score and (not fw or c["frameworks"].get(fw)):
            out.append((score, {**c, "frameworks": {k: v for k, v in c["frameworks"].items() if not fw or k == fw}}))
    out.sort(key=lambda x: -x[0])
    return ok(controls=[c for _, c in out[:8]], count=len(out),
              note="Synthetic control set for the demo; framework ids are references only and the mapping is "
                   "illustrative — not an audit opinion or certification claim.")

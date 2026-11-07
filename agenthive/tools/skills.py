"""wco-ge-skills — the foundational skill library.

Atomic, reusable functions that underpin higher-level agents. Each skill does one job with the cheapest model that
can do it (Flash-Lite with a JSON schema) or with no model at all. The same functions are exposed to external
clients (Gemini Enterprise, other MCP hosts) by agenthive/mcp_server.py.
"""
from __future__ import annotations

import re

from ._base import doc_text, err, fixture, hive_tool, llm_json, offline, ok

_RISK_TERMS = {
    "dissatisfaction": ["frustrated", "disappointed", "unacceptable", "not happy", "concerned", "escalate", "again?"],
    "scope_creep": ["also add", "one more thing", "while you're at it", "out of scope", "additional", "can we include"],
    "disengagement": ["no time", "skip", "reschedule", "busy", "later", "not a priority", "whatever"],
    "timeline_risk": ["delay", "slip", "behind", "blocked", "waiting on", "deadline"],
}


def _resolve_text(text_or_doc: str) -> str:
    """Accept raw text or the key of a sample document (e.g. 'transcript_steering_q3')."""
    key = text_or_doc.strip()
    if re.fullmatch(r"[a-z0-9_]+", key) and (d := doc_text(key)):
        return d
    return text_or_doc


@hive_tool("skills", kind="skill")
def detect_meeting_sentiment_risk(transcript: str) -> dict:
    """Score a meeting transcript for client dissatisfaction, scope creep, disengagement and timeline risk.

    Args:
        transcript: Full transcript text, or the key of a sample document such as 'transcript_steering_q3'.

    Returns:
        Overall risk level, per-category scores (0-1) with quoted evidence, and a suggested PM alert.
    """
    text = _resolve_text(transcript)
    if len(text) < 40:
        return err("transcript too short to analyse")
    lowered = text.lower()
    lexicon = {k: [t for t in terms if t in lowered] for k, terms in _RISK_TERMS.items()}
    if offline():
        score = {k: min(1.0, len(v) / 3) for k, v in lexicon.items()}
        top = max(score.values())
        return ok(risk_level="high" if top > 0.6 else "medium" if top > 0 else "low", scores=score,
                  lexicon_hits=lexicon)
    schema = {
        "type": "object",
        "properties": {
            "overall_risk": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            "signals": {"type": "array", "items": {"type": "object", "properties": {
                "category": {"type": "string",
                             "enum": ["dissatisfaction", "scope_creep", "disengagement", "timeline_risk", "budget"]},
                "score": {"type": "number"}, "speaker": {"type": "string"}, "evidence_quote": {"type": "string"}},
                "required": ["category", "score", "evidence_quote"]}},
            "sentiment_trend": {"type": "string"},
            "pm_alert": {"type": "string"},
        },
        "required": ["overall_risk", "signals", "pm_alert"],
    }
    res = llm_json("You audit client meetings for a cloud consultancy. Identify risk signals with verbatim evidence "
                   "quotes (max 20 words each). Draft a 3-sentence alert for the project manager.\n\nTRANSCRIPT:\n"
                   + text[:30000], schema)
    if "_error" in res:
        return err(res["_error"], lexicon_hits=lexicon)
    return ok(**res, lexicon_hits=lexicon, model_tier="lite")


@hive_tool("skills", kind="skill")
def extract_meeting_structured_data(notes: str) -> dict:
    """Extract action items (owner, task, due date), decisions, open questions and risks from meeting notes.

    Args:
        notes: Meeting notes or transcript text, or the key of a sample document.

    Returns:
        Structured action items, decisions, open questions and risks ready to create tasks from.
    """
    text = _resolve_text(notes)
    if len(text) < 20:
        return err("notes too short")
    if offline():
        return ok(action_items=[], decisions=[], open_questions=[], risks=[])
    schema = {
        "type": "object",
        "properties": {
            "action_items": {"type": "array", "items": {"type": "object", "properties": {
                "owner": {"type": "string"}, "task": {"type": "string"}, "due": {"type": "string"},
                "priority": {"type": "string", "enum": ["P1", "P2", "P3"]}}, "required": ["owner", "task"]}},
            "decisions": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["action_items", "decisions"],
    }
    res = llm_json("Extract structured data from these meeting notes. Use 'unassigned' when no owner is stated and "
                   "ISO dates when a due date can be inferred (else 'TBD').\n\nNOTES:\n" + text[:30000], schema)
    return err(res["_error"]) if "_error" in res else ok(**res, model_tier="lite")


@hive_tool("skills", kind="skill")
def extract_video_to_okf(video: str) -> dict:
    """Deconstruct a recorded meeting or video into an Open Knowledge Framework (OKF) record.

    Args:
        video: A gs:// URI or public YouTube URL of the recording, or the key of a sample transcript.

    Returns:
        OKF record: title, summary, chapters with timestamps, entities, decisions, reusable Q&A pairs and tags.
    """
    from google.genai import types

    parts = None
    source = video.strip()
    if source.startswith("gs://") or "youtube.com" in source or "youtu.be" in source:
        mime = "video/mp4" if not source.endswith(".mp3") else "audio/mpeg"
        parts = [types.Part(file_data=types.FileData(file_uri=source, mime_type=mime))]
        body = "Analyse the attached recording."
    else:
        body = "TRANSCRIPT (with [mm:ss] timestamps where available):\n" + _resolve_text(source)[:40000]
    if offline():
        return ok(title="offline", chapters=[], qa=[])
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"}, "summary": {"type": "string"},
            "chapters": {"type": "array", "items": {"type": "object", "properties": {
                "start": {"type": "string"}, "title": {"type": "string"}, "key_points": {
                    "type": "array", "items": {"type": "string"}}}, "required": ["start", "title"]}},
            "entities": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "type": {"type": "string"}}}},
            "decisions": {"type": "array", "items": {"type": "string"}},
            "qa": {"type": "array", "items": {"type": "object", "properties": {
                "question": {"type": "string"}, "answer": {"type": "string"}}}},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "summary", "chapters", "qa", "tags"],
    }
    res = llm_json("Convert this recording into an Open Knowledge Framework record that makes it searchable: "
                   "chapters with start timestamps, entities, decisions and 3-6 reusable Q&A pairs.\n\n" + body,
                   schema, tier="flash" if parts else "lite", parts=parts)
    return err(res["_error"]) if "_error" in res else ok(okf=res, source=source[:200])


@hive_tool("skills", kind="skill")
def drive_organization(folder: str = "shared_drive_sales") -> dict:
    """Analyse a messy Google Drive folder and propose a clean taxonomy with file moves, renames and archives.

    Args:
        folder: Sample folder key (e.g. 'shared_drive_sales'). Runs as a dry run — nothing is moved.

    Returns:
        Proposed folder tree, per-file actions (move / rename / archive / dedupe) and summary counts.
    """
    data = fixture("drive_folders")
    files = data.get(folder)
    if files is None:
        return err(f"unknown folder {folder!r}", available=sorted(data))
    rules = [
        (r"(?i)(sow|statement of work|msa|contract)", "01 Contracts"),
        (r"(?i)(proposal|rfp|quote|pricing)", "02 Proposals"),
        (r"(?i)(deck|pitch|slides|\.pptx)", "03 Decks"),
        (r"(?i)(invoice|po |purchase order|receipt)", "04 Finance"),
        (r"(?i)(notes|minutes|transcript|meeting)", "05 Meetings"),
        (r"(?i)(case study|reference|testimonial)", "06 Case studies"),
    ]
    seen, actions = {}, []
    for f in files:
        name = f["name"]
        base = re.sub(r"(?i)( \(\d+\)| - copy| copy|_final|_v\d+|_old)", "", name.rsplit(".", 1)[0]).strip().lower()
        if base in seen:
            actions.append({"file": name, "action": "dedupe", "keep": seen[base]})
            continue
        seen[base] = name
        if f.get("modified", "2026") < "2024-01-01":
            actions.append({"file": name, "action": "archive", "to": "99 Archive", "reason": "not modified since 2023"})
            continue
        target = next((t for pat, t in rules if re.search(pat, name)), "07 Working files")
        new_name = re.sub(r"(?i)( \(\d+\)| - copy|_final+|_v\d+)", "", name)
        act = {"file": name, "action": "move", "to": target}
        if new_name != name:
            act["rename_to"] = new_name
        actions.append(act)
    summary = {k: sum(1 for a in actions if a["action"] == k) for k in ("move", "archive", "dedupe")}
    tree = sorted({a.get("to") for a in actions if a.get("to")})
    return ok(folder=folder, files_scanned=len(files), proposed_tree=tree, actions=actions, summary=summary,
              dry_run=True)


@hive_tool("skills", kind="skill")
def partner_advantage_cataloger(batch: str = "partner_portal_week45") -> dict:
    """Grade new Google Partner Advantage content for AI-ingestion readiness and tag it for the team.

    Args:
        batch: Sample content batch key (e.g. 'partner_portal_week45').

    Returns:
        Per-file readiness score (0-100), blocking issues, tags (product, audience, motion) and a team digest.
    """
    data = fixture("partner_content")
    items = data.get(batch)
    if items is None:
        return err(f"unknown batch {batch!r}", available=sorted(data))
    graded = []
    for it in items:
        score, issues = 100, []
        if it.get("format") in ("scanned_pdf", "image"):
            score -= 35
            issues.append("needs OCR (scanned)")
        if it.get("pages", 0) > 80:
            score -= 15
            issues.append("very long — split by chapter")
        if not it.get("has_text_layer", True):
            score -= 20
            issues.append("no text layer")
        if it.get("confidential"):
            score -= 30
            issues.append("partner-confidential — restrict ACLs before indexing")
        if it.get("age_days", 0) > 365:
            score -= 10
            issues.append("older than 12 months — verify currency")
        graded.append({**it, "readiness": max(score, 0), "issues": issues,
                       "verdict": "ingest" if score >= 70 else "fix first" if score >= 40 else "exclude"})
    graded.sort(key=lambda g: -g["readiness"])
    return ok(batch=batch, items=graded,
              counts={v: sum(1 for g in graded if g["verdict"] == v) for v in ("ingest", "fix first", "exclude")})


@hive_tool("skills", kind="skill")
def ocr_document_text(document: str) -> dict:
    """Extract text and key fields from a scanned document or image.

    Args:
        document: gs:// URI of a PDF/PNG/JPG, or the key of a sample scanned document (e.g. 'scan_permit_form').

    Returns:
        Extracted plain text, detected document type, key-value fields and a confidence note.
    """
    from google.genai import types

    src = document.strip()
    if src.startswith("gs://"):
        mime = "application/pdf" if src.lower().endswith(".pdf") else "image/png" if src.lower().endswith(".png") \
            else "image/jpeg"
        parts = [types.Part(file_data=types.FileData(file_uri=src, mime_type=mime))]
        prompt = "OCR the attached document."
    else:
        text = doc_text(src)
        if text is None:
            return err("pass a gs:// URI or a sample document key")
        parts, prompt = None, "This is the raw OCR layer of a scanned document (may contain noise):\n" + text
    if offline():
        return ok(text="(offline)", fields={})
    schema = {"type": "object", "properties": {
        "document_type": {"type": "string"}, "text": {"type": "string"},
        "fields": {"type": "array", "items": {"type": "object", "properties": {
            "key": {"type": "string"}, "value": {"type": "string"}}}},
        "quality_note": {"type": "string"}}, "required": ["document_type", "text", "fields"]}
    res = llm_json(prompt + "\nReturn clean text, the document type and key fields.", schema, parts=parts)
    return err(res["_error"]) if "_error" in res else ok(**res)


@hive_tool("skills", kind="skill")
def route_incoming_email(subject: str, body: str, sender: str = "") -> dict:
    """Classify an incoming email by intent and route it to the right queue with a priority and draft reply.

    Args:
        subject: Email subject line.
        body: Email body text.
        sender: Sender address (optional; used for VIP / domain rules).

    Returns:
        Intent (support / sales / invoice / legal / hr / spam / other), priority, queue, SLA and a short draft reply.
    """
    vip_domains = {"bigclient.example", "board.example"}
    domain = sender.split("@")[-1].lower() if "@" in sender else ""
    if offline():
        return ok(intent="other", queue="triage", priority="P3")
    schema = {"type": "object", "properties": {
        "intent": {"type": "string", "enum": ["support", "sales", "invoice", "legal", "hr", "spam", "other"]},
        "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
        "queue": {"type": "string"}, "confidence": {"type": "number"},
        "summary": {"type": "string"}, "draft_reply": {"type": "string"}},
        "required": ["intent", "priority", "queue", "summary"]}
    res = llm_json(f"Route this email for a cloud consultancy.\nFROM: {sender}\nSUBJECT: {subject}\n\n{body[:8000]}",
                   schema)
    if "_error" in res:
        return err(res["_error"])
    if domain in vip_domains:
        res["priority"], res["vip"] = "P1", True
    res["sla_hours"] = {"P1": 4, "P2": 24, "P3": 72}[res.get("priority", "P3")]
    return ok(**res, model_tier="lite")

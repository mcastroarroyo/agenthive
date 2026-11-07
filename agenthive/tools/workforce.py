"""Agent Workforce realm tools — Wursta's AI staffing marketplace ("Hire an AI expert. Get a finished, branded
document. Pay per job.").

The demo customer is the fictional Kitewing Software (see the SMB realm); its marketing, sales and operations teams hire
Workforce specialists. Tools cover the marketplace roster, brief scoping and the upfront estimate (illustrative pricing,
not final), Brand Intelligence (learn a brand profile from guidelines, rule-based brand checks), QA claim extraction
against approved facts, deliverable templates, specialist helpers (SEO audit and draft checks, social calendar slots,
SOP step checks, market sizing) and the Document Studio renderer.

`wf_render_document` builds a REAL file in memory (python-docx / python-pptx / openpyxl, imported lazily) styled with
the brand profile and attaches it to the ADK session state as
    state["hive_file:<file_id>"] = {"name": "<slug>.docx", "mime": "<mime>", "size": <bytes>, "b64": "<base64>"}
so the Hive UI can offer the download. Everything else is deterministic over fixtures/wf_*.json (synthetic).
"""
from __future__ import annotations

import base64
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
import unicodedata
from typing import Any

from ._base import doc_text, err, fixture, hive_tool, ok

try:  # ADK injects the context; the web image builds the catalog without ADK installed
    from google.adk.tools import ToolContext
except ImportError:  # pragma: no cover
    ToolContext = Any  # type: ignore[misc,assignment]

TODAY = dt.date(2026, 11, 6)   # the demo's fixed "today" keeps every answer reproducible
MAX_FILE_BYTES = 1_000_000
FORMATS = ("docx", "pptx", "xlsx", "md", "csv")
MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "md": "text/markdown",
    "csv": "text/csv",
}
_KEY = re.compile(r"^[a-z][a-z0-9_]{3,79}$")


# --- helpers ------------------------------------------------------------------------------------------------------


def _norm(s: Any) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("&", " and ")).strip()


def _slug(s: str, n: int = 60) -> str:
    return re.sub(r"-+", "-", _norm(s).replace(" ", "-"))[:n].strip("-") or "document"


def _h(*parts: Any, n: int = 8) -> str:
    return hashlib.sha1("|".join(json.dumps(p, sort_keys=True, default=str) for p in parts).encode()).hexdigest()[:n]


def _text(value: str) -> tuple[str, str | None]:
    """Resolve a sample-document key to its text; otherwise return the value itself."""
    v = (value or "").strip()
    if _KEY.match(v):
        t = doc_text(v)
        if t is not None:
            return t, v
    return v, None


def _state(tool_context: Any) -> Any:
    return getattr(tool_context, "state", None) if tool_context is not None else None


def _state_get(st: Any, key: str) -> Any:
    try:
        return st.get(key) if st is not None else None
    except Exception:  # noqa: BLE001 — a foreign state object must never break a tool
        return None


def _brand_id(name: str) -> str:
    return "BRD-" + hashlib.sha1(_norm(name).encode()).hexdigest()[:6].upper()


def _profiles() -> list[dict]:
    return fixture("wf_brand_profiles")["profiles"]


def _brand(brand: str, tool_context: Any = None) -> dict | None:
    """Brand profile by id, name or alias: learned in this session first, then the brand library, '' = house style."""
    b = (brand or "").strip()
    profiles = _profiles()
    if _norm(b) in ("", "house", "house style", "default", "none", "agent workforce", "no brand"):
        return next(p for p in profiles if p["brand_id"] == "BRD-HOUSE")
    st = _state(tool_context)
    learned = _state_get(st, f"wf_brand:{b.upper()}") if b.upper().startswith("BRD-") else None
    if learned:
        return learned
    q = _norm(b)
    for p in profiles:
        if b.upper() == p["brand_id"] or q == _norm(p["name"]) or q in [_norm(a) for a in p.get("aliases", [])]:
            return p
    for p in profiles:
        if q and (q in _norm(p["name"]) or _norm(p["name"]).split()[0] == q.split()[0]):
            return p
    learned = _state_get(st, f"wf_brand:{_brand_id(b)}")
    return learned or None


def _customer(name: str) -> dict | None:
    q = _norm(name)
    for c in fixture("wf_customer_workspace")["customers"]:
        if q in (_norm(c["name"]), _norm(c["id"])) or q in [_norm(a) for a in c.get("aliases", [])]:
            return c
    return None


def _sentences(text: str) -> list[str]:
    out = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s or re.match(r"^\|?[\s:\-|]+\|?$", s):
            continue
        s = re.sub(r"^(#{1,6}\s+|[-*•]\s+|\d+[.)]\s+|>\s*)", "", s)
        s = s.replace("**", "").replace("__", "")
        if s.startswith("|"):
            s = " ".join(c.strip() for c in s.strip("|").split("|"))
        parts: list[str] = []
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", s):
            if parts and _ABBR.search(parts[-1]):
                parts[-1] += " " + part
            elif part.strip():
                parts.append(part.strip())
        out += parts
    return out


_ABBR = re.compile(r"(\b(?:U\.S|U\.K|e\.g|i\.e|Inc|Co|Corp|Ltd|Dr|Mr|Ms|Mrs|St|vs|No|approx|Jan|Feb|Mar|Apr|Jun|Jul|"
                   r"Aug|Sep|Sept|Oct|Nov|Dec)\.)$")


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(1, n)


def _readability(text: str) -> dict:
    sents = [s for s in _sentences(text) if len(s.split()) >= 3]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", " ".join(sents))
    if not sents or not words:
        return {"words": len(words), "sentences": len(sents), "avg_sentence_words": 0, "flesch_reading_ease": None}
    wps = len(words) / len(sents)
    spw = sum(_syllables(w) for w in words) / len(words)
    return {"words": len(re.findall(r"\S+", text)), "sentences": len(sents), "avg_sentence_words": round(wps, 1),
            "flesch_reading_ease": round(206.835 - 1.015 * wps - 84.6 * spw, 1)}


_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
_NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")


def _numbers(text: str) -> set[float]:
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)                 # ISO dates
    t = re.sub(r"\b(19|20)\d{2}\b", " ", t)                          # years
    out = set()
    for m in _NUM.findall(t):
        v = m.strip("$%").replace(",", "")
        try:
            out.add(float(v))
        except ValueError:
            pass
    return out


def _variants(name: str) -> list[str]:
    """Ways a company name shows up in copy: full, '&' <-> 'and', distinctive first word(s)."""
    v = [name, name.replace("&", "and")]
    toks = name.split()
    if len(toks) > 1:
        if toks[1] in ("&", "and") and len(toks) > 2:
            v += [" ".join(toks[:3]), " ".join(toks[:3]).replace("&", "and")]
        elif len(toks[0]) >= 7:
            v.append(toks[0])
        else:
            v.append(" ".join(toks[:2]))
    return list(dict.fromkeys(v))


def _find_name(text: str, name: str) -> str | None:
    for var in _variants(name):
        flags = 0 if " " not in var else re.I
        if re.search(r"(?<![A-Za-z])" + re.escape(var) + r"(?![A-Za-z])", text, flags):
            return var
    return None


# --- marketplace --------------------------------------------------------------------------------------------------


@hive_tool("workforce")
def wf_marketplace(department: str = "", need: str = "") -> dict:
    """Browse the Agent Workforce marketplace: 10 departments, 70 specialists, what each produces and who to hire.

    Args:
        department: Optional department name or id (e.g. 'Marketing', 'social_media') for that department's detail.
        need: Optional plain-English need (e.g. 'a LinkedIn calendar and a client proposal') for ranked recommendations.

    Returns:
        Departments with agent counts, the named example specialists and typical outputs; for a need, the best
        matching departments with the hive specialist to hire, what it delivers and its default file format; the two
        delivery modes; and a note when the need is something Agent Workforce does not do.
    """
    mk = fixture("wf_marketplace")
    depts = mk["departments"]
    specs = {s["agent_id"]: s for s in mk["hive_specialists"]}

    def brief(d: dict) -> dict:
        return {"department": d["name"], "agents": d["agents"], "example_specialists": d["examples"],
                "example_outputs": d["outputs"] or "see the full roster in the product",
                "experimental": d.get("experimental", False) or None,
                "hire_in_this_hive": [{"agent": specs[a]["name"], "agent_id": a, "delivers": specs[a]["delivers"],
                                       "default_format": specs[a]["default_format"]} for a in d["hive_prototypes"]]
                or None}

    modes = [f"{m['name']}: {m['how']}" for m in mk["delivery_modes"]]
    if department.strip():
        q = _norm(department)
        d = next((x for x in depts if q in (_norm(x["id"]), _norm(x["name"]))), None) or \
            next((x for x in depts if q in _norm(x["name"]) or _norm(x["name"]) in q), None)
        if not d:
            return err(f"no department matching {department!r}", departments=[x["name"] for x in depts])
        return ok(**brief(d), roster_note=mk["roster_note"], delivery_modes=modes)
    if need.strip():
        low = need.lower()
        not_for = [n["why"] for n in mk["not_for"] if any(a in low for a in n["ask"])]
        ranked = []
        for d in depts:
            hits = [k for k in d["keywords"] if re.search(r"(?<![a-z])" + re.escape(k), low)]
            if hits:
                ranked.append((len(hits), d, hits))
        ranked.sort(key=lambda x: -x[0])
        recs = [{**brief(d), "matched": hits} for _, d, hits in ranked[:3]]
        return ok(need=need, recommendations=recs, not_what_we_do=not_for or None,
                  hint=None if recs else "No department matched — ask what the finished document should be.",
                  total_agents=mk["total_agents"], roster_note=mk["roster_note"], delivery_modes=modes)
    return ok(pitch=mk["pitch"], total_agents=mk["total_agents"],
              departments=[{"department": d["name"], "agents": d["agents"], "examples": d["examples"],
                            "outputs": d["outputs"] or None, "experimental": d.get("experimental") or None,
                            "in_this_hive": [specs[a]["name"] for a in d["hive_prototypes"]] or None} for d in depts],
              journey=[f"{j['step']} {j['name']} — {j['what']}" for j in mk["journey"]],
              capabilities=[c["name"] for c in mk["capabilities"]], delivery_modes=modes,
              delivery_notes=mk["delivery_notes"], roster_note=mk["roster_note"])


# --- brief & estimate ---------------------------------------------------------------------------------------------

_FORMAT_WORDS = [
    ("pptx", r"\.pptx|powerpoint|\bdeck\b|\bslides?\b|presentation"),
    ("xlsx", r"\.xlsx|excel|spreadsheet|workbook"),
    ("csv", r"\.csv|\bcsv\b"),
    ("pdf", r"\.pdf|\bpdf\b"),
    ("md", r"\.md\b|markdown"),
    ("docx", r"\.docx|\bword (doc|document|file)\b|\bms word\b|google doc"),
]
_QTY = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "a": 1, "an": 1}


def _scope(text: str) -> str:
    """The part of a brief that states the deliverable (a 'Deliverable:' line when present), without asides."""
    low = text.lower()
    m = re.search(r"^\s*(?:[-*]\s*)?\**deliverables?\**\s*[:\-—]\s*(.+?)(?:\n\s*\n|\n\s*\*\*|\Z)", low, re.M | re.S)
    return re.sub(r"\([^)]*\)", " ", m.group(1) if m else low)


def _detect_format(text: str) -> str:
    """Earliest file-format mention in the deliverable scope, else in the whole brief."""
    for t in (_scope(text), text.lower()):
        hits = [(m.start(), f) for f, rx in _FORMAT_WORDS for m in [re.search(rx, t)] if m]
        if hits:
            return min(hits)[1]
    return ""


def _detect_kinds(text: str) -> list[tuple[str, int]]:
    tpl = fixture("wf_templates")["templates"]
    scope = _scope(text)
    found = []
    for kind, t in tpl.items():
        for k in t["keywords"]:
            for mm in re.finditer(r"(?<![a-z])" + re.escape(k), scope):
                found.append((mm.end() - mm.start(), mm.start(), mm.end(), kind))
    found.sort(key=lambda x: (-x[0], x[1]))
    taken: list[tuple[int, int]] = []
    kinds: dict[str, int] = {}
    for _, a, b, kind in found:
        if any(a < y and x < b for x, y in taken):
            continue
        taken.append((a, b))
        before = scope[max(0, a - 24):a].split()
        qty = 1
        for w in reversed(before[-3:]):
            if w.isdigit():
                qty = min(5, max(1, int(w)))
                break
            if w in _QTY:
                qty = _QTY[w]
                break
        kinds[kind] = max(kinds.get(kind, 0), qty)
    return list(kinds.items())


@hive_tool("workforce")
def wf_estimate_job(brief: str, deliverables: list[str] | None = None, output_format: str = "", priority: str = "",
                    customer: str = "Kitewing Software") -> dict:
    """Scope a plain-English job brief and estimate its cost upfront for every priority tier (illustrative pricing).

    Args:
        brief: The brief in plain English, or a sample brief key such as 'wf_brief_proposal_alderbrook'.
        deliverables: Optional deliverable kinds to use instead of detecting them: seo_audit, blog_brief, blog_post,
            content_calendar, proposal, pitch_deck, sop, gtm_plan, whitepaper, press_release, one_pager. Repeat a
            kind for several copies (e.g. ['blog_brief', 'blog_brief']).
        output_format: Optional file format the customer asked for: docx, pptx, xlsx, pdf, csv or md.
        priority: Optional tier: P1 (urgent), P2 (standard) or P3 (economy). Detected from the brief when empty.
        customer: Customer account whose credit balance is checked.

    Returns:
        Job id, scoped deliverables (kind, format, specialists, outline), billable agents, the estimate per tier
        (per-agent rate, subtotal, 20% buffer, credits to reserve, turnaround), the recommended tier, the credit
        balance check and the assumptions. Pricing is illustrative, not final.
    """
    text, key = _text(brief)
    if len(text.strip()) < (3 if deliverables else 15):
        return err("brief too short — describe the finished document you need")
    tpl = fixture("wf_templates")["templates"]
    pr = fixture("wf_pricing")
    if deliverables:
        counts: dict[str, int] = {}
        for d in deliverables:
            k = _norm(d).replace(" ", "_")
            k = k if k in tpl else next((x for x in tpl if _norm(tpl[x]["name"]) == _norm(d)), "")
            if not k:
                return err(f"unknown deliverable {d!r}", kinds=list(tpl))
            counts[k] = counts.get(k, 0) + 1
        kinds = list(counts.items())
    else:
        kinds = _detect_kinds(text)
    if not kinds:
        return err("could not tell which deliverable the brief asks for — pass deliverables=[...]", kinds=list(tpl))
    low = text.lower()
    fmt_req = (output_format or "").lower().strip(". ") or _detect_format(text)
    kd = dict(kinds)
    if fmt_req == "pptx" and "proposal" in kd:          # "the proposal as a deck" is a pitch deck
        kd["pitch_deck"] = max(kd.pop("proposal"), kd.get("pitch_deck", 0))
        kinds = list(kd.items())
    notes, items = [], []
    for kind, qty in kinds:
        t = tpl[kind]
        fmt = fmt_req if fmt_req in t["formats"] else t["default_format"]
        if fmt_req and fmt_req not in t["formats"]:
            notes.append(f"{t['name']}: {fmt_req} is not a {t['name'].lower()} format here; delivering .{fmt}.")
        if fmt == "pdf":
            notes.append("PDF export runs in the Agent Workforce product; this prototype delivers .docx.")
            fmt = "docx"
        names = [next(s["name"] for s in fixture("wf_marketplace")["hive_specialists"] if s["agent_id"] == a)
                 for a in t["specialists"]]
        items.append({"kind": kind, "deliverable": t["name"], "quantity": qty, "format": fmt,
                      "specialists": names, "specialist_ids": t["specialists"], "length": t["length"],
                      "outline": [s.split(" — ")[0] for s in t["sections"]]})
    agents = sum(len(i["specialist_ids"]) * i["quantity"] for i in items)
    tier = (priority or "").upper().strip()
    if tier not in ("P1", "P2", "P3"):
        tier = "P2"
        for t_, words in pr["urgency_words"].items():
            if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low) for w in words):
                tier = t_
                break
        why = "detected from the brief" if tier != "P2" else "default (no urgency stated)"
    else:
        why = "requested"
    est = []
    for t_ in pr["tiers"]:
        sub = round(t_["per_agent_usd"] * agents, 2)
        buf = round(sub * pr["buffer_pct"] / 100, 2)
        est.append({"tier": t_["id"], "name": t_["name"], "mode": t_["mode"], "per_agent_usd": t_["per_agent_usd"],
                    "subtotal_usd": sub, "buffer_usd": buf, "reserve_credits": round(sub + buf, 2),
                    "turnaround": t_["turnaround"]})
    chosen = next(e for e in est if e["tier"] == tier)
    cust = _customer(customer)
    credits = None
    if cust:
        bal = cust["credits"]["balance"]
        after = round(bal - chosen["reserve_credits"], 2)
        credits = {"customer": cust["name"], "balance": bal, "reserve": chosen["reserve_credits"],
                   "balance_after_reserve": after, "enough": after >= 0,
                   "top_up_needed": None if after >= 0 else math.ceil(-after)}
    title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.strip()), "")[:100]
    prof = _brand(cust["brand_profile"]) if cust else None
    assumptions = [
        f"Brand: {prof['name']} profile ({prof['brand_id']}) applied to every file." if prof else
        "Brand: house style (no brand profile on file).",
        "Facts limited to the brief and the customer's approved brand facts; public facts are fact-checked.",
        "Orchestration, Brand Intelligence, QA & fact-check and rendering are included (not billed per agent).",
        pr["billable_rule"], pr["buffer_rule"],
    ]
    return ok(job_id="WFJ-" + str(10000 + int(_h(text, kinds, fmt_req), 16) % 90000), brief_key=key, title=title,
              deliverables=items, billable_agents=agents, estimate=est, recommended_tier=tier,
              recommended_why=why, credits=credits, notes=notes or None, assumptions=assumptions,
              pricing=f"{pr['label']} — per-agent rates P1 $7.50, P2 $5.00, P3 $2.50; 1 credit = $1",
              approval="Demo: the customer approves the recommended tier; credits are reserved (simulated).")


# --- brand intelligence -------------------------------------------------------------------------------------------


def _md_sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    cur = "_intro"
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+)", line)
        if m:
            cur = _norm(m.group(1))
            out[cur] = ""
            continue
        out[cur] = out.get(cur, "") + line + "\n"
    return out


def _md_tables(body: str) -> list[list[list[str]]]:
    tables, cur = [], []
    for line in (body or "").splitlines() + [""]:
        s = line.strip()
        if s.startswith("|"):
            if not re.match(r"^\|[\s:\-|]+\|?$", s):
                cur.append([c.strip() for c in s.strip("|").split("|")])
        elif cur:
            tables.append(cur)
            cur = []
    return tables


def _section(secs: dict[str, str], *words: str) -> str:
    """Body of the first section whose heading contains a word — words are tried in priority order."""
    for w in words:
        for k, v in secs.items():
            if w in k:
                return v
    return ""


def _bullet(body: str, label: str) -> str:
    m = re.search(r"^\s*[-*]?\s*" + re.escape(label) + r"\s*:\s*(.+)$", body, re.M | re.I)
    return m.group(1).strip() if m else ""


def _split_list(s: str) -> list[str]:
    return [x.strip(" .\"'") for x in re.split(r",\s*", s or "") if x.strip(" .")]


def _parse_guidelines(text: str, brand_name: str = "") -> dict:
    """Deterministic parser for brand guidelines written in markdown (sections, tables, labelled bullets)."""
    secs = _md_sections(text)
    first = next((ln for ln in text.splitlines() if ln.startswith("# ")), "")
    ess = _section(secs, "essential", "brand basics")
    name = brand_name.strip() or re.sub(r"\s*\(.*?\)", "", _bullet(ess, "Company name")).strip() \
        or re.split(r"\s+[—–-]\s+", first.lstrip("# "))[0].strip()
    voice_sec = _section(secs, "voice", "tone")
    voice = next((p.strip() for p in voice_sec.split("\n\n") if p.strip() and not p.strip().startswith(("|", "Tone"))),
                 "")
    rules_sec = _section(secs, "writing rules", "style rules", "writing")
    rules = [re.sub(r"^\d+[.)]\s*", "", ln.strip()) for ln in rules_sec.splitlines() if re.match(r"^\s*\d+[.)]\s", ln)]
    rules_txt = " ".join(rules).lower()
    words_sec = _section(secs, "words we avoid", "banned", "avoid")
    banned = _split_list(_bullet(words_sec, "Never use") or _bullet(text, "Never use"))
    repl = {r[0].lower(): r[1] for t in _md_tables(words_sec) for r in t[1:] if len(r) >= 2}
    products = []
    for t in _md_tables(_section(secs, "product names", "naming")):
        for r in t[1:]:
            if len(r) >= 2:
                allowed = [r[0], *re.findall(r"\"([^\"]+)\"", r[1])]
                products.append({"name": r[0], "rule": r[1], "never": _split_list(r[2]) if len(r) > 2 else [],
                                 "allowed": list(dict.fromkeys(allowed))})
    cn = _section(secs, "customer names", "claims", "names")
    anonym = []
    for item in _split_list(_bullet(cn, "Anonymised only") or _bullet(cn, "Anonymized only")):
        m = re.match(r"(.+?)\s*\(write\s+\"?([^\")]+)\"?\)", item)
        anonym.append({"name": m.group(1).strip(), "use": m.group(2).strip()} if m else {"name": item, "use": ""})
    names = {"approved": _split_list(_bullet(cn, "Approved for public use")), "anonymised": anonym,
             "never": _split_list(_bullet(cn, "Never mention")),
             "prospects": _split_list(re.sub(r"^\(.*?\)\s*", "", _bullet(cn, "Prospects (never named in public content)")
                                             or _bullet(cn, "Prospects"))),
             "competitors": _split_list(_bullet(cn, "Competitors (no named comparisons in public content)")
                                        or _bullet(cn, "Competitors"))}
    facts_sec = _section(secs, "approved facts", "boilerplate", "facts")
    boiler = next((ln.split(":", 1)[1].strip() for ln in facts_sec.splitlines() if ln.startswith("About ")), "")
    ftables = _md_tables(facts_sec)
    facts = [{"fact": r[0], "approved": r[1]} for r in (ftables[0][1:] if ftables else []) if len(r) >= 2]
    results = [{"customer": r[0], "result": r[1]} for r in (ftables[1][1:] if len(ftables) > 1 else []) if len(r) >= 2]
    social_sec = _section(secs, "social")
    pillars = []
    for item in _split_list(_bullet(social_sec, "Content pillars")):
        m = re.match(r"(.+?)\s+(\d+)%", item)
        if m:
            pillars.append({"name": m.group(1).strip(), "share_pct": int(m.group(2))})
    social = {"hashtags": [h for h in _split_list(_bullet(social_sec, "Approved hashtags")) if h.startswith("#")],
              "max_hashtags": int(re.search(r"at most (\d+)", _bullet(social_sec, "Hashtags") or "at most 3").group(1)),
              "max_emojis": int(re.search(r"at most (\d+)", _bullet(social_sec, "Emojis") or "at most 2").group(1)),
              "pillars": pillars, "cadence": _bullet(social_sec, "Cadence")}
    fonts: dict[str, dict] = {}
    for t in _md_tables(_section(secs, "typograph", "fonts")):
        for r in t[1:]:
            role = _norm(r[0])
            key = {"headings": "heading", "heading": "heading", "body": "body", "slide titles": "slide_title",
                   "slide body": "slide_body"}.get(role)
            if key and len(r) >= 2:
                fonts[key] = {"name": r[1], "fallback": r[2] if len(r) > 2 else "", "spec": r[3] if len(r) > 3 else ""}
    colours: dict[str, dict] = {}
    for t in _md_tables(_section(secs, "colour", "color", "palette")):
        for r in t[1:]:
            hx = next((c for c in r if re.fullmatch(r"#[0-9A-Fa-f]{6}", c)), None)
            if not hx:
                continue
            use = (r[-1] if len(r) >= 3 else "").lower()
            role = ("primary" if use.startswith("primary") else "accent" if use.startswith("accent") else
                    "secondary" if use.startswith("secondary") else "text" if "body text" in use else
                    "background" if "background" in use else "on_primary" if "text on" in use else _norm(r[0]))
            colours.setdefault(role, {"name": r[0], "hex": hx.upper(), "use": r[-1] if len(r) >= 3 else ""})
    if not colours:   # loose documents: first hex colours in order of appearance
        for role, hx in zip(("primary", "accent", "secondary", "text", "background"),
                            dict.fromkeys(h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", text))):
            colours[role] = {"name": role.title(), "hex": hx, "use": ""}
    logo_sec = _section(secs, "logo")
    wm = re.search(r"wordmark\s+([A-Z][A-Z0-9 ]{2,})", logo_sec)
    layout_sec = _section(secs, "layout", "document")
    footer = re.search(r"Footer:\s*\"([^\"]+)\"", layout_sec)
    return {
        "brand_id": _brand_id(name) if name else "", "name": name, "aliases": [name.split()[0].lower()] if name else [],
        "website": _bullet(ess, "Website"), "voice": voice,
        "tone_words": _split_list(_bullet(voice_sec, "Tone words")), "writing_rules": rules,
        "spelling": "en-US" if "us english" in rules_txt else "en-GB" if re.search(r"uk english|british", rules_txt)
        else "",
        "max_exclamations": 1 if "one exclamation" in rules_txt else 2 if "two exclamation" in rules_txt else None,
        "emojis_in_documents": 0 if "no emojis in documents" in rules_txt else None,
        "avg_sentence_words": int(m.group(1)) if (m := re.search(r"sentence under (\d+) words", rules_txt)) else None,
        "banned_words": banned, "replacements": repl, "product_names": products, "names": names,
        "claims_policy": _bullet(cn, "Claims policy"), "boilerplate": boiler, "facts": facts, "results": results,
        "social": social, "fonts": fonts, "colours": colours,
        "logo": {"wordmark": wm.group(1).strip() if wm else (name.split()[0].upper() if name else ""),
                 "rules": [ln.strip()[2:] for ln in logo_sec.splitlines() if ln.strip().startswith("- ")]},
        "layout": {"footer": footer.group(1) if footer else name,
                   "rules": [ln.strip()[2:] for ln in layout_sec.splitlines() if ln.strip().startswith("- ")]},
    }


def _coverage(p: dict) -> dict:
    checks = {"fonts": bool(p["fonts"].get("heading") and p["fonts"].get("body")),
              "colours": bool(p["colours"].get("primary")), "tone of voice": bool(p["voice"] or p["tone_words"]),
              "writing rules": bool(p["writing_rules"]), "banned words": bool(p["banned_words"]),
              "product names": bool(p["product_names"]), "customer naming and claims": bool(p["claims_policy"]),
              "approved facts / boilerplate": bool(p["facts"] or p["boilerplate"]),
              "logo usage": bool(p["logo"]["rules"]), "layout": bool(p["layout"]["rules"])}
    return {"found": [k for k, v in checks.items() if v], "missing": [k for k, v in checks.items() if not v]}


@hive_tool("workforce", kind="action")
def wf_brand_learn(guidelines: str, brand_name: str = "", *, tool_context: ToolContext) -> dict:
    """Learn a brand profile (fonts, colours, tone, writing rules, banned words, names, facts) from brand guidelines.

    Args:
        guidelines: Brand guidelines as markdown text, or a sample document key such as
            'wf_kitewing_brand_guidelines'.
        brand_name: Company name when the guidelines do not state it.

    Returns:
        The deterministic brand id, a summary of what was learned (fonts, colour hex codes, tone words, rule and word
        counts, product names, naming rules, facts), what is missing, and whether it updated a stored profile. The
        profile is saved to the brand library (simulated) and to this session for later checks and rendering.
    """
    text, key = _text(guidelines)
    if len(text) < 200:
        return err("guidelines too short — paste the brand guidelines or give a document key")
    p = _parse_guidelines(text, brand_name)
    if not p["name"]:
        return err("could not find the company name — pass brand_name")
    stored = next((x for x in _profiles() if x["brand_id"] == p["brand_id"]), None)
    changes = []
    if stored:
        for f in ("fonts", "colours", "banned_words", "product_names", "facts", "results", "writing_rules"):
            if json.dumps(stored.get(f), sort_keys=True) != json.dumps(p.get(f), sort_keys=True):
                changes.append(f)
        profile = {**stored, **{k: v for k, v in p.items() if v}}     # keep curated fact rules
    else:
        profile = {**p, "fact_rules": []}
    profile.update(source_doc=key or "pasted text", learned_on=TODAY.isoformat())
    st = _state(tool_context)
    if st is not None:
        st[f"wf_brand:{profile['brand_id']}"] = profile
    cov = _coverage(p)
    return ok(brand_id=profile["brand_id"], name=profile["name"],
              fonts={k: f"{v['name']} (fallback {v['fallback']})" for k, v in p["fonts"].items()},
              colours={k: f"{v['name']} {v['hex']}" for k, v in p["colours"].items()},
              tone_words=p["tone_words"], writing_rules=len(p["writing_rules"]), spelling=p["spelling"] or None,
              banned_words=len(p["banned_words"]), banned_sample=p["banned_words"][:8],
              product_names=[x["name"] for x in p["product_names"]],
              names={k: len(v) for k, v in p["names"].items()}, facts=len(p["facts"]),
              approved_results=len(p["results"]), wordmark=p["logo"]["wordmark"], footer=p["layout"]["footer"],
              coverage=cov,
              library=("matches the stored profile — no changes" if stored and not changes else
                       f"updated stored profile: {', '.join(changes)}" if stored else "new profile saved") +
              " (simulated); available in this session as " + profile["brand_id"])


@hive_tool("workforce")
def wf_brand_profile(brand: str = "kitewing", focus: str = "", *, tool_context: ToolContext = None) -> dict:
    """Get a customer's stored brand profile to apply to a deliverable: voice, rules, words, names, facts, visuals.

    Args:
        brand: The brand you write for — brand id (e.g. 'BRD-...') or company name; default is the demo customer,
            Kitewing Software ('kitewing'). Never a customer named in the content. 'house' = Agent Workforce house
            style.
        focus: 'writing' (voice, rules, words, product and customer names, approved facts and results), 'visual'
            (fonts, colours, logo, layout) or '' for both.

    Returns:
        The brand profile fields for the focus, compact enough to follow while writing.
    """
    p = _brand(brand, tool_context)
    if not p:
        return err(f"no brand profile {brand!r}", brands=[f"{x['brand_id']} {x['name']}" for x in _profiles()],
                   hint="brand = the company you write for (e.g. 'kitewing'), not a company named in the content; "
                        "new brands are learned with wf_brand_learn")
    f = (focus or "").lower()
    out: dict[str, Any] = {"brand_id": p["brand_id"], "name": p["name"]}
    if f in ("", "writing"):
        out.update(voice=p["voice"], tone_words=p["tone_words"], writing_rules=p["writing_rules"],
                   spelling=p.get("spelling"), banned_words=p["banned_words"], replacements=p["replacements"],
                   product_names=[f"{x['name']}: {x['rule']}" + (f" (never: {', '.join(x['never'])})"
                                                                   if x["never"] else "") for x in p["product_names"]],
                   names=p["names"], claims_policy=p["claims_policy"], boilerplate=p["boilerplate"],
                   facts=[f"{x['fact']}: {x['approved']}" for x in p["facts"]],
                   approved_results=[f"{x['customer']}: {x['result']}" for x in p["results"]],
                   social=p.get("social") if p.get("social", {}).get("hashtags") else None)
    if f in ("", "visual"):
        out.update(fonts={k: f"{v['name']} (fallback {v['fallback']}) {v.get('spec', '')}".strip()
                          for k, v in p["fonts"].items()},
                   colours={k: f"{v['name']} {v['hex']}" + (f" — {v['use']}" if v.get("use") else "")
                            for k, v in p["colours"].items()},
                   logo=p["logo"], layout=p["layout"])
    return ok(**out)


_UK_US = {"optimis": "optimiz", "organis": "organiz", "prioritis": "prioritiz", "recognis": "recogniz",
          "realis": "realiz", "summaris": "summariz", "minimis": "minimiz", "maximis": "maximiz",
          "customis": "customiz", "standardis": "standardiz", "utilis": "utiliz", "modernis": "moderniz",
          "apologis": "apologiz", "capitalis": "capitaliz", "digitalis": "digitaliz", "analys": "analyz"}
_UK_WORDS = {"colour": "color", "colours": "colors", "favour": "favor", "behaviour": "behavior", "labour": "labor",
             "honour": "honor", "neighbour": "neighbor", "centre": "center", "centres": "centers",
             "catalogue": "catalog", "programme": "program", "programmes": "programs", "licence": "license",
             "travelling": "traveling", "modelling": "modeling"}
_RESULT_VERB = re.compile(r"\b(cut|cuts|reduc\w*|lower\w*|sav(e|es|ed|ing|ings)|increas\w*|improv\w*|boost\w*|"
                          r"grow\w*|faster|fewer|down|up|drop\w*|rais\w*|doubl\w*|tripl\w*|halv\w*|from \S+ to)\b",
                          re.I)


def _style_issues(text: str, p: dict, audience: str, channel: str) -> tuple[list[dict], list[dict]]:
    block: list[dict] = []
    warn: list[dict] = []
    low = text.lower()
    for w in p["banned_words"]:
        if re.search(r"(?<![a-z])" + re.escape(w.lower()) + r"(?![a-z])", low):
            block.append({"rule": "banned word", "found": w,
                          "fix": f"use '{p['replacements'][w.lower()]}'" if w.lower() in p["replacements"]
                          else "rephrase with a plain verb"})
    for prod in p["product_names"]:
        for bad in prod["never"]:
            for m in re.finditer(r"(?<![A-Za-z])" + re.escape(bad) + r"(?![A-Za-z])", text, re.I):
                if m.group(0) not in prod["allowed"]:
                    block.append({"rule": "product name", "found": m.group(0), "fix": f"write '{prod['name']}'"})
                    break
        short = [a for a in prod["allowed"] if a != prod["name"]]
        if "first mention" in prod["rule"].lower() and short:
            first_short = re.search(r"(?<![A-Za-z])" + re.escape(short[0]) + r"(?![A-Za-z])", text)
            first_full = text.find(prod["name"])
            if first_short and (first_full < 0 or first_full > first_short.start() - len(prod["name"]) + len(short[0])):
                warn.append({"rule": "product name", "found": short[0],
                             "fix": f"use the full name '{prod['name']}' on first mention"})
    names = p["names"]
    if audience != "internal":
        for n in names["never"]:
            if (v := _find_name(text, n)):
                block.append({"rule": "customer naming", "found": v, "fix": "remove — this customer may not be "
                              "mentioned; use an approved customer or 'a customer'"})
        for a in names["anonymised"]:
            if (v := _find_name(text, a["name"])):
                block.append({"rule": "customer naming", "found": v, "fix": f"anonymise as '{a['use']}'"})
    for n in names["prospects"]:
        if (v := _find_name(text, n)):
            if audience == "public":
                block.append({"rule": "prospect named", "found": v, "fix": "prospects are never named in public "
                              "content"})
            elif audience == "client":
                warn.append({"rule": "prospect named", "found": v,
                             "fix": "fine only if they are the addressee of this document"})
    if audience == "public":
        for n in names["competitors"]:
            if (v := _find_name(text, n)):
                warn.append({"rule": "competitor named", "found": v, "fix": "no named comparisons in public content; "
                             "stating a public fact is fine"})
    if audience != "internal":
        ok_names = [*names["approved"], *[a["use"] for a in names["anonymised"]]]
        flagged = 0
        for s in _sentences(text):
            sl = s.lower()
            if not re.search(r"\d+(\.\d+)?\s?%|\b\d+(\.\d+)?x\b|\$\s?\d|\bfrom \d+(\.\d+)?%? to \d", sl):
                continue
            if not _RESULT_VERB.search(s) or re.search(r"according to|source:|\]\(http|customer-reported", sl):
                continue
            if any(_find_name(s, n) or n.lower() in sl for n in ok_names):
                continue
            if re.search(r"per (technician|tech|month|year|seat)|price|pricing|discount|fee|acv|subscription|invoice "
                         r"total|plan\b", sl):
                continue
            block.append({"rule": "claims policy", "found": s[:140], "fix": "name the approved customer story or "
                          "label it 'customer-reported'; otherwise remove the number"})
            flagged += 1
            if flagged >= 4:
                break
    social = channel in ("linkedin", "instagram", "social")
    ex = text.count("!")
    max_ex = p.get("max_exclamations") or (p.get("social") or {}).get("max_exclamations") or 1
    if ex > max_ex:
        warn.append({"rule": "punctuation", "found": f"{ex} exclamation marks", "fix": f"at most {max_ex}"})
    emojis = len(_EMOJI.findall(text))
    soc = p.get("social") or {}
    if social and emojis > soc.get("max_emojis", 2):
        warn.append({"rule": "emojis", "found": str(emojis), "fix": f"at most {soc.get('max_emojis', 2)} per post"})
    if not social and emojis and p.get("emojis_in_documents") == 0:
        warn.append({"rule": "emojis", "found": str(emojis), "fix": "no emojis in documents"})
    if social:
        tags = re.findall(r"#\w+", text)
        if len(tags) > soc.get("max_hashtags", 3):
            block.append({"rule": "hashtags", "found": f"{len(tags)} hashtags", "fix": f"at most "
                          f"{soc.get('max_hashtags', 3)}"})
        approved = {t.lower() for t in soc.get("hashtags", [])}
        odd = [t for t in tags if approved and t.lower() not in approved]
        if odd:
            warn.append({"rule": "hashtags", "found": ", ".join(odd[:5]), "fix": "use the approved hashtag list"})
        hook = text.strip().splitlines()[0] if text.strip() else ""
        if channel == "linkedin" and len(hook) > 140:
            warn.append({"rule": "hook", "found": f"{len(hook)} characters", "fix": "keep the first line under 140"})
    if p.get("spelling") == "en-US":
        found = []
        for m in re.finditer(r"\b([A-Za-z]+)\b", text):
            w = m.group(1)
            lw = w.lower()
            if lw in _UK_WORDS:
                found.append((w, _UK_WORDS[lw]))
            else:
                for uk, us in _UK_US.items():
                    if lw.startswith(uk) and re.fullmatch(uk + r"(e|es|ed|ing|ation|ations|er|ers)", lw):
                        found.append((w, us + lw[len(uk):]))
        for w, us in list(dict.fromkeys(found))[:5]:
            warn.append({"rule": "US spelling", "found": w, "fix": us})
    protected = {w.lower() for prod in p["product_names"] for w in prod["name"].split()} | \
        {w.lower() for n in names["approved"] for w in n.split()} | {w.lower() for w in p["name"].split()}
    title_case = 0
    for ln in text.splitlines():
        m = re.match(r"^#{1,4}\s+(.+)", ln.strip())
        if not m:
            continue
        ws = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", m.group(1))[1:] if len(w) >= 4 and w.lower() not in protected]
        if len(ws) >= 2 and all(w[0].isupper() for w in ws) and title_case < 3:
            warn.append({"rule": "sentence-case headings", "found": m.group(1)[:80], "fix": "write headings in "
                         "sentence case"})
            title_case += 1
    caps = [w for w in re.findall(r"\b[A-Z]{5,}\b", text) if w != p["logo"].get("wordmark")]
    if caps:
        warn.append({"rule": "all caps", "found": ", ".join(dict.fromkeys(caps[:4])), "fix": "avoid shouting in caps"})
    return block, warn


@hive_tool("workforce")
def wf_brand_check(text: str, brand: str = "kitewing", audience: str = "public", channel: str = "document", *,
                   tool_context: ToolContext = None) -> dict:
    """Check a draft against a brand profile with rules: banned words, product and customer names, claims, style.

    Args:
        text: The draft (markdown or plain text), or a sample document key such as 'wf_draft_press_release'.
        brand: Brand id or company name (default the demo customer, Kitewing Software).
        audience: 'public' (website, social, press), 'client' (a proposal or deck sent to one company) or 'internal'.
        channel: 'document' (also decks and spreadsheets), 'linkedin', 'instagram' or 'email'.

    Returns:
        Score 0-100, pass/fail (pass = no blocking issues and score >= 80), blocking issues and warnings each with
        what was found and the fix, and readability stats (words, average sentence length, Flesch reading ease).
    """
    body, _ = _text(text)
    if len(body.strip()) < 20:
        return err("text too short to check")
    p = _brand(brand, tool_context)
    if not p:
        return err(f"no brand profile {brand!r}", hint="learn it first with wf_brand_learn")
    aud = audience.lower().strip() if audience.lower().strip() in ("public", "client", "internal") else "public"
    ch = channel.lower().strip() or "document"
    block, warn = _style_issues(body, p, aud, ch)
    stats = _readability(body)
    target = p.get("avg_sentence_words") or 22
    if stats["avg_sentence_words"] and stats["avg_sentence_words"] > target:
        warn.append({"rule": "sentence length", "found": f"average {stats['avg_sentence_words']} words",
                     "fix": f"keep the average under {target}"})
    long_s = [s for s in _sentences(body) if len(s.split()) > 35]
    if long_s:
        warn.append({"rule": "long sentences", "found": f"{len(long_s)} over 35 words, e.g. '{long_s[0][:90]}...'",
                     "fix": "split them"})
    score = max(0, 100 - 15 * len(block) - 4 * len(warn))
    return ok(brand=p["name"], brand_id=p["brand_id"], audience=aud, channel=ch, score=score,
              passed=not block and score >= 80, blocking=block[:20], warnings=warn[:12], stats=stats,
              next_step="Apply each fix in your text and continue; re-check only a passage you rewrote completely."
              if block or warn else "On brand — continue.")


# --- QA: claims ---------------------------------------------------------------------------------------------------

_CLAIMY = re.compile(r"\d|\b(soc ?2|iso ?27001|hipaa|gdpr|certified|award|finalist|first|only|largest|leading|"
                     r"number one|#1|according to|study|survey|research|percent|available|beta|launch\w*|"
                     r"most \w+ed)\b", re.I)
_STATY = re.compile(r"\d+(\.\d+)?\s?(%|x\b|percent|customers|contractors|technicians|hours|days|minutes|jobs|people|"
                    r"employees|branches|million|billion)|\$\s?\d", re.I)
_SUPER = re.compile(r"\b(first|only|largest|leading|number one|#1|most \w+ed)\b", re.I)
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "by", "with", "is", "are", "was", "were", "that",
         "this", "it", "its", "as", "at", "be", "from", "than", "more", "our", "we", "their", "they", "will", "has",
         "have", "according"}


@hive_tool("workforce")
def wf_extract_claims(text: str, brand: str = "kitewing", audience: str = "public", *,
                      tool_context: ToolContext = None) -> dict:
    """Extract the factual claims in a draft and check each against the brand's approved facts and customer results.

    Args:
        text: The draft (markdown or plain text), or a sample document key such as 'wf_draft_press_release'.
        brand: The brand you write for — its approved facts apply (default Kitewing Software).
        audience: 'public', 'client' (a document addressed to one company, which may then be named) or 'internal'.

    Returns:
        Claims with status: 'matches' or 'contradicts' (against approved facts and results, with the approved
        wording), 'restricted' (names that may not appear), 'unverified' (about the company but not in the approved
        facts) or 'check_web' (public facts to verify with Google Search, with a suggested query); plus counts.
    """
    body, _ = _text(text)
    if len(body.strip()) < 20:
        return err("text too short")
    p = _brand(brand, tool_context)
    if not p:
        return err(f"no brand profile {brand!r}")
    names = p["names"]
    aud = (audience or "public").lower().strip()
    own = [p["name"], p["name"].split()[0], *[x["name"] for x in p["product_names"]]]
    results = []
    for r in p["results"]:
        results.append((r["customer"], _numbers(r["result"]), r["result"]))
    claims = []
    for s in _sentences(body):
        sl = s.lower()
        if len(s) < 20:
            continue
        rule_hit = any(re.search(r["trigger"], sl) for r in p.get("fact_rules", []))
        restricted = [] if aud == "internal" else \
            [v for n in names["never"] + (names["prospects"] if aud == "public" else []) if (v := _find_name(s, n))] + \
            [v for a in names["anonymised"] if (v := _find_name(s, a["name"]))]
        if not (rule_hit or restricted or _CLAIMY.search(s)):
            continue
        c: dict[str, Any] = {"claim": s[:220]}
        if restricted:
            c["restricted_name"] = restricted[0]
        hit = None
        for rule in p.get("fact_rules", []):
            if not re.search(rule["trigger"], sl):
                continue
            if rule["type"] == "number":
                vals = {float(m.replace(",", "")) for m in re.findall(rule["pattern"], sl)}
                if vals:
                    hit = {"status": "matches" if vals <= set(rule["expected"]) else "contradicts",
                           "topic": rule["topic"], "approved": rule["approved"]}
            else:
                bad = rule.get("forbid") and re.search(rule["forbid"], sl)
                missing = rule.get("require") and not re.search(rule["require"], sl)
                hit = {"status": "contradicts" if bad or missing else "matches", "topic": rule["topic"],
                       "approved": rule["approved"],
                       "note": f"found '{bad.group(0)}'" if bad else "approved wording missing" if missing else None}
            if hit and hit["status"] == "contradicts":
                break
        if not hit:
            for cust, allowed, wording in results:
                if _find_name(s, cust) or (cust.startswith("a ") and cust.lower() in sl):
                    nums = _numbers(s)
                    hit = {"status": "matches" if nums <= allowed else "contradicts", "topic": f"{cust} results",
                           "approved": wording}
                    break
        if hit and hit["status"] == "contradicts":
            claims.append({**c, **{k: v for k, v in hit.items() if v}})
            continue
        if restricted:
            claims.append({**c, "status": "restricted",
                           "note": "this name may not appear in public content (brand customer-naming rules)"})
            continue
        if hit:
            claims.append({**c, **{k: v for k, v in hit.items() if v}})
            continue
        about_us = any(re.search(r"(?<![A-Za-z])" + re.escape(o) + r"(?![A-Za-z])", s) for o in own) or \
            bool(re.search(r"\b(our|we)\b", sl))
        has_stat = bool(_STATY.search(s)) or "according to" in sl
        if about_us and not re.search(r"according to|bureau|survey|study|census", sl):
            if has_stat or _SUPER.search(s):
                claims.append({**c, "status": "unverified",
                               "note": "about the company but not in the approved facts — confirm or remove"})
        elif has_stat:
            q = " ".join(w for w in re.findall(r"[A-Za-z0-9%$.]+", s) if w.lower() not in _STOP)[:110]
            claims.append({**c, "status": "check_web", "query": q})
    order = {"contradicts": 0, "restricted": 1, "check_web": 2, "unverified": 3, "matches": 4}
    claims.sort(key=lambda x: order[x["status"]])
    counts: dict[str, int] = {}
    for x in claims:
        counts[x["status"]] = counts.get(x["status"], 0) + 1
    return ok(brand=p["name"], audience=aud, claims=claims[:15], counts=counts, total=len(claims),
              next_step="Fix every 'contradicts' and 'restricted' claim with the approved wording; verify 'check_web' "
                        "claims with Google Search (cite the source) or remove them. No need to run this again.")


# --- deliverable templates ----------------------------------------------------------------------------------------


@hive_tool("workforce")
def wf_deliverable_template(kind: str = "") -> dict:
    """Get the Agent Workforce standard outline, length and quality checklist for one kind of deliverable.

    Args:
        kind: seo_audit, blog_brief, blog_post, content_calendar, proposal, pitch_deck, sop, gtm_plan, whitepaper,
            press_release or one_pager ('' lists the kinds).

    Returns:
        Section outline with guidance, target length, default and allowed formats, the specialist(s) who produce it
        and the checklist QA will apply.
    """
    tpl = fixture("wf_templates")["templates"]
    if not kind.strip():
        return ok(kinds={k: f"{v['name']} (.{v['default_format']})" for k, v in tpl.items()})
    k = _norm(kind).replace(" ", "_")
    t = tpl.get(k) or next((v for x, v in tpl.items() if _norm(v["name"]) == _norm(kind) or k in x), None)
    if not t:
        return err(f"unknown deliverable kind {kind!r}", kinds=list(tpl))
    return ok(kind=next(x for x, v in tpl.items() if v is t), name=t["name"], sections=t["sections"],
              length=t["length"], default_format=t["default_format"], formats=t["formats"],
              specialists=t["specialists"], checklist=t["checklist"])


# --- Document Studio: the renderer ----------------------------------------------------------------------------------


def _blocks(body: str) -> list[tuple]:
    """Markdown-ish body -> blocks: ('h', level, text) ('p', text) ('ul'|'ol', [(level, text)]) ('quote', text)
    ('table', rows)."""
    out: list[tuple] = []
    para: list[str] = []
    table: list[list[str]] = []
    lst: tuple[str, list] | None = None

    def flush() -> None:
        nonlocal para, table, lst
        if para:
            out.append(("p", " ".join(para)))
            para = []
        if table:
            out.append(("table", table))
            table = []
        if lst:
            out.append(lst)
            lst = None

    for raw in (body or "").replace("\r", "").split("\n"):
        line = raw.rstrip()
        s = line.strip()
        if s.startswith("|"):
            if para or lst:
                p_, l_ = para, lst
                para, lst = [], None
                if p_:
                    out.append(("p", " ".join(p_)))
                if l_:
                    out.append(l_)
            if not re.match(r"^\|[\s:\-|]+\|?$", s):
                table.append([c.strip() for c in s.strip().strip("|").split("|")])
            continue
        if table:
            out.append(("table", table))
            table = []
        if not s or re.fullmatch(r"[-*_]{3,}", s):
            flush()
            continue
        if (m := re.match(r"^(#{1,6})\s+(.*)", s)):
            flush()
            out.append(("h", len(m.group(1)), m.group(2).strip()))
            continue
        m_ul = re.match(r"^(\s*)[-*•+]\s+(.*)", line)
        m_ol = re.match(r"^(\s*)\d+[.)]\s+(.*)", line)
        if m_ul or m_ol:
            m = m_ul or m_ol
            kind = "ul" if m_ul else "ol"
            if para:
                out.append(("p", " ".join(para)))
                para = []
            if lst and lst[0] != kind:
                out.append(lst)
                lst = None
            lst = lst or (kind, [])
            lst[1].append((min(2, len(m.group(1).replace("\t", "  ")) // 2), m.group(2).strip()))
            continue
        if (m := re.match(r"^>\s?(.*)", s)):
            flush()
            out.append(("quote", m.group(1)))
            continue
        if lst:
            out.append(lst)
            lst = None
        para.append(s)
    flush()
    return out


_INLINE = re.compile(r"(\*\*[^*]+\*\*|__[^_]+__|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def _runs(text: str) -> list[tuple[str, bool, bool]]:
    """Inline markdown -> [(text, bold, italic)]; links become 'text (url)'."""
    out = []
    for part in _INLINE.split(text or ""):
        if not part:
            continue
        if part.startswith(("**", "__")) and len(part) > 4:
            out.append((part[2:-2], True, False))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append((part[1:-1], False, True))
        elif part.startswith("`"):
            out.append((part[1:-1], False, False))
        elif (m := re.match(r"\[([^\]]+)\]\(([^)]+)\)", part)):
            out.append((f"{m.group(1)} ({m.group(2)})", False, False))
        else:
            out.append((part, False, False))
    return out


def _plain(text: str) -> str:
    return "".join(t for t, _, _ in _runs(text))


def _rows(table: Any) -> list[list[str]]:
    """Table input (list of lists, list of dicts, or markdown rows) -> list of string rows, header first."""
    if not table:
        return []
    if isinstance(table, str):
        return next(iter(_md_tables(table)), [])
    if isinstance(table, dict):
        table = table.get("rows") or [table]
    rows: list[list[str]] = []
    if isinstance(table, list) and table and isinstance(table[0], dict):
        cols = list(dict.fromkeys(k for r in table if isinstance(r, dict) for k in r))
        rows = [cols] + [[_cell(r.get(c, "")) for c in cols] for r in table if isinstance(r, dict)]
    else:
        for r in table:
            if isinstance(r, (list, tuple)):
                rows.append([_cell(c) for c in r])
            elif isinstance(r, str) and "|" in r:
                rows.append([c.strip() for c in r.strip().strip("|").split("|")])
            elif r is not None:
                rows.append([_cell(r)])
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows if any(str(c).strip() for c in r)]


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _spec(title: str, subtitle: str, sections: list[dict] | None, markdown: str) -> tuple[str, str, list[dict]]:
    """Normalise the two input styles into (title, subtitle, sections[{heading, body, table, notes}])."""
    out: list[dict] = []
    if markdown and markdown.strip():
        md_title, cur = "", {"heading": "", "body": ""}
        for line in markdown.replace("\r", "").split("\n"):
            if (m := re.match(r"^#\s+(.+)", line.strip())) and not md_title and not cur["body"].strip() and not out:
                md_title = m.group(1).strip()
                continue
            if (m := re.match(r"^##\s+(.+)", line.strip())):
                if cur["heading"] or cur["body"].strip():
                    out.append(cur)
                cur = {"heading": m.group(1).strip(), "body": ""}
                continue
            cur["body"] += line + "\n"
        if cur["heading"] or cur["body"].strip():
            out.append(cur)
        title = title or md_title
    for s in sections or []:
        if not isinstance(s, dict):
            out.append({"heading": "", "body": str(s)})
            continue
        body = str(s.get("body") or s.get("content") or s.get("text") or "")
        bullets = s.get("bullets") or s.get("points") or []
        if isinstance(bullets, list) and bullets:
            body = (body.rstrip() + "\n" if body.strip() else "") + "\n".join(f"- {b}" for b in bullets)
        out.append({"heading": str(s.get("heading") or s.get("title") or ""), "body": body,
                    "table": _rows(s.get("table") or s.get("rows")), "notes": str(s.get("notes") or "")})
    for s in out:
        s.setdefault("table", [])
        s.setdefault("notes", "")
        s["body"] = s["body"].strip("\n")
    if subtitle == "" and out and not out[0]["heading"] and len(out[0]["body"]) <= 200 and len(out) > 1 \
            and not _blocks(out[0]["body"])[1:] and not out[0]["table"]:
        subtitle = _plain(out.pop(0)["body"]).lstrip("*_ ").rstrip("*_ ")
    return title, subtitle, out


def _hex(p: dict, role: str, default: str) -> str:
    return (p["colours"].get(role) or {}).get("hex", default).lstrip("#").upper()


def _font(p: dict, role: str, default: str) -> str:
    return (p["fonts"].get(role) or {}).get("name", default)


def _meta_line(prepared_for: str, version: int, job_id: str) -> str:
    bits = [f"Prepared for {prepared_for}" if prepared_for else "", TODAY.strftime("%d %B %Y").lstrip("0"),
            f"Version {version}", f"Job {job_id}" if job_id else ""]
    return " · ".join(b for b in bits if b)


def _docx(title: str, subtitle: str, sections: list[dict], p: dict, prepared_for: str, version: int, job_id: str,
          confidential: bool) -> tuple[bytes, dict]:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    hf, bf = _font(p, "heading", "Arial"), _font(p, "body", "Calibri")
    primary, accent = _hex(p, "primary", "1F2A44"), _hex(p, "accent", "B0306A")
    ink, band = _hex(p, "text", "1F2328"), _hex(p, "background", "F4F5F7")
    muted = _hex(p, "secondary", "5C6B8A")

    def set_font(font: Any, name: str, size: float | None = None, color: str | None = None,
                 bold: bool | None = None) -> None:
        font.name = name
        rpr = font.element.get_or_add_rPr() if hasattr(font, "element") else None
        if rpr is not None:
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is None:
                rfonts = OxmlElement("w:rFonts")
                rpr.insert(0, rfonts)
            for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                rfonts.set(qn(a), name)
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                rfonts.attrib.pop(qn(a), None)
        if size:
            font.size = Pt(size)
        if color:
            font.color.rgb = RGBColor.from_string(color)
        if bold is not None:
            font.bold = bold

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = sec.bottom_margin = Cm(2.2)
        sec.left_margin = sec.right_margin = Cm(2.3)
    styles = doc.styles
    set_font(styles["Normal"].font, bf, 10.5, ink)
    styles["Normal"].paragraph_format.space_after = Pt(6)
    styles["Normal"].paragraph_format.line_spacing = 1.15
    for lvl, size in ((1, 18), (2, 14), (3, 12)):
        st = styles[f"Heading {lvl}"]
        set_font(st.font, hf, size, primary, True)
        st.font.italic = False
        st.paragraph_format.space_before = Pt(16 if lvl == 1 else 10)
        st.paragraph_format.space_after = Pt(6)
    for name in ("List Bullet", "List Bullet 2", "List Number", "Quote"):
        try:
            set_font(styles[name].font, bf, 10.5, ink)
        except KeyError:
            pass

    def add_runs(par: Any, text: str, size: float | None = None, color: str | None = None) -> None:
        for t, b, i in _runs(text):
            r = par.add_run(t)
            r.bold = b or None
            r.italic = i or None
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = RGBColor.from_string(color)

    def shade(cell: Any, fill: str) -> None:
        tcpr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill)
        tcpr.append(shd)

    def add_table(rows: list[list[str]]) -> None:
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        t = doc.add_table(rows=len(rows), cols=ncols)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblpr = t._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "4")
            e.set(qn("w:color"), "D5DAE1")
            borders.append(e)
        tblpr.append(borders)
        for i, row in enumerate(rows):
            for j in range(ncols):
                cell = t.cell(i, j)
                par = cell.paragraphs[0]
                par.paragraph_format.space_after = Pt(2)
                txt = row[j] if j < len(row) else ""
                if i == 0:
                    r = par.add_run(_plain(txt))
                    r.bold = True
                    r.font.size = Pt(9.5)
                    r.font.color.rgb = RGBColor.from_string("FFFFFF")
                    set_font(r.font, hf)
                    shade(cell, primary)
                else:
                    add_runs(par, txt, 9.5)
                    if i % 2 == 0:
                        shade(cell, band)
        doc.add_paragraph()

    def rule(par: Any, color: str, size: int = 18) -> None:
        ppr = par._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        b = OxmlElement("w:bottom")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(size))
        b.set(qn("w:space"), "4")
        b.set(qn("w:color"), color)
        bdr.append(b)
        ppr.append(bdr)

    def field(par: Any, instr: str) -> None:
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), instr)
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = "1"
        r.append(t)
        fld.append(r)
        par._p.append(fld)

    # title page
    wm = p["logo"].get("wordmark") or p["name"].upper()
    par = doc.add_paragraph()
    r = par.add_run(wm)
    set_font(r.font, hf, 13, primary, True)
    rpr = r._r.get_or_add_rPr()
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:val"), "60")
    rpr.append(sp)
    for _ in range(6):
        doc.add_paragraph()
    par = doc.add_paragraph()
    r = par.add_run(title)
    set_font(r.font, hf, 28, primary, True)
    rule(par, accent, 24)
    if subtitle:
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(10)
        r = par.add_run(subtitle)
        set_font(r.font, bf, 14, ink)
    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(24)
    r = par.add_run(_meta_line(prepared_for, version, job_id))
    set_font(r.font, bf, 10, muted)
    if confidential:
        par = doc.add_paragraph()
        r = par.add_run("Confidential")
        set_font(r.font, hf, 10, accent, True)
    par = doc.add_paragraph()
    r = par.add_run(f"Delivered by Agent Workforce · brand profile {p['brand_id']}")
    set_font(r.font, bf, 8, "8A94A6")
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    words, rows_n, outline = 0, 0, []
    for s in sections:
        if s["heading"]:
            doc.add_heading(_plain(s["heading"]), level=1)
            outline.append(_plain(s["heading"]))
        for b in _blocks(s["body"]):
            if b[0] == "h":
                doc.add_heading(_plain(b[2]), level=2 if b[1] <= 3 else 3)
            elif b[0] == "p":
                add_runs(doc.add_paragraph(), b[1])
                words += len(b[1].split())
            elif b[0] in ("ul", "ol"):
                for lvl, txt in b[1]:
                    style = ("List Bullet" if b[0] == "ul" else "List Number") + (" 2" if lvl and b[0] == "ul" else "")
                    try:
                        add_runs(doc.add_paragraph(style=style), txt)
                    except KeyError:
                        add_runs(doc.add_paragraph(), f"• {txt}")
                    words += len(txt.split())
            elif b[0] == "quote":
                q = doc.add_paragraph(style="Quote")
                add_runs(q, b[1])
                words += len(b[1].split())
            elif b[0] == "table":
                add_table(b[1])
                rows_n += len(b[1])
        if s["table"]:
            add_table(s["table"])
            rows_n += len(s["table"])

    footer_txt = p["layout"].get("footer") or p["name"]
    for sec in doc.sections:
        sec.different_first_page_header_footer = True
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run(wm)
        set_font(r.font, hf, 8, primary, True)
        for ft in (sec.footer, sec.first_page_footer):
            fp = ft.paragraphs[0]
            r = fp.add_run(footer_txt + (" · Confidential" if confidential else "") + " · Page ")
            set_font(r.font, bf, 8, "6B7280")
            field(fp, "PAGE")
    cp = doc.core_properties
    cp.title, cp.subject, cp.author = title[:250], subtitle[:250], "Agent Workforce"
    cp.keywords = " ".join(x for x in (job_id, p["brand_id"]) if x)
    cp.last_modified_by = "Agent Workforce"
    cp.created = cp.modified = dt.datetime(TODAY.year, TODAY.month, TODAY.day, 9, 0)
    buf = io.BytesIO()
    doc.save(buf)
    pages = 1 + max(1, math.ceil(words / 380 + rows_n / 28 + len(outline) * 0.08))
    return buf.getvalue(), {"pages_est": pages, "words": words, "outline": outline}


def _pptx(title: str, subtitle: str, sections: list[dict], p: dict, prepared_for: str, version: int, job_id: str,
          confidential: bool) -> tuple[bytes, dict]:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.util import Inches, Pt

    hf = _font(p, "slide_title", _font(p, "heading", "Arial"))
    bf = _font(p, "slide_body", _font(p, "body", "Calibri"))
    primary, accent = _hex(p, "primary", "1F2A44"), _hex(p, "accent", "B0306A")
    ink, band = _hex(p, "text", "1F2328"), _hex(p, "background", "F4F5F7")
    on_primary = _hex(p, "on_primary", "FFFFFF")
    secondary = _hex(p, "secondary", "5C6B8A")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    wm = p["logo"].get("wordmark") or p["name"].upper()
    footer_txt = p["layout"].get("footer") or p["name"]

    def box(slide: Any, x: float, y: float, w: float, h: float) -> Any:
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tb.text_frame.word_wrap = True
        return tb.text_frame

    def style_run(r: Any, font: str, size: float, color: str, bold: bool = False, italic: bool = False) -> None:
        r.font.name, r.font.size, r.font.bold, r.font.italic = font, Pt(size), bold, italic
        r.font.color.rgb = RGBColor.from_string(color)

    def write(par: Any, text: str, font: str, size: float, color: str, bold: bool = False) -> None:
        for t, b, i in _runs(text):
            style_run(par.add_run(), font, size, color, bold or b, i)
            par.runs[-1].text = t

    def bullet(par: Any, level: int) -> None:
        ppr = par._p.get_or_add_pPr()
        ppr.set("marL", str(int(Inches(0.3 + 0.35 * level))))
        ppr.set("indent", str(int(-Inches(0.25))))
        clr = ppr.makeelement(qn("a:buClr"), {})
        srgb = clr.makeelement(qn("a:srgbClr"), {"val": accent})
        clr.append(srgb)
        ppr.append(clr)
        ppr.append(ppr.makeelement(qn("a:buChar"), {"char": "•"}))

    def rect(slide: Any, x: float, y: float, w: float, h: float, color: str) -> None:
        shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(color)
        shp.line.fill.background()
        shp.shadow.inherit = False

    # title slide
    s = prs.slides.add_slide(blank)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = RGBColor.from_string(primary)
    tf = box(s, 0.7, 0.55, 8, 0.5)
    write(tf.paragraphs[0], wm, hf, 14, on_primary, True)
    tf = box(s, 0.7, 2.0, 11.9, 2.0)
    tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    write(tf.paragraphs[0], title, hf, 40 if len(title) < 60 else 32, on_primary, True)
    rect(s, 0.7, 4.15, 1.6, 0.09, accent)
    if subtitle:
        tf = box(s, 0.7, 4.4, 11.9, 1.2)
        write(tf.paragraphs[0], subtitle, bf, 20, on_primary)
    tf = box(s, 0.7, 6.55, 11.9, 0.5)
    write(tf.paragraphs[0], _meta_line(prepared_for, version, job_id) + (" · Confidential" if confidential else ""),
          bf, 12, on_primary)

    n_slide = 1

    def content_slide(heading: str, items: list[tuple[str, int, str]], table: list[list[str]], notes: str) -> None:
        nonlocal n_slide
        n_slide += 1
        sl = prs.slides.add_slide(blank)
        rect(sl, 0.7, 0.45, 0.9, 0.08, accent)
        tf_ = box(sl, 0.7, 0.6, 11.9, 1.0)
        write(tf_.paragraphs[0], heading or title, hf, 28 if len(heading) < 55 else 22, primary, True)
        top = 1.75
        if items:
            chars = sum(len(t) for t, _, _ in items)
            size = 20 if chars < 300 and len(items) <= 5 else 17 if chars < 600 else 14
            h = 4.9 if not table else min(2.2, 0.45 * len(items) + 0.3)
            tf_ = box(sl, 0.7, top, 11.9, h)
            first = True
            for text, level, kind in items:
                par = tf_.paragraphs[0] if first else tf_.add_paragraph()
                first = False
                par.space_after = Pt(8)
                if kind == "h":
                    write(par, text, hf, size, primary, True)
                else:
                    write(par, text, bf, size - 2 * level, ink)
                    if kind == "li":
                        bullet(par, level)
            top += h + 0.15
        if table:
            ncols = max(len(r) for r in table)
            rows_h = min(5.4 - (top - 1.75), 0.42 * len(table))
            gt = sl.shapes.add_table(len(table), ncols, Inches(0.7), Inches(top), Inches(11.9), Inches(rows_h)).table
            for i, row in enumerate(table):
                for j in range(ncols):
                    c = gt.cell(i, j)
                    c.fill.solid()
                    c.fill.fore_color.rgb = RGBColor.from_string(primary if i == 0 else band if i % 2 == 0
                                                                 else "FFFFFF")
                    par = c.text_frame.paragraphs[0]
                    txt = row[j] if j < len(row) else ""
                    write(par, _plain(txt) if i == 0 else txt, hf if i == 0 else bf, 12 if len(table) < 8 else 11,
                          "FFFFFF" if i == 0 else ink, i == 0)
        ft = box(sl, 0.7, 6.95, 9.5, 0.35)
        write(ft.paragraphs[0], footer_txt + (" · Confidential" if confidential else ""), bf, 10, secondary)
        ft = box(sl, 10.4, 6.95, 2.2, 0.35)
        ft.paragraphs[0].alignment = PP_ALIGN.RIGHT
        write(ft.paragraphs[0], f"{wm}   {n_slide}", hf, 10, primary, True)
        if notes:
            sl.notes_slide.notes_text_frame.text = notes

    outline = []
    for sec in sections:
        items: list[tuple[str, int, str]] = []
        tables: list[list[list[str]]] = [sec["table"]] if sec["table"] else []
        for b in _blocks(sec["body"]):
            if b[0] == "h":
                items.append((_plain(b[2]), 0, "h"))
            elif b[0] in ("p", "quote"):
                items.append((b[1], 0, "p"))
            elif b[0] in ("ul", "ol"):
                items += [(t, lvl, "li") for lvl, t in b[1]]
            elif b[0] == "table":
                tables.insert(0, b[1])
        heading = _plain(sec["heading"])
        outline.append(heading or title)
        chunks = [items[i:i + 6] for i in range(0, len(items), 6)] or [[]]
        if tables and len(chunks[-1]) > 3:
            chunks.append([])
        for ci, chunk in enumerate(chunks):
            last = ci == len(chunks) - 1
            tbl = tables[0] if (last and tables) else []
            if tbl and len(tbl) > 9:
                content_slide(heading + (" (cont.)" if ci else ""), chunk, tbl[:9], sec["notes"] if ci == 0 else "")
                rest = tbl[9:]
                while rest:
                    content_slide(heading + " (cont.)", [], [tbl[0]] + rest[:8], "")
                    rest = rest[8:]
            else:
                content_slide(heading + (" (cont.)" if ci else ""), chunk, tbl, sec["notes"] if ci == 0 else "")
        for extra in tables[1:]:
            content_slide(heading + " (cont.)", [], extra[:9], "")
    cp = prs.core_properties
    cp.title, cp.subject, cp.author = title[:250], subtitle[:250], "Agent Workforce"
    cp.keywords = " ".join(x for x in (job_id, p["brand_id"]) if x)
    cp.created = cp.modified = dt.datetime(TODAY.year, TODAY.month, TODAY.day, 9, 0)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue(), {"slides": len(prs.slides), "outline": outline}


def _typed(v: str) -> Any:
    s = str(v).strip()
    if re.fullmatch(r"-?(0|[1-9]\d{0,14})(\.\d+)?", s):
        return float(s) if "." in s else int(s)
    if re.fullmatch(r"\$-?\d[\d,]*(\.\d+)?", s):
        return ("usd", float(s[1:].replace(",", "")))
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return dt.date.fromisoformat(s)
        except ValueError:
            return s
    return s


def _xlsx(title: str, subtitle: str, sheets: list[dict], p: dict, prepared_for: str, version: int,
          job_id: str) -> tuple[bytes, dict]:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    hf, bf = _font(p, "heading", "Arial"), _font(p, "body", "Calibri")
    primary, ink, band = _hex(p, "primary", "1F2A44"), _hex(p, "text", "1F2328"), _hex(p, "background", "F4F5F7")
    accent = _hex(p, "accent", "B0306A")
    wb = Workbook()
    thin = Side(style="thin", color="D5DAE1")
    used: set[str] = set()
    outline = []
    for i, sh in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        name = re.sub(r"[\[\]:*?/\\]", "", str(sh.get("name") or f"Sheet{i + 1}"))[:31] or f"Sheet{i + 1}"
        base, k = name, 2
        while name.lower() in used:
            name = f"{base[:28]} {k}"
            k += 1
        used.add(name.lower())
        ws.title = name
        outline.append(name)
        rows = sh["rows"]
        widths: dict[int, int] = {}
        for r_i, row in enumerate(rows, start=1):
            for c_i, val in enumerate(row, start=1):
                v = _typed(val) if r_i > 1 else _plain(str(val))
                cell = ws.cell(row=r_i, column=c_i)
                if isinstance(v, tuple):
                    cell.value, cell.number_format = v[1], '"$"#,##0.00'
                else:
                    cell.value = _plain(v) if isinstance(v, str) else v
                    if isinstance(v, dt.date):
                        cell.number_format = "yyyy-mm-dd"
                cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
                if r_i == 1:
                    cell.font = Font(name=hf, bold=True, color="FFFFFF", size=10.5)
                    cell.fill = PatternFill("solid", fgColor=primary)
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                else:
                    cell.font = Font(name=bf, color=ink, size=10)
                    if r_i % 2 == 1:
                        cell.fill = PatternFill("solid", fgColor=band)
                    cell.alignment = Alignment(vertical="top", wrap_text=len(str(val)) > 40)
                widths[c_i] = max(widths.get(c_i, 0), min(60, len(str(val))))
        for c_i, w in widths.items():
            ws.column_dimensions[get_column_letter(c_i)].width = max(9, w * 1.1 + 2)
        if rows:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
        ws.sheet_properties.tabColor = primary
    about = wb.create_sheet("About")
    about["A1"] = title
    about["A1"].font = Font(name=hf, bold=True, size=16, color=primary)
    r = 2
    if subtitle:
        about["A2"] = subtitle
        about["A2"].font = Font(name=bf, size=12, color=ink)
        r = 3
    for label, val in (("Prepared for", prepared_for), ("Date", TODAY.isoformat()), ("Version", version),
                       ("Job", job_id or "—"), ("Brand profile", f"{p['name']} ({p['brand_id']})"),
                       ("Delivered by", "Agent Workforce")):
        r += 1
        about.cell(row=r, column=1, value=label).font = Font(name=hf, bold=True, color=primary)
        about.cell(row=r, column=2, value=val).font = Font(name=bf, color=ink)
    about.cell(row=r + 2, column=1, value=p["layout"].get("footer") or p["name"]).font = Font(name=bf, color=accent,
                                                                                              size=9)
    about.column_dimensions["A"].width, about.column_dimensions["B"].width = 18, 60
    about.sheet_properties.tabColor = accent
    wb.properties.title, wb.properties.creator = title[:250], "Agent Workforce"
    wb.properties.created = wb.properties.modified = dt.datetime(TODAY.year, TODAY.month, TODAY.day, 9, 0)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), {"sheets": len(wb.sheetnames), "outline": outline,
                            "rows": sum(max(0, len(s["rows"]) - 1) for s in sheets)}


def _md(title: str, subtitle: str, sections: list[dict], p: dict, prepared_for: str, version: int,
        job_id: str) -> tuple[bytes, dict]:
    lines = [f"# {title}", ""]
    if subtitle:
        lines += [f"*{subtitle}*", ""]
    lines += [f"> {_meta_line(prepared_for, version, job_id)} · {p['name']}", ""]
    for s in sections:
        if s["heading"]:
            lines += [f"## {s['heading']}", ""]
        if s["body"]:
            lines += [s["body"], ""]
        if s["table"]:
            t = s["table"]
            lines += ["| " + " | ".join(t[0]) + " |", "|" + "---|" * len(t[0])]
            lines += ["| " + " | ".join(r) + " |" for r in t[1:]] + [""]
    lines += ["---", f"{p['layout'].get('footer') or p['name']} · Delivered by Agent Workforce"]
    return "\n".join(lines).encode(), {"outline": [s["heading"] for s in sections if s["heading"]]}


def _sheets_from(sheets: list[dict] | None, sections: list[dict]) -> list[dict]:
    out = []
    for i, sh in enumerate(sheets or []):
        if not isinstance(sh, dict):
            continue
        rows = sh.get("rows") or sh.get("data") or []
        cols = sh.get("columns") or sh.get("header")
        if rows and isinstance(rows[0], dict):
            rows = _rows(rows)
        else:
            rows = _rows(rows)
            if cols and (not rows or [str(c) for c in cols] != rows[0]):
                rows = [[str(c) for c in cols]] + rows
        if rows:
            out.append({"name": sh.get("name") or sh.get("title") or f"Sheet{i + 1}", "rows": rows})
    if out:
        return out
    for s in sections:
        tables = ([s["table"]] if s["table"] else []) + [b[1] for b in _blocks(s["body"]) if b[0] == "table"]
        for j, t in enumerate(tables):
            out.append({"name": (_plain(s["heading"]) or "Sheet") + (f" {j + 1}" if j else ""), "rows": t})
    if not out and sections:
        rows = [["Section", "Content"]]
        for s in sections:
            for b in _blocks(s["body"]):
                txt = b[1] if b[0] in ("p", "quote") else "; ".join(t for _, t in b[1]) if b[0] in ("ul", "ol") \
                    else b[2] if b[0] == "h" else ""
                if txt:
                    rows.append([_plain(s["heading"]), _plain(txt)])
        out.append({"name": "Content", "rows": rows})
    return out


@hive_tool("workforce", kind="action")
def wf_render_document(title: str, output_format: str = "", subtitle: str = "", sections: list[dict] | None = None,
                       markdown: str = "", sheets: list[dict] | None = None, brand: str = "kitewing",
                       prepared_for: str = "", job_id: str = "", version: int = 1, confidential: bool = False, *,
                       tool_context: ToolContext) -> dict:
    """Render the final deliverable as a real brand-styled file (Word, PowerPoint, Excel, Markdown or CSV).

    Give the content EITHER as `markdown` (a full document: '# Title', '## Section' per section or slide, paragraphs,
    '- ' bullets, '1. ' steps, '### ' sub-headings, '| a | b |' tables, **bold**) OR as `sections`. For xlsx give
    `sheets` (or markdown/sections whose tables become sheets).

    Args:
        title: Document title (title page / title slide).
        output_format: 'docx', 'pptx', 'xlsx', 'md' or 'csv' ('pdf' is delivered as docx in this prototype).
            Empty = xlsx when sheets are given, otherwise docx.
        subtitle: Optional subtitle.
        sections: Optional list of {"heading": str, "body": markdown text, "bullets": [str] (optional),
            "table": [[header...], [row...]] (optional), "notes": speaker notes for pptx (optional)}. In pptx each
            section becomes a slide (long sections continue on extra slides).
        markdown: Optional full document in markdown instead of sections.
        sheets: For xlsx/csv: list of {"name": str, "rows": [[header...], [row...], ...]} (rows may also be dicts).
        brand: Brand id or company name whose fonts, colours, wordmark and footer are applied (default Kitewing
            Software; 'house' for the Agent Workforce house style).
        prepared_for: Who the document is for (shown on the title page); default the brand's company.
        job_id: Agent Workforce job id, if any.
        version: 1 for the first delivery; increase by one for each revision.
        confidential: True for proposals and internal documents (adds 'Confidential').

    Returns:
        file_id, file name, format, size in bytes, page/slide/sheet count and the outline. The file itself is
        attached to the session for download — never returned in the response.
    """
    fmt = (output_format or ("xlsx" if sheets else "docx")).lower().strip(". ")
    note = None
    if fmt in ("pdf", "doc", "word"):
        note = "PDF export runs in the Agent Workforce product; delivered .docx." if fmt == "pdf" else None
        fmt = "docx"
    fmt = {"ppt": "pptx", "powerpoint": "pptx", "excel": "xlsx", "xls": "xlsx", "markdown": "md"}.get(fmt, fmt)
    if fmt not in FORMATS:
        return err(f"unsupported format {output_format!r}", formats=list(FORMATS))
    title = (title or "").strip()
    p = _brand(brand, tool_context)
    if not p:
        return err(f"no brand profile {brand!r}", hint="use 'kitewing', a learned brand id or 'house'")
    title, subtitle, secs = _spec(title, (subtitle or "").strip(), sections, markdown)
    if not title:
        return err("title is required")
    xl = _sheets_from(sheets, secs) if fmt in ("xlsx", "csv") else []
    if fmt in ("xlsx", "csv") and not xl:
        return err("no rows to put in the spreadsheet — give sheets or tables")
    if fmt not in ("xlsx", "csv") and not any(s["body"] or s["table"] for s in secs):
        return err("no content — give markdown or sections with a body")
    st = _state(tool_context)
    if st is None:
        return err("no session state to attach the file to")
    version = max(1, int(version or 1))
    prepared_for = (prepared_for or p["name"]).strip()
    version_tag = f"-v{version}" if version > 1 else ""
    try:
        if fmt == "docx":
            data, info = _docx(title, subtitle, secs, p, prepared_for, version, job_id, confidential)
        elif fmt == "pptx":
            data, info = _pptx(title, subtitle, secs, p, prepared_for, version, job_id, confidential)
        elif fmt == "xlsx":
            data, info = _xlsx(title, subtitle, xl, p, prepared_for, version, job_id)
        elif fmt == "md":
            data, info = _md(title, subtitle, secs, p, prepared_for, version, job_id)
        else:
            sio = io.StringIO()
            csv.writer(sio).writerows([[_plain(c) for c in r] for r in xl[0]["rows"]])
            data, info = sio.getvalue().encode(), {"rows": len(xl[0]["rows"]) - 1, "outline": [xl[0]["name"]]}
    except Exception as e:  # noqa: BLE001 — tools must not raise
        return err(f"render failed: {type(e).__name__}: {e}"[:300])
    if len(data) > MAX_FILE_BYTES:
        return err(f"file too large ({len(data)} bytes, limit {MAX_FILE_BYTES}) — shorten the content")
    file_id = "wf-" + _h(fmt, title, subtitle, secs, xl, p["brand_id"], prepared_for, job_id, version, confidential,
                         n=12)
    name = f"{_slug(title)}{version_tag}.{fmt}"
    st[f"hive_file:{file_id}"] = {"name": name, "mime": MIME[fmt], "size": len(data),
                                  "b64": base64.b64encode(data).decode()}
    counts = {k: info[k] for k in ("pages_est", "slides", "sheets", "rows", "words") if k in info}
    return ok(file_id=file_id, name=name, format=fmt, size=len(data), **counts, outline=info["outline"][:15],
              version=version, brand=p["name"], brand_id=p["brand_id"], job_id=job_id or None, note=note,
              delivered="attached to this session for download")


# --- specialists: SEO -----------------------------------------------------------------------------------------------


@hive_tool("workforce")
def wf_seo_audit(site: str = "kitewing.example", focus: str = "") -> dict:
    """Audit the customer's website from its connected crawl and Search Console snapshot (technical, on-page, content).

    Args:
        site: Customer site (the demo customer's is 'kitewing.example').
        focus: Optional filter: a path fragment ('/blog', '/industries') or an area ('technical', 'on-page',
            'content', 'performance').

    Returns:
        Score 0-100, a scorecard by area, issues sorted by severity (page, issue, impact, fix), quick-win queries
        (position 4-15 with low click-through) and the snapshot date.
    """
    w = fixture("wf_customer_workspace")["website"]
    if _norm(site) and _norm(site) not in _norm(w["site"]) and "kitewing" not in _norm(site):
        return err(f"no connected site {site!r}", sites=[w["site"]])
    pages = w["pages"]
    f = (focus or "").strip().lower()
    area_f = f if f in ("technical", "on-page", "on page", "content", "performance") else ""
    if f and not area_f:
        pages = [pg for pg in pages if f in pg["path"]]
        if not pages:
            return err(f"no pages matching {focus!r}", paths=[pg["path"] for pg in w["pages"]])
    issues = []
    sev_w = {"critical": 8, "high": 4, "medium": 2, "low": 1}

    def add(pg: dict, area: str, sev: str, issue: str, fix: str) -> None:
        issues.append({"page": pg["path"], "area": area, "severity": sev, "issue": issue, "fix": fix})

    titles: dict[str, list[str]] = {}
    targets: dict[str, list[str]] = {}
    for pg in pages:
        titles.setdefault(pg["title"].lower(), []).append(pg["path"])
        targets.setdefault(pg["target_query"], []).append(pg["path"])
        if not pg["indexable"]:
            add(pg, "technical", "critical", "page is set to noindex, so it cannot rank (0 sessions)",
                "remove the noindex tag and resubmit the URL")
        if pg["internal_links_in"] == 0:
            add(pg, "technical", "medium", "orphan page — no internal links point to it",
                "link it from the home page, the product pages and related posts")
        n = len(pg["title"])
        if n > 60:
            add(pg, "on-page", "high", f"title is {n} characters (shows truncated)", "rewrite under 60 characters")
        if not pg["meta"]:
            add(pg, "on-page", "high", "missing meta description", "write 120-155 characters with the target query")
        elif not 70 <= len(pg["meta"]) <= 160:
            add(pg, "on-page", "low", f"meta description is {len(pg['meta'])} characters", "aim for 120-155")
        if not pg["h1"]:
            add(pg, "on-page", "high", "no H1 heading", f"add one H1 with '{pg['target_query']}'")
        if pg["words"] < 300 and pg["indexable"]:
            add(pg, "content", "medium", f"thin content ({pg['words']} words)",
                "expand to 600+ words: how it works, proof, FAQs")
        if pg["lcp_s"] > 4:
            add(pg, "performance", "high", f"slow Largest Contentful Paint {pg['lcp_s']}s",
                "compress the hero image and defer scripts (target under 2.5s)")
        elif pg["lcp_s"] > 2.5:
            add(pg, "performance", "medium", f"Largest Contentful Paint {pg['lcp_s']}s", "target under 2.5s")
        age = (TODAY - dt.date.fromisoformat(pg["last_updated"])).days
        if pg["path"].startswith("/blog") and age > 365:
            add(pg, "content", "medium", f"not updated for {age // 30} months", "refresh facts, examples and links")
    for t, paths in titles.items():
        if len(paths) > 1:
            for pth in paths:
                add(next(x for x in pages if x["path"] == pth), "on-page", "high",
                    f"duplicate title shared with {', '.join(x for x in paths if x != pth)}", "write a unique title")
    for q, paths in targets.items():
        if len(paths) > 1:
            add(next(x for x in pages if x["path"] == paths[1]), "content", "medium",
                f"keyword cannibalisation: '{q}' targeted by {', '.join(paths)}",
                "pick one page for the query; retarget or merge the other and link to it")
    if area_f:
        issues = [i for i in issues if i["area"].replace(" ", "-") == area_f.replace(" ", "-")]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda i: (order[i["severity"]], i["page"]))
    score = max(0, 100 - sum(sev_w[i["severity"]] for i in issues))
    card = {}
    for area in ("technical", "on-page", "content", "performance"):
        found = [i for i in issues if i["area"] == area]
        worst = min((order[i["severity"]] for i in found), default=9)
        card[area] = {"issues": len(found), "status": "critical" if worst <= 0 else "needs work" if worst <= 2 and found
                      else "good"}
    wins = []
    paths = {pg["path"] for pg in pages}
    for q in w["queries"]:
        ctr = q["clicks"] / q["impressions"] * 100 if q["impressions"] else 0
        if q["page"] in paths and 4 <= q["position"] <= 15 and q["impressions"] >= 1000 and ctr < 3:
            wins.append({"query": q["query"], "page": q["page"], "position": q["position"],
                         "impressions": q["impressions"], "ctr_pct": round(ctr, 1),
                         "action": "improve title/meta for click-through and add the query to an H2"})
    wins.sort(key=lambda x: -x["impressions"])
    return ok(site=w["site"], snapshot_date=w["snapshot_date"], source=w["source"], pages_checked=len(pages),
              score=score, scorecard=card, issues=issues[:15], issue_count=len(issues), quick_wins=wins[:6])


@hive_tool("workforce")
def wf_seo_check_draft(primary_keyword: str, title: str, meta_description: str, body: str,
                       secondary_keywords: list[str] | None = None, target_words: int = 0,
                       draft_type: str = "post") -> dict:
    """Check a blog post or a blog post brief for on-page SEO: title, meta, keyword placement, structure, readability.

    Args:
        primary_keyword: The main search query, e.g. 'reduce technician overtime'.
        title: SEO title (under 60 characters).
        meta_description: Meta description (120-155 characters).
        body: The post, or the brief's outline, in markdown ('#'/'##' headings).
        secondary_keywords: Optional related queries that should appear.
        target_words: Optional target word count of a post (0 = no target).
        draft_type: 'post' (full article: density, links, readability, length) or 'brief' (an outline: title, meta,
            H2 structure, keyword coverage and call to action only).

    Returns:
        Score 0-100, passed checks, fixes, keyword density %, secondary keyword coverage and readability. Run it once
        and apply the fixes.
    """
    kw = (primary_keyword or "").strip().lower()
    if not kw or len((body or "").split()) < 30:
        return err("primary_keyword and a body of at least 30 words are required")
    fixes, passed = [], []
    tl, ml = len(title or ""), len(meta_description or "")
    (passed if 0 < tl <= 60 else fixes).append(f"title length {tl} (target 30-60)")
    (passed if kw in (title or "").lower() else fixes).append("primary keyword in the title")
    (passed if 120 <= ml <= 155 else fixes).append(f"meta description length {ml} (target 120-155)")
    (passed if kw in (meta_description or "").lower() else fixes).append("primary keyword in the meta description")
    brief = (draft_type or "post").lower().startswith("brief")
    words = re.findall(r"[A-Za-z0-9'%$-]+", body.lower())
    first100 = " ".join(words[:100])
    if not brief:
        (passed if kw in first100 else fixes).append("primary keyword in the first 100 words")
    else:
        (passed if kw in body.lower() else fixes).append("primary keyword in the outline")
    h2 = re.findall(r"^##\s+(.+)", body, re.M)
    (passed if len(h2) >= 3 else fixes).append(f"{len(h2)} H2 sections (target 3+)")
    (passed if any(kw.split()[0] in h.lower() for h in h2) else fixes).append("keyword theme in at least one H2")
    occurrences = len(re.findall(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", body.lower()))
    density = round(occurrences * len(kw.split()) / max(1, len(words)) * 100, 2)
    if not brief:
        (passed if 0.4 <= density <= 2.5 else fixes).append(f"keyword density {density}% (target 0.4-2.5%)")
    sec = [k for k in (secondary_keywords or []) if k.strip()]
    covered = [k for k in sec if k.lower() in body.lower()]
    if sec:
        (passed if len(covered) >= math.ceil(len(sec) / 2) else fixes).append(
            f"secondary keywords covered {len(covered)}/{len(sec)}")
    if target_words and not brief:
        (passed if abs(len(words) - target_words) <= target_words * 0.2 else fixes).append(
            f"{len(words)} words (target {target_words} ±20%)")
    links = len(re.findall(r"\]\(|(?<![a-z])/[a-z0-9-]+/[a-z0-9-]+", body))
    if not brief:
        (passed if links >= 2 else fixes).append(f"{links} links (target 2+ internal/external)")
    cta = bool(re.search(r"\b(book|request|download|read|join|see|try|talk to|contact|sign up|register|"
                         r"call to action|cta)\b", body.lower() if brief else body.lower()[-600:]))
    (passed if cta else fixes).append("call to action" + ("" if brief else " near the end"))
    stats = _readability(body)
    if stats["flesch_reading_ease"] is not None and not brief:
        (passed if stats["flesch_reading_ease"] >= 50 else fixes).append(
            f"Flesch reading ease {stats['flesch_reading_ease']} (target 50+)")
    score = round(100 * len(passed) / (len(passed) + len(fixes)))
    return ok(score=score, draft_type="brief" if brief else "post", passed=passed, fixes=fixes,
              keyword_density_pct=None if brief else density,
              secondary_missing=[k for k in sec if k not in covered] or None, words=len(words),
              readability=None if brief else stats,
              next_step="Apply the fixes in your text and continue — no need to run the check again.")


# --- specialists: social -------------------------------------------------------------------------------------------


@hive_tool("workforce")
def wf_social_slots(start_date: str, weeks: int = 4, channels: list[str] | None = None,
                    brand: str = "kitewing") -> dict:
    """Plan the posting slots of a social content calendar from the customer's cadence, pillars and key dates.

    Args:
        start_date: First day of the calendar, YYYY-MM-DD (not in the past).
        weeks: Number of weeks, 1-8.
        channels: 'linkedin' and/or 'instagram' (default both).
        brand: Brand whose content pillars and social rules apply (default Kitewing Software).

    Returns:
        Dated slots (date, day, time, channel, pillar, format, campaign moment) with the pillar mix balanced to the
        brand targets, skipped blackout dates, planned vs target pillar shares and the brand's social rules.
    """
    try:
        start = dt.date.fromisoformat(start_date[:10])
    except (TypeError, ValueError):
        return err("start_date must be YYYY-MM-DD")
    if start < TODAY:
        return err(f"start_date is in the past (today is {TODAY.isoformat()})")
    if not 1 <= int(weeks) <= 8:
        return err("weeks must be between 1 and 8")
    soc = fixture("wf_customer_workspace")["social"]
    chans = [c.lower().strip() for c in (channels or ["linkedin", "instagram"]) if c.strip()]
    bad = [c for c in chans if c not in soc["channels"]]
    if bad or not chans:
        return err(f"unknown channels {bad}", channels=list(soc["channels"]))
    p = _brand(brand)
    pillars = (p.get("social") or {}).get("pillars") if p else None
    if not pillars:
        return err("the brand profile has no content pillars")
    blackout = {b["date"]: b["reason"] for b in soc["blackout_dates"]}
    moments = {m["date"]: m for m in soc["content_moments"] if m["approved"]}
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    end = start + dt.timedelta(days=7 * int(weeks) - 1)
    slots, skipped = [], []
    d = start
    while d <= end:
        for c in chans:
            cfg = soc["channels"][c]
            if days[d.weekday()] in cfg["days"]:
                if d.isoformat() in blackout:
                    skipped.append({"date": d.isoformat(), "channel": c, "reason": blackout[d.isoformat()]})
                else:
                    slots.append({"date": d.isoformat(), "day": days[d.weekday()], "time": cfg["time"], "channel": c})
        d += dt.timedelta(days=1)
    used_moments = set()
    for m_date, m in sorted(moments.items()):
        md = dt.date.fromisoformat(m_date)
        if not start <= md <= end:
            continue
        cands = [s for s in slots if "moment" not in s and abs((dt.date.fromisoformat(s["date"]) - md).days) <= 2]
        cands.sort(key=lambda s: (abs((dt.date.fromisoformat(s["date"]) - md).days), s["channel"] != "linkedin"))
        if cands:
            cands[0]["moment"], cands[0]["pillar"] = m["title"], m["pillar"]
            used_moments.add(m_date)
    assigned = {pl["name"]: sum(1 for s in slots if s.get("pillar") == pl["name"]) for pl in pillars}
    for i, s in enumerate(slots):
        if "pillar" in s:
            continue
        deficit = {pl["name"]: pl["share_pct"] / 100 * (i + 1) - assigned[pl["name"]] for pl in pillars}
        best = max(pillars, key=lambda pl: (deficit[pl["name"]], pl["share_pct"]))["name"]
        s["pillar"] = best
        assigned[best] += 1
    fmt_i = {c: 0 for c in chans}
    for s in slots:
        fm = soc["channels"][s["channel"]]["formats"]
        s["format"] = fm[fmt_i[s["channel"]] % len(fm)]
        fmt_i[s["channel"]] += 1
    n = max(1, len(slots))
    mix = [{"pillar": pl["name"], "target_pct": pl["share_pct"], "planned": assigned[pl["name"]],
            "planned_pct": round(100 * assigned[pl["name"]] / n)} for pl in pillars]
    sp = (p.get("social") or {})
    return ok(start=start.isoformat(), end=end.isoformat(), timezone=soc["timezone"], slots=slots, total=len(slots),
              skipped=skipped or None, pillar_mix=mix,
              rules={"hashtags": sp.get("hashtags"), "max_hashtags": sp.get("max_hashtags"),
                     "max_emojis": sp.get("max_emojis"),
                     "linkedin": "hook under 140 characters; 400-1,300 characters; one call to action"},
              channel_stats={c: {k: soc["channels"][c][k] for k in ("followers", "avg_engagement_pct", "best_pillar")}
                             for c in chans})


# --- specialists: operations ----------------------------------------------------------------------------------------

_VAGUE = ["as needed", "asap", "as appropriate", "appropriate", "etc", "quickly", "regularly", "if possible",
          "and so on", "periodically", "when necessary", "properly"]
_NOT_VERB = {"the", "a", "an", "this", "that", "it", "we", "they", "he", "she", "you", "there", "all", "each",
             "every", "our", "your", "their", "step", "next", "then", "after", "before", "once", "when", "sales",
             "customer", "manager", "team"}


@hive_tool("workforce")
def wf_sop_check(steps: list[dict], roles: list[str] | None = None) -> dict:
    """Check the procedure steps of an SOP: imperative verb, one owner, done-when, no vague words, decision branches.

    Args:
        steps: Ordered steps: {"step": "Send the handoff form to implementation", "owner": "Account Executive",
            "system": "CRM" (optional), "done_when": "form status is Submitted"}.
        roles: Optional roles from the RACI table, to find roles that own no step.

    Returns:
        Score 0-100, pass/fail, issues per step number with the fix, owners and step counts, and RACI roles that own
        no step.
    """
    if not steps:
        return err("steps are required")
    issues, owners = [], {}
    for i, s in enumerate(steps, start=1):
        if not isinstance(s, dict):
            s = {"step": str(s)}
        text = str(s.get("step") or s.get("action") or "").strip()
        owner = str(s.get("owner") or "").strip()
        if not text:
            issues.append({"step": i, "issue": "empty step", "fix": "describe the action"})
            continue
        first = re.sub(r"[^A-Za-z]", "", text.split()[0]).lower()
        if first in _NOT_VERB or first.endswith(("ing", "ed")) or (first.endswith("s") and not first.endswith("ss")
                                                                   and first not in ("is", "process")):
            if first != "if":
                issues.append({"step": i, "issue": f"starts with '{text.split()[0]}'",
                               "fix": "start with an imperative verb (Send, Check, Create, Book...)"})
        if len(text.split()) > 30:
            issues.append({"step": i, "issue": f"{len(text.split())} words", "fix": "split into steps of 30 words "
                           "or fewer"})
        if not owner:
            issues.append({"step": i, "issue": "no owner", "fix": "name one accountable role"})
        elif re.search(r"\band\b|/|&|,", owner):
            issues.append({"step": i, "issue": f"several owners ('{owner}')", "fix": "one owner per step; consult "
                           "the others"})
        if not str(s.get("done_when") or "").strip():
            issues.append({"step": i, "issue": "no done-when", "fix": "state the observable result that ends the step"})
        low = text.lower()
        vague = [v for v in _VAGUE if re.search(r"(?<![a-z])" + re.escape(v) + r"(?![a-z])", low)]
        if vague:
            issues.append({"step": i, "issue": f"vague wording: {', '.join(vague)}", "fix": "give a time limit or "
                           "criterion"})
        if low.startswith("if ") and not re.search(r"\b(otherwise|else|if not)\b", low):
            issues.append({"step": i, "issue": "decision without the other branch", "fix": "add 'otherwise ...'"})
        if owner:
            owners[owner] = owners.get(owner, 0) + 1
    idle = [r for r in (roles or []) if r and not any(_norm(r) in _norm(o) or _norm(o) in _norm(r) for o in owners)]
    score = max(0, 100 - 6 * len(issues) - 4 * len(idle))
    return ok(steps=len(steps), score=score, passed=score >= 80 and not any(i["issue"] == "no owner" for i in issues),
              issues=issues[:20], owners=owners, roles_without_steps=idle or None,
              next_step="Apply the fixes in your SOP and continue — no need to run the check again." if issues or idle
              else "All steps pass — continue.")


# --- specialists: strategy ------------------------------------------------------------------------------------------


@hive_tool("workforce")
def wf_market_size(segments: list[dict], currency: str = "USD") -> dict:
    """Size a market bottom-up (TAM, SAM, SOM) per segment from account counts and annual value, with a range.

    Args:
        segments: List of {"name": str, "accounts": number of companies, "annual_value": value per account per year,
            "serviceable_pct": % of accounts you can serve today, "obtainable_pct": % of the serviceable market you
            can win in 3 years, "source": where the account count comes from (URL or 'estimate')}.
        currency: Currency label for the values.

    Returns:
        TAM, SAM and SOM per segment and in total, a low/high SOM range (±20%), the method, and segments whose
        inputs have no source (to be labelled as estimates).
    """
    if not segments:
        return err("segments are required")
    rows, unsourced, problems = [], [], []
    tot = {"tam": 0.0, "sam": 0.0, "som": 0.0}
    for s in segments:
        try:
            name = str(s.get("name") or "segment")
            acc, val = float(s.get("accounts", 0)), float(s.get("annual_value", 0))
            sp, op = float(s.get("serviceable_pct", 100)), float(s.get("obtainable_pct", 0))
        except (TypeError, ValueError, AttributeError):
            problems.append(f"bad numbers in {s!r}"[:120])
            continue
        if acc <= 0 or val <= 0 or not 0 <= sp <= 100 or not 0 <= op <= 100:
            problems.append(f"{name}: accounts and annual_value must be > 0 and percentages 0-100")
            continue
        tam = acc * val
        sam = tam * sp / 100
        som = sam * op / 100
        for k, v in (("tam", tam), ("sam", sam), ("som", som)):
            tot[k] += v
        src = str(s.get("source") or "").strip()
        if not src or "estimate" in src.lower():
            unsourced.append(name)
        rows.append({"segment": name, "accounts": int(acc), "annual_value": round(val, 2), "tam": round(tam),
                     "sam": round(sam), "som": round(som), "som_accounts": round(acc * sp / 100 * op / 100),
                     "source": src or "estimate"})
    if not rows:
        return err("no valid segments", problems=problems)
    return ok(currency=currency, segments=rows, total={k: round(v) for k, v in tot.items()},
              som_range={"low": round(tot["som"] * 0.8), "high": round(tot["som"] * 1.2)},
              method="TAM = accounts x annual value; SAM = TAM x serviceable %; SOM = SAM x obtainable % (3 years)",
              label_as_estimate=unsourced or None, problems=problems or None)

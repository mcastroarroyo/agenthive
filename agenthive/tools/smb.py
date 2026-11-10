"""SMB realm tools — a fictional 62-person B2B software company, Kitewing Software, its customers and prospects.

Kitewing sells Kitewing FieldOps (scheduling, dispatch, mobile work orders and invoicing for service contractors).
Growth tools cover the CRM, discovery playbook, pricing, case studies, security answers, account health, ROI and
brand checks; Operations tools cover estimates, team capacity, risks, project status, retros and AI readiness; People
tools cover onboarding and skills. Data lives in fixtures/smb_*.json (synthetic); actions are simulated.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
import unicodedata

from ._base import err, fixture, hive_tool, ok

TODAY = dt.date(2026, 11, 6)   # the demo's fixed "today" keeps every answer reproducible


# --- helpers ------------------------------------------------------------------------------------------------------


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower().replace("&", " and ")).strip()


def _pick(query: str, items: list[dict], keys: tuple[str, ...] = ("name",)) -> dict | None:
    """Best fuzzy match of `query` against items[key] (exact id, containment either way, then token overlap)."""
    q = _norm(query)
    if not q:
        return None
    for it in items:
        if q == _norm(it.get("id", "")):
            return it
    for it in items:
        for k in keys:
            v = _norm(it.get(k, ""))
            if v and (q == v or q in v or (len(v) > 3 and v in q)):
                return it
    qt = set(q.split()) - {"the", "and", "inc", "co", "group", "services", "of"}
    best, score = None, 0
    for it in items:
        for k in keys:
            n = len(qt & set(_norm(it.get(k, "")).split()))
            if n > score:
                best, score = it, n
    return best


def _date(s: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s)[:10]) if s else None
    except ValueError:
        return None


def _sid(prefix: str, *parts: object, lo: int = 4000, span: int = 5000) -> str:
    h = int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)
    return f"{prefix}-{lo + h % span}"


def _add_bdays(d: dt.date, n: int) -> dt.date:
    step = 1 if n >= 0 else -1
    while n:
        d += dt.timedelta(days=step)
        if d.weekday() < 5:
            n -= step
    return d


def _accounts() -> list[dict]:
    return fixture("smb_crm")["accounts"]


def _account(company: str) -> dict | None:
    return _pick(company, _accounts(), ("name", "id"))


def _named_account(text: str) -> dict | None:
    """The CRM account explicitly named in `text` (by id or by the distinctive first word of its name), else None."""
    acc = _account(text) if text and len(text.strip()) > 2 else None
    if not acc:
        return None
    q = _norm(text)
    return acc if q == _norm(acc["id"]) or _norm(acc["name"]).split()[0] in q.split() else None


_SEGMENT_WORDS = {
    "hvac_plumbing": ["hvac", "plumb", "heating", "cooling", "home service", "electrical", "drain", "mechanical"],
    "facilities": ["facilit", "property", "building", "maintenance group"],
    "fire_security": ["fire", "alarm", "security", "cctv", "access control", "sprinkler", "inspection"],
    "elevator": ["elevator", "escalator", "lift"],
    "pest_landscaping": ["pest", "landscap", "lawn", "snow", "pool", "cleaning", "route"],
}


def _segment(text: str) -> str | None:
    """Resolve a segment key from a key, industry words or a CRM company name."""
    t = (text or "").strip()
    if not t:
        return None
    if t in fixture("smb_sales_playbook")["segments"]:
        return t
    acc = _named_account(t)
    if acc:
        return acc["segment"]
    low = t.lower()
    for seg, words in _SEGMENT_WORDS.items():
        if any(w in low for w in words):
            return seg
    return None


# --- Growth: CRM, discovery and qualification ---------------------------------------------------------------------


@hive_tool("smb")
def smb_crm_lookup(company: str) -> dict:
    """Look up a customer or prospect in Kitewing's CRM: firmographics, contacts, opportunities, activities and notes.

    Args:
        company: Company name (partial is fine, e.g. 'Alderbrook') or account id (e.g. 'P-2001', 'C-1001').

    Returns:
        The CRM record with contacts (role, influence, sentiment), opportunities, recent activities, known pains and
        competitors, plus days since the last touch. Lists known accounts when nothing matches.
    """
    acc = _account(company)
    if not acc:
        return err(f"no CRM account matching {company!r}",
                   accounts=[f"{a['id']} {a['name']} ({a['type']})" for a in _accounts()])
    dates = [d for d in (_date(x["date"]) for x in acc.get("activities", [])) if d]
    last = max(dates) if dates else None
    open_opps = [o for o in acc.get("opportunities", []) if not o["stage"].startswith("Closed")]
    return ok(account=acc, open_opportunities=open_opps,
              days_since_last_activity=(TODAY - last).days if last else None,
              note="All companies are fictional; public web search will not find them.")


_CRIT_ALIASES = {
    "m": "metrics", "metric": "metrics", "eb": "economic_buyer", "economic": "economic_buyer", "buyer": "economic_buyer",
    "dc": "decision_criteria", "criteria": "decision_criteria", "dp": "decision_process", "process": "decision_process",
    "paper": "decision_process", "paper process": "decision_process", "pain": "identify_pain", "i": "identify_pain",
    "identify": "identify_pain", "c": "champion", "coach": "champion", "comp": "competition", "competitors": "competition",
    "competitor": "competition", "b": "budget", "a": "authority", "n": "need", "t": "timeline", "timing": "timeline",
}


def _framework(name: str) -> tuple[str, dict] | None:
    fws = fixture("smb_sales_playbook")["frameworks"]
    key = (name or "MEDDICC").upper().replace("MEDDPICC", "MEDDICC")
    return (key, fws[key]) if key in fws else None


@hive_tool("smb")
def smb_discovery_playbook(framework: str = "MEDDICC", segment: str = "") -> dict:
    """Get Kitewing's discovery playbook: qualification questions, segment pain hypotheses, proof points and call agenda.

    Args:
        framework: 'MEDDICC' (default, deals above $25k ACV) or 'BANT' (small deals and SDR qualification).
        segment: Segment key (hvac_plumbing, facilities, fire_security, elevator, pest_landscaping), industry words
            (e.g. 'HVAC', 'fire alarm') or a CRM company name such as 'Alderbrook Home Services'.

    Returns:
        Criteria with weights, questions and what to listen for; the segment's pains, hypotheses and matching case
        studies; competitor landmine questions; the 30-minute agenda, stage exit criteria and follow-up rules.
    """
    fw = _framework(framework)
    if not fw:
        return err(f"unknown framework {framework!r}", frameworks=list(fixture("smb_sales_playbook")["frameworks"]))
    pb = fixture("smb_sales_playbook")
    seg_key = _segment(segment) if segment else None
    seg = pb["segments"].get(seg_key) if seg_key else None
    cases = {c["id"]: c for c in fixture("smb_case_studies")["case_studies"]}
    proof = []
    if seg:
        for cid in seg["proof_points"]:
            c = cases[cid]
            proof.append({"id": cid, "customer": c["customer"] if c["public"] else c.get("public_name", "anonymised"),
                          "public": c["public"], "headline_metrics": c["metrics"]})
    acc = _named_account(segment) if segment else None
    landmines = {}
    if acc and acc["type"] == "prospect":
        for comp in acc.get("competitors", []):
            for name, info in pb["competitors"].items():
                if name.lower() in comp.lower():
                    landmines[name] = info
    return ok(framework=fw[0], description=fw[1]["description"], criteria=fw[1]["criteria"],
              segment=seg_key, segment_playbook=seg, proof_points=proof,
              competitor_landmines=landmines or pb["competitors"], call_agenda=pb["call_agenda_30min"],
              stages=pb["stages"], follow_up_rules=pb["follow_up_rules"],
              segments_available=list(pb["segments"]) if not seg else None)


@hive_tool("smb")
def smb_score_qualification(framework: str, scores: list[dict]) -> dict:
    """Score a deal's qualification (MEDDICC or BANT) from evidence and recommend the stage, gaps and next questions.

    Args:
        framework: 'MEDDICC' or 'BANT'.
        scores: One entry per criterion: {"criterion": "metrics", "score": 0-3, "evidence": "buyer's words"}.
            Scale: 0 unknown, 1 weak/assumed, 2 partially confirmed, 3 confirmed by the buyer. MEDDICC criteria:
            metrics, economic_buyer, decision_criteria, decision_process, identify_pain, champion, competition.
            Missing criteria count as 0.

    Returns:
        Weighted qualification %, verdict, recommended stage, per-criterion table, red flags and the next questions
        for every gap.
    """
    fw = _framework(framework)
    if not fw:
        return err(f"unknown framework {framework!r}; use MEDDICC or BANT")
    crit = {c["id"]: c for c in fw[1]["criteria"]}
    given: dict[str, dict] = {}
    unknown = []
    for s in scores or []:
        raw = _norm(s.get("criterion", "")).replace(" ", "_")
        cid = raw if raw in crit else _CRIT_ALIASES.get(raw.replace("_", " "), _CRIT_ALIASES.get(raw))
        if cid not in crit:
            cid = next((k for k in crit if raw and (raw in k or k in raw)), None)
        if cid not in crit:
            unknown.append(s.get("criterion"))
            continue
        try:
            sc = max(0, min(3, int(round(float(s.get("score", 0))))))
        except (TypeError, ValueError):
            sc = 0
        given[cid] = {"score": sc, "evidence": str(s.get("evidence", "")).strip()}
    rows, total_w, got = [], 0, 0.0
    for cid, c in crit.items():
        g = given.get(cid, {"score": 0, "evidence": ""})
        total_w += c["weight"]
        got += c["weight"] * g["score"] / 3
        rows.append({"criterion": cid, "name": c["name"], "weight": c["weight"], "score": g["score"],
                     "evidence": g["evidence"] or "(none)"})
    pct = round(100 * got / total_w, 1)
    flags = []
    by = {r["criterion"]: r for r in rows}
    if fw[0] == "MEDDICC":
        if by["economic_buyer"]["score"] <= 1:
            flags.append("No confirmed economic buyer — get a meeting before a proposal.")
        if by["identify_pain"]["score"] <= 1:
            flags.append("Pain not quantified or not urgent — risk of 'no decision'.")
        if by["champion"]["score"] <= 1:
            flags.append("No tested champion — nobody is selling for us internally.")
        if by["decision_process"]["score"] <= 1:
            flags.append("No dated decision process (incl. legal/security review).")
    flags += [f"{r['name']} scored {r['score']} without evidence." for r in rows if r["score"] >= 2 and
              r["evidence"] == "(none)"]
    gaps = sorted([r for r in rows if r["score"] <= 1], key=lambda r: -r["weight"])
    next_q = [{"criterion": g["name"], "ask": crit[g["criterion"]]["questions"][:2]} for g in gaps]
    if pct >= 75:
        verdict, stage = "Qualified — advance", "Solution Validation"
    elif pct >= 50:
        verdict, stage = "Qualified with gaps — keep in Discovery and close the gaps", "Discovery"
    else:
        verdict, stage = "Not yet qualified — more discovery or nurture", "Discovery"
    return ok(framework=fw[0], qualification_pct=pct, verdict=verdict, recommended_stage=stage, criteria=rows,
              red_flags=flags, gaps=[g["name"] for g in gaps], next_questions=next_q,
              ignored_criteria=unknown or None)


_STAGES = [s["name"] for s in fixture("smb_sales_playbook")["stages"]]


@hive_tool("smb", kind="action")
def smb_log_opportunity(company: str, opportunity_name: str, stage: str, amount_usd: float, close_date: str,
                        next_step: str, qualification_pct: float = 0.0, summary: str = "") -> dict:
    """Create or update an opportunity in the CRM with stage, amount, close date, next step and summary (simulated).

    Args:
        company: CRM company name or account id.
        opportunity_name: e.g. 'Alderbrook — FieldOps Growth (140 techs)'.
        stage: One of Prospecting, Discovery, Solution Validation, Proposal, Negotiation, Closed Won, Closed Lost.
        amount_usd: Expected first-year contract value (ACV).
        close_date: Expected close date, YYYY-MM-DD.
        next_step: The dated next step agreed with the buyer.
        qualification_pct: MEDDICC/BANT score from smb_score_qualification.
        summary: Short opportunity summary for the CRM.

    Returns:
        Opportunity id, whether it was created or updated, stage probability and weighted pipeline value.
    """
    acc = _account(company)
    if not acc:
        return err(f"no CRM account matching {company!r}")
    st = next((s for s in _STAGES if _norm(s) == _norm(stage)), None)
    if not st:
        return err(f"unknown stage {stage!r}", stages=_STAGES)
    cd = _date(close_date)
    if not cd or cd < TODAY:
        return err("close_date must be YYYY-MM-DD and not in the past")
    if amount_usd <= 0:
        return err("amount_usd must be positive")
    prob = next(s["probability_pct"] for s in fixture("smb_sales_playbook")["stages"] if s["name"] == st)
    open_opps = [o for o in acc.get("opportunities", []) if not o["stage"].startswith("Closed")]
    existing = _pick(opportunity_name, open_opps, ("name",)) if open_opps else None
    opp_id = existing["id"] if existing else _sid("OPP", acc["id"], opportunity_name, lo=3200, span=700)
    return ok(opportunity_id=opp_id, action="updated" if existing else "created", account=acc["name"],
              name=opportunity_name, stage=st, previous_stage=existing["stage"] if existing else None,
              amount_usd=round(amount_usd, 2), probability_pct=prob,
              weighted_usd=round(amount_usd * prob / 100, 2), close_date=cd.isoformat(), next_step=next_step,
              qualification_pct=qualification_pct, summary=summary[:600], owner=acc.get("account_owner"),
              simulated=True)


@hive_tool("smb", kind="action")
def smb_save_email_draft(to: list[str], subject: str, body: str, cc: list[str] | None = None) -> dict:
    """Save an email as a draft in the user's mailbox for review — never sends it (simulated).

    Args:
        to: Recipient email addresses.
        subject: Subject line.
        body: Plain-text body.
        cc: Optional CC addresses.

    Returns:
        Draft id, recipients, word count and a reminder that the user must review and send it.
    """
    rx = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
    bad = [a for a in [*(to or []), *(cc or [])] if not rx.match(a.strip())]
    if not to or bad:
        return err("invalid or missing recipients", invalid=bad)
    if not subject.strip() or len(body.split()) < 5:
        return err("subject and a body of at least 5 words are required")
    return ok(draft_id=_sid("DRAFT", *to, subject), to=to, cc=cc or [], subject=subject,
              words=len(body.split()), draft_state="saved as draft — review and send it yourself", simulated=True)


# --- Growth: presales -----------------------------------------------------------------------------------------------


def _addon_key(name: str) -> str | None:
    n = _norm(name)
    if "route" in n or "optim" in n:
        return "Route Optimizer"
    if "assist" in n or n in ("ai", "copilot", "gemini") or "copilot" in n:
        return "Assist"
    if "insight" in n or "analytic" in n or "bigquery" in n:
        return "Insights"
    return None


@hive_tool("smb")
def smb_price_quote(plan: str, technicians: int, addons: list[str] | None = None, billing: str = "annual",
                    term_years: int = 1, discount_pct: float = 0.0, implementation: str = "",
                    migration_sources: int = 0, nonprofit: bool = False) -> dict:
    """Price a Kitewing FieldOps quote with the official price book, discount rules and approval matrix.

    Args:
        plan: 'Starter', 'Growth' or 'Enterprise'.
        technicians: Number of licensed field technicians.
        addons: Optional add-ons: 'Route Optimizer', 'Assist' (AI copilot on Gemini), 'Insights' (BigQuery analytics).
        billing: 'annual' (list price), 'quarterly' (Growth/Enterprise, ACV >= $50k) or 'monthly' (Starter/Growth).
        term_years: Contract term 1-3 years (2 years: 3% off, 3 years: 6% off subscription).
        discount_pct: Extra discretionary discount % on subscription (AE up to 10, VP Sales up to 20, deal desk 30).
        implementation: 'QuickStart', 'Standard' or 'Premium'; empty picks the package that fits the size.
        migration_sources: Number of legacy systems to migrate data from ($3,500 each).
        nonprofit: True for registered nonprofits (10% off subscription).

    Returns:
        Line items, subscription ACV after discounts, implementation fees, first-year total, TCV, effective price per
        technician per month, required approver and warnings.
    """
    pr = fixture("smb_pricing")
    p_name = next((k for k in pr["plans"] if k.lower() == (plan or "").strip().lower()), None)
    if not p_name:
        return err(f"unknown plan {plan!r}", plans=list(pr["plans"]))
    p = pr["plans"][p_name]
    if technicians < 1:
        return err("technicians must be >= 1")
    if p["max_techs"] and technicians > p["max_techs"]:
        return err(f"{p_name} allows at most {p['max_techs']} technicians", suggestion="Growth" if p_name == "Starter"
                   else "Enterprise")
    if technicians < p["min_techs"]:
        return err(f"{p_name} requires at least {p['min_techs']} technicians")
    billing = (billing or "annual").lower()
    if billing not in p["billing"]:
        return err(f"{p_name} does not offer {billing} billing", billing_options=p["billing"])
    if not 1 <= term_years <= 3:
        return err("term_years must be 1, 2 or 3")
    warnings, lines = [], []
    per_tech = p["per_tech_month_monthly"] if billing == "monthly" else p["per_tech_month_annual"]
    lines.append({"item": f"{p_name} plan", "unit": "per technician per month", "unit_price": per_tech,
                  "qty": technicians, "annual_usd": per_tech * technicians * 12})
    for a in addons or []:
        key = _addon_key(a)
        if not key:
            warnings.append(f"unknown add-on {a!r} ignored")
            continue
        info = pr["addons"][key]
        if p_name in info.get("included_in", []):
            lines.append({"item": key, "unit": "included", "unit_price": 0, "qty": 1, "annual_usd": 0})
            continue
        if p_name not in info["eligible_plans"]:
            warnings.append(f"{key} is not available on {p_name} (needs {', '.join(info['eligible_plans'])})")
            continue
        if "per_tech_month" in info:
            lines.append({"item": key, "unit": "per technician per month", "unit_price": info["per_tech_month"],
                          "qty": technicians, "annual_usd": info["per_tech_month"] * technicians * 12})
        else:
            lines.append({"item": key, "unit": "flat per month", "unit_price": info["flat_month"], "qty": 1,
                          "annual_usd": info["flat_month"] * 12})
    list_annual = sum(li["annual_usd"] for li in lines)
    d = pr["discounts"]
    vol = next((v["pct"] for v in d["volume"] if technicians >= v["min_techs"] and
                (v["max_techs"] is None or technicians <= v["max_techs"])), 0)
    my = d["multi_year"].get(str(term_years), 0)
    npf = d["nonprofit_pct"] if nonprofit else 0
    std = list_annual * (1 - vol / 100) * (1 - my / 100) * (1 - npf / 100)
    if discount_pct < 0:
        return err("discount_pct cannot be negative")
    acv = std * (1 - discount_pct / 100)
    total_disc = 0 if not list_annual else round(100 * (1 - acv / list_annual), 1)
    approver = next((a["approver"] for a in d["discretionary_approval"] if discount_pct <= a["max_pct"]), None)
    if approver is None:
        warnings.append("Discretionary discount above 30% is not allowed.")
        approver = "Not allowed"
    if total_disc > d["max_total_subscription_discount_pct"]:
        warnings.append(f"Total subscription discount {total_disc}% exceeds the 35% cap.")
    if billing == "quarterly" and acv < 50000:
        warnings.append("Quarterly billing requires ACV of $50,000 or more.")
    impl_key = next((k for k in ("QuickStart", "Standard", "Premium") if k.lower() == implementation.strip().lower()),
                    None) if implementation else None
    if not impl_key:
        impl_key = "Premium" if p_name == "Enterprise" or technicians > 150 else \
            "Standard" if technicians > 25 or p_name == "Growth" else "QuickStart"
    impl = pr["implementation"][impl_key]
    if impl["max_techs"] and technicians > impl["max_techs"]:
        warnings.append(f"{impl_key} implementation covers up to {impl['max_techs']} technicians; consider Premium.")
    impl_fee = impl["fee_usd"] + max(0, migration_sources) * pr["implementation"]["data_migration_per_source_usd"]
    return ok(plan=p_name, technicians=technicians, billing=billing, term_years=term_years, line_items=lines,
              subscription_list_annual_usd=round(list_annual, 2),
              discounts_pct={"volume": vol, "multi_year": my, "nonprofit": npf, "discretionary": discount_pct,
                             "total_effective": total_disc},
              subscription_acv_usd=round(acv, 2), tcv_subscription_usd=round(acv * term_years, 2),
              implementation={"package": impl_key, "fee_usd": impl["fee_usd"],
                              "data_migration_usd": impl_fee - impl["fee_usd"], "total_usd": impl_fee,
                              "duration_weeks": impl["duration_weeks"], "includes": impl["includes"]},
              first_year_total_usd=round(acv + impl_fee, 2),
              effective_per_tech_month_usd=round(acv / technicians / 12, 2),
              approval_required=approver, warnings=warnings, price_book_effective=pr["effective"],
              terms=pr["terms"]["payment"])


@hive_tool("smb")
def smb_find_case_studies(industry: str = "", keyword: str = "", public_only: bool = False) -> dict:
    """Find Kitewing customer case studies by industry and/or outcome keyword, with metrics and usage permissions.

    Args:
        industry: Segment key, industry words (e.g. 'HVAC', 'facilities', 'fire') or a CRM company name.
        keyword: Outcome or product keyword, e.g. 'drive time', 'inspection', 'Assist', 'DSO'.
        public_only: True to return only stories approved for public use (social posts, websites).

    Returns:
        Matching case studies (challenge, solution, before/after metrics, quote) and whether the customer may be
        named publicly; falls back to all public stories when nothing matches.
    """
    cs = fixture("smb_case_studies")["case_studies"]
    seg = _segment(industry) if industry else None
    kw = _norm(keyword)
    hits = []
    for c in cs:
        if seg and c["segment"] != seg:
            continue
        if kw:
            blob = _norm(" ".join([*c["keywords"], c["challenge"], c["solution"], *c["products"],
                                   *[m["metric"] for m in c["metrics"]]]))
            if not any(w in blob for w in kw.split() if len(w) > 2):
                continue
        if public_only and not c["public"]:
            continue
        hits.append(c)
    fallback = False
    if not hits:
        hits, fallback = [c for c in cs if c["public"]], True
    out = [{**{k: v for k, v in c.items() if k != "keywords"},
            "usage_rule": "May be named publicly" if c["public"] else
            f"Do NOT name publicly — refer to it as '{c.get('public_name', 'a customer')}' or keep internal"}
           for c in hits]
    return ok(case_studies=out, count=len(out), fallback_all_public=fallback)


@hive_tool("smb")
def smb_security_answer(question: str) -> dict:
    """Answer a security-questionnaire question from Kitewing's approved answer bank, with confidence and owner.

    Args:
        question: The customer's question in English (translate it first if it is in another language), e.g. 'Do
            you support SAML SSO?' or 'Is our data used to train AI models?'.

    Returns:
        The best 1-2 approved answers with topic, id and confidence (high / medium / low); low confidence means
        escalate to the Sales Engineer instead of improvising.
    """
    bank = fixture("smb_security_answers")
    q = " " + _norm(question) + " "
    if len(q.strip()) < 4:
        return err("question too short")
    scored = []
    for a in bank["answers"]:
        s = sum(len(k.split()) + 1 for k in a["keywords"] if f" {_norm(k)} " in q)
        if s:
            scored.append((s, a))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return ok(matches=[], confidence="low", escalate_to=bank["owner"],
                  note="No approved answer — do not improvise; escalate.")
    top = scored[0][0]
    conf = "high" if top >= 4 else "medium" if top >= 2 else "low"
    matches = [{"id": a["id"], "topic": a["topic"], "answer": a["answer"], "match_score": s}
               for s, a in scored[:2] if s >= top / 2]
    return ok(matches=matches, confidence=conf, last_reviewed=bank["last_reviewed"],
              escalate_to=bank["owner"] if conf == "low" else None)


# --- Growth: account 360 and ROI ------------------------------------------------------------------------------------


def _clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


@hive_tool("smb")
def smb_account_360(company: str) -> dict:
    """Build a 360-degree index of a customer account: health score, stakeholder map, risks, renewal and whitespace.

    Args:
        company: Customer name or id (e.g. 'Harbor & Pine Mechanical', 'C-1003').

    Returns:
        Health score 0-100 with band and component breakdown (usage, support, financial, relationship, sentiment),
        risk signals, stakeholder map, renewal countdown, open tickets, overdue invoices, usage trend and whitespace
        (expansion opportunities with estimated ACV at list price).
    """
    acc = _account(company)
    if not acc:
        return err(f"no account matching {company!r}")
    if acc["type"] != "customer":
        return err(f"{acc['name']} is a prospect — use smb_crm_lookup for prospects")
    act = fixture("smb_account_activity")["accounts"].get(acc["id"])
    if not act:
        return err(f"no activity data for {acc['name']}")
    pr = fixture("smb_pricing")
    since90 = TODAY - dt.timedelta(days=90)
    signals = []
    # usage
    u = act["usage"]
    ratio = u[-1]["active"] / max(1, u[-1]["licensed"])
    trend = (u[-1]["active"] - u[0]["active"]) / max(1, u[0]["active"])
    usage = _clamp(100 * ratio + 100 * min(trend, 0.05))
    if trend <= -0.1:
        signals.append(f"Active technicians down {abs(round(trend * 100))}% in 6 months ({u[0]['active']} -> "
                       f"{u[-1]['active']} of {u[-1]['licensed']} licensed).")
    # support
    t = act["tickets"]
    open_t = [x for x in t if x["status"] != "resolved"]
    recent = [x for x in t if _date(x["opened"]) >= since90]
    csats = [x["csat"] for x in t if x.get("csat")]
    avg_csat = round(sum(csats) / len(csats), 2) if csats else None
    support = 100 - 30 * sum(x["priority"] == "P1" for x in open_t) - 15 * sum(x["priority"] == "P2" for x in open_t)
    support -= 5 * max(0, len(recent) - 3)
    if avg_csat is not None and avg_csat < 4:
        support -= (4 - avg_csat) * 10
    support = _clamp(support)
    for x in open_t:
        if x["priority"] in ("P1", "P2"):
            signals.append(f"Open {x['priority']} {x['id']}: {x['subject']} (since {x['opened']}).")
    # financial
    overdue = []
    for inv in act["invoices"]:
        due = _date(inv["due"])
        if inv["status"] != "paid" and due and due < TODAY:
            overdue.append({**inv, "days_overdue": (TODAY - due).days})
    worst = max((o["days_overdue"] for o in overdue), default=0)
    financial = 100 - (50 if worst > 30 else 25 if worst > 0 else 0)
    for o in overdue:
        signals.append(f"Invoice {o['id']} (${o['amount_usd']:,}) overdue {o['days_overdue']} days.")
    # relationship
    qbr_days = (TODAY - _date(act["last_qbr"])).days if act.get("last_qbr") else 999
    rel = 100 if qbr_days <= 120 else 75 if qbr_days <= 180 else 50 if qbr_days <= 270 else 30
    if not act.get("exec_sponsor_engaged"):
        rel -= 15
        signals.append("Executive sponsor not engaged.")
    champs = [c for c in acc["contacts"] if c["role"] == "champion"]
    if not champs:
        rel -= 25
        signals.append("No active champion in the CRM.")
    elif any(c["sentiment"] == "negative" for c in champs):
        rel -= 25
        signals.append(f"Champion sentiment negative ({', '.join(c['name'] for c in champs)}).")
    if qbr_days > 180:
        signals.append(f"No QBR for {qbr_days} days (last {act['last_qbr']}).")
    unknown_eb = [c["name"] for c in acc["contacts"] if c["role"] == "economic_buyer" and not c.get("last_contact")]
    if unknown_eb:
        signals.append(f"Economic buyer never met: {', '.join(unknown_eb)}.")
    rel = _clamp(rel)
    # sentiment
    sval = {"positive": 100, "neutral": 60, "negative": 10}
    em = [e for e in act["emails"] if _date(e["date"]) >= since90] or act["emails"][:1]
    sentiment = round(sum(sval.get(e["sentiment"], 60) for e in em) / max(1, len(em)), 1)
    comp = {"usage": (usage, 30), "support": (support, 25), "financial": (financial, 15),
            "relationship": (rel, 20), "sentiment": (sentiment, 10)}
    score = round(sum(v * w for v, w in comp.values()) / 100)
    band = "Healthy" if score >= 80 else "Watch" if score >= 60 else "At risk"
    # whitespace
    plan = pr["plans"][acc["plan"]]
    per_tech_now = plan["per_tech_month_annual"] + sum(pr["addons"][a].get("per_tech_month", 0) for a in acc["addons"])
    ws = []
    gap = acc["technicians"] - acc["licensed_technicians"]
    starter_capped = acc["plan"] == "Starter" and acc["technicians"] > plan["max_techs"]
    if gap > 0 and not starter_capped:
        ws.append({"play": f"License {gap} unlicensed technicians", "est_acv_usd": gap * per_tech_now * 12,
                   "why": f"{acc['technicians']} technicians, {acc['licensed_technicians']} licensed"})
    blob = " ".join([acc.get("notes", ""), *[a["summary"] for a in acc.get("activities", [])],
                     *[e["snippet"] for e in act["emails"]], *[x["subject"] for x in t]]).lower()
    if starter_capped:
        growth = pr["plans"]["Growth"]["per_tech_month_annual"]
        ws.append({"play": f"Upgrade Starter -> Growth and license all {acc['technicians']} technicians",
                   "est_acv_usd": acc["technicians"] * growth * 12 - acc["arr_usd"],
                   "why": f"Starter caps at {plan['max_techs']} technicians ({gap} unlicensed today); recurring "
                          "service agreements need Growth"})
    if acc["plan"] == "Growth" and acc["technicians"] >= 50 and any(k in blob for k in ("sso", "multi-branch",
                                                                                       "branch-level", "permissions")):
        ent = pr["plans"]["Enterprise"]["per_tech_month_annual"] - plan["per_tech_month_annual"]
        saved = 600 * 12 if "Insights" in acc["addons"] else 0
        ws.append({"play": "Upgrade Growth -> Enterprise (SSO, multi-branch permissions)",
                   "est_acv_usd": acc["licensed_technicians"] * ent * 12 - saved,
                   "why": "Customer asked for SSO / branch permissions"})
    for name, info in pr["addons"].items():
        if name in acc["addons"] or acc["plan"] in info.get("included_in", []):
            continue
        if acc["plan"] not in info["eligible_plans"]:
            continue
        val = info.get("per_tech_month", 0) * acc["licensed_technicians"] * 12 or info.get("flat_month", 0) * 12
        ws.append({"play": f"Add {name}", "est_acv_usd": val, "why": info["description"]})
    days_to_renewal = (_date(acc["renewal_date"]) - TODAY).days
    if days_to_renewal <= 120:
        signals.append(f"Renewal in {days_to_renewal} days ({acc['renewal_date']}).")
    stake = sorted(acc["contacts"], key=lambda c: {"high": 0, "medium": 1, "low": 2}.get(c["influence"], 3))
    return ok(account={k: acc[k] for k in ("id", "name", "industry", "plan", "addons", "technicians",
                                           "licensed_technicians", "arr_usd", "customer_since", "renewal_date",
                                           "account_owner", "csm")},
              health={"score": score, "band": band,
                      "components": {k: {"score": round(v, 1), "weight_pct": w} for k, (v, w) in comp.items()},
                      "avg_csat": avg_csat, "method": "weighted: usage 30, support 25, relationship 20, financial 15, "
                                                      "email sentiment 10"},
              risk_signals=signals,
              stakeholders=[{**c, "days_since_contact": (TODAY - _date(c["last_contact"])).days
                             if c.get("last_contact") else None} for c in stake],
              renewal={"date": acc["renewal_date"], "days_to_renewal": days_to_renewal},
              open_opportunities=acc.get("opportunities", []), open_tickets=open_t, overdue_invoices=overdue,
              usage_trend=u, recent_emails=act["emails"][:4],
              whitespace={"plays": sorted(ws, key=lambda w: -w["est_acv_usd"]),
                          "total_est_acv_usd": sum(w["est_acv_usd"] for w in ws),
                          "basis": "list prices, before volume or multi-year discounts"})


@hive_tool("smb")
def smb_estimate_benefits(segment: str, technicians: int = 0, drive_hours_per_tech_day: float = 0.0,
                          jobs_per_tech_day: float = 0.0, first_time_fix_rate_pct: float = 0.0,
                          overtime_pct: float = 0.0, office_staff: int = 0, annual_revenue_usd: float = 0.0,
                          dso_days: float = 0.0, loaded_tech_hourly_usd: float = 0.0,
                          with_route_optimizer: bool = True, with_assist: bool = False) -> dict:
    """Estimate the annual business benefit of Kitewing FieldOps from a prospect's baseline (benchmarks fill gaps).

    Args:
        segment: Segment key, industry words (e.g. 'HVAC') or a CRM company name (e.g. 'Alderbrook Home Services' —
            then technicians and revenue default to the CRM values).
        technicians: Field technicians (0 = take from the CRM when a company is given).
        drive_hours_per_tech_day: Driving hours per technician per day (0 = segment benchmark).
        jobs_per_tech_day: Completed jobs per technician per day (0 = benchmark).
        first_time_fix_rate_pct: Today's first-time-fix rate in % (0 = benchmark).
        overtime_pct: Overtime as % of technician hours (0 = benchmark).
        office_staff: Dispatchers and office/billing staff (0 = estimate 1 per 7 technicians).
        annual_revenue_usd: Annual revenue, used for the cash (DSO) lever (0 = CRM value or lever skipped).
        dso_days: Days sales outstanding today (0 = benchmark).
        loaded_tech_hourly_usd: Fully loaded technician cost per hour (0 = benchmark).
        with_route_optimizer: Include the Route Optimizer add-on (bigger drive-time lever).
        with_assist: Include Kitewing Assist (extra first-time-fix gain).

    Returns:
        Benefit by lever with formulas and inputs (flagging which came from benchmarks), total annual benefit,
        conservative/expected/stretch scenarios and an estimate of internal one-off effort for the investment.
    """
    bm = fixture("smb_roi_benchmarks")
    seg = _segment(segment)
    if not seg:
        return err(f"cannot resolve segment from {segment!r}", segments=list(bm["segments"]))
    b, imp = bm["segments"][seg], bm["improvements"]
    acc = _named_account(segment)
    used = []

    def pick(val: float, key: str, label: str) -> float:
        if val and val > 0:
            return float(val)
        used.append(label)
        return float(b[key])

    techs = technicians or (acc or {}).get("technicians", 0)
    if not techs:
        return err("technicians is required (or give a CRM company name)")
    rev = annual_revenue_usd or (acc or {}).get("annual_revenue_usd", 0)
    drive = pick(drive_hours_per_tech_day, "drive_hours_per_tech_day", "drive hours/day")
    jobs = pick(jobs_per_tech_day, "jobs_per_tech_day", "jobs/tech/day")
    ftf = pick(first_time_fix_rate_pct, "first_time_fix_rate_pct", "first-time-fix %")
    ot = pick(overtime_pct, "overtime_pct", "overtime %")
    dso = pick(dso_days, "dso_days", "DSO")
    rate = pick(loaded_tech_hourly_usd, "loaded_tech_hourly_usd", "loaded hourly cost")
    staff = office_staff or (acc or {}).get("office_staff", 0) or max(1, round(techs / 7))
    if not office_staff and not (acc or {}).get("office_staff"):
        used.append("office staff (1 per 7 technicians)")
    wd, real = bm["workdays_per_year"], bm["realisation_factor"]
    drive_red = imp["drive_time_reduction_pct"]["value"] if with_route_optimizer else \
        imp["drive_time_reduction_pct_without_route_optimizer"]["value"]
    gain = imp["first_time_fix_gain_pts"]["value"] + (imp["assist_extra_ftf_pts"]["value"] if with_assist else 0)
    gain = max(0.0, min(gain, 95 - ftf))
    levers = []
    hrs = techs * drive * wd * drive_red / 100
    levers.append({"lever": "Drive time", "annual_usd": round(hrs * rate * real),
                   "formula": f"{techs} techs x {drive} h/day x {wd} days x {drive_red}% x ${rate}/h x {real} realisation",
                   "hours_freed": round(hrs)})
    visits = techs * jobs * wd * gain / 100
    levers.append({"lever": "First-time fix (repeat visits avoided)", "annual_usd": round(visits * b["repeat_visit_cost_usd"] * real),
                   "formula": f"{techs} x {jobs} jobs/day x {wd} days x +{gain} pts x ${b['repeat_visit_cost_usd']}/visit x {real}",
                   "visits_avoided": round(visits)})
    ot_hrs = techs * 2080 * ot / 100 * imp["overtime_reduction_pct"]["value"] / 100
    levers.append({"lever": "Overtime premium", "annual_usd": round(ot_hrs * rate * imp["overtime_premium"]["value"]),
                   "formula": f"{techs} x 2080 h x {ot}% OT x {imp['overtime_reduction_pct']['value']}% less x ${rate} x "
                              f"{imp['overtime_premium']['value']} premium", "overtime_hours_avoided": round(ot_hrs)})
    adm = staff * b["admin_hours_per_staff_week"] * 48 * imp["admin_time_reduction_pct"]["value"] / 100
    levers.append({"lever": "Office & dispatch admin time", "annual_usd": round(adm * b["admin_hourly_usd"] * real),
                   "formula": f"{staff} staff x {b['admin_hours_per_staff_week']} h/week x 48 weeks x "
                              f"{imp['admin_time_reduction_pct']['value']}% x ${b['admin_hourly_usd']}/h x {real}"})
    cash = 0.0
    if rev:
        cash = rev * imp["dso_reduction_days"]["value"] / 365
        levers.append({"lever": "Faster invoicing (DSO)", "annual_usd": round(cash * imp["cost_of_capital_pct"]["value"] / 100),
                       "formula": f"${rev:,.0f} revenue x {imp['dso_reduction_days']['value']} days / 365 x "
                                  f"{imp['cost_of_capital_pct']['value']}% cost of capital",
                       "one_time_cash_released_usd": round(cash)})
    else:
        used.append("DSO lever skipped (no revenue given)")
    total = sum(lv["annual_usd"] for lv in levers)
    internal = techs * imp["internal_training_hours_per_tech"]["value"] * rate + \
        staff * imp["internal_hours_per_office_staff"]["value"] * b["admin_hourly_usd"]
    return ok(segment=seg, company=(acc or {}).get("name"), technicians=techs,
              baseline={"drive_hours_per_tech_day": drive, "jobs_per_tech_day": jobs, "first_time_fix_rate_pct": ftf,
                        "overtime_pct": ot, "office_staff": staff, "dso_days": dso, "loaded_tech_hourly_usd": rate,
                        "annual_revenue_usd": rev or None},
              from_benchmarks=used, levers=levers, total_annual_benefit_usd=total,
              scenarios={k: round(total * f) for k, f in bm["scenarios"].items()},
              internal_one_off_effort_usd=round(internal),
              assumptions={k: v for k, v in imp.items()}, realisation_note=bm["realisation_note"],
              next_step="Add the implementation fee from smb_price_quote to internal effort as the investment, use the "
                        "subscription ACV as annual run cost, then call compute_roi.")


# --- Growth: social & brand -----------------------------------------------------------------------------------------


@hive_tool("smb")
def smb_company_news(since: str = "", kind: str = "", include_internal: bool = False) -> dict:
    """List recent Kitewing company news approved for social posts, plus content pillars and the next posting slots.

    Args:
        since: Only items on/after this date (YYYY-MM-DD).
        kind: Optional filter: product, customer_story, culture, event, insight.
        include_internal: True to also list internal-only items (marked DO NOT POST).

    Returns:
        News items with approval flags, brand voice, content pillars with target shares, cadence and the next six
        LinkedIn posting slots.
    """
    m = fixture("smb_marketing")
    since_d = _date(since)
    items = []
    for n in m["news"]:
        if since_d and _date(n["date"]) < since_d:
            continue
        if kind and kind.lower() not in n["kind"]:
            continue
        if not n["approved_for_social"] and not include_internal:
            continue
        items.append({**n, "post_status": "approved" if n["approved_for_social"] else "DO NOT POST"})
    slots, d = [], TODAY
    while len(slots) < 6:
        d += dt.timedelta(days=1)
        if d.weekday() in (1, 2, 3):
            slots.append(f"{d.isoformat()} ({d.strftime('%a')}) 08:30")
    return ok(news=items, voice=m["brand"]["voice"], pillars=m["brand"]["pillars"], cadence=m["brand"]["cadence"],
              approved_hashtags=m["brand"]["approved_hashtags"], next_slots=slots)


_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")


@hive_tool("smb")
def smb_brand_check(text: str, channel: str = "linkedin") -> dict:
    """Check one social post against Kitewing's brand rules and return a score with blocking issues and fixes.

    Args:
        text: The full post text (one post per call).
        channel: Currently 'linkedin'.

    Returns:
        Score 0-100, pass/fail (pass = no blocking issues and score >= 80), blocking issues (banned words, unapproved
        names, unsourced claims, too many hashtags) and warnings (length, hook, CTA, emojis, product naming).
    """
    br = fixture("smb_marketing")["brand"]
    if not text or len(text.strip()) < 20:
        return err("text too short to check")
    li = br["linkedin"]
    low = text.lower()
    block, warn = [], []
    n = len(text)
    if n > li["hard_max_chars"]:
        block.append(f"{n} characters — over the {li['hard_max_chars']} hard limit.")
    elif n > li["ideal_max_chars"]:
        warn.append(f"{n} characters — ideal is {li['ideal_min_chars']}-{li['ideal_max_chars']}.")
    elif n < li["ideal_min_chars"]:
        warn.append(f"{n} characters — short; ideal is {li['ideal_min_chars']}-{li['ideal_max_chars']}.")
    hook = text.strip().splitlines()[0]
    if len(hook) > li["hook_max_chars"]:
        warn.append(f"First line is {len(hook)} characters — keep the hook under {li['hook_max_chars']}.")
    for w in br["banned_words"]:
        if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low):
            block.append(f"Banned word: '{w}'.")
    tags = re.findall(r"#\w+", text)
    if len(tags) > br["max_hashtags"]:
        block.append(f"{len(tags)} hashtags — max {br['max_hashtags']}.")
    approved = {t.lower() for t in br["approved_hashtags"]}
    odd = [t for t in tags if t.lower() not in approved]
    if odd:
        warn.append(f"Hashtags not on the approved list: {', '.join(odd)}.")
    emojis = len(_EMOJI.findall(text))
    if emojis > br["max_emojis"]:
        warn.append(f"{emojis} emojis — max {br['max_emojis']}.")
    if text.count("!") > br["max_exclamations"]:
        warn.append(f"{text.count('!')} exclamation marks — max {br['max_exclamations']}.")
    if not any(c in low for c in br["cta_markers"]):
        warn.append("No clear call to action (e.g. 'Read the story', 'Join us', 'Tell us in the comments').")
    for name in br["unapproved_names"]:
        if name.lower() in low:
            block.append(f"'{name}' may not be named publicly (no permission / prospect / employee consent).")
    public = []
    for c in fixture("smb_case_studies")["case_studies"]:
        if c["public"]:
            words = c["customer"].lower().split()
            public.append(words[0] if len(words[0]) >= 8 else " ".join(words[:2]))
    if re.search(r"\d+(\.\d+)?\s?%|\b\d+(\.\d+)?x\b", low):
        if not any(p in low for p in public) and "customer-reported" not in low:
            block.append("Result claim without a named, approved customer story or 'customer-reported' label.")
    if "kitewing ai" in low:
        block.append("Use 'Kitewing Assist', never 'Kitewing AI'.")
    if "the bot" in low:
        warn.append("Avoid 'the bot' — say 'Kitewing Assist'.")
    if re.search(r"route optimi[sz]er", text) and "Route Optimizer" not in text:
        warn.append("Write 'Route Optimizer' with capitals.")
    if "fieldops" in low and "kitewing fieldops" not in low:
        warn.append("Use the full name 'Kitewing FieldOps' on first mention.")
    score = max(0, 100 - 20 * len(block) - 5 * len(warn))
    return ok(score=score, passed=not block and score >= 80, blocking=block, warnings=warn,
              stats={"chars": n, "hashtags": len(tags), "emojis": emojis}, channel=channel)


# --- Operations: planning -------------------------------------------------------------------------------------------


@hive_tool("smb")
def smb_estimate_tasks(tasks: list[dict], contingency_pct: float = 15.0) -> dict:
    """Estimate work-package durations with three-point (PERT) estimates from Kitewing's reference projects.

    Args:
        tasks: Work packages: {"id": "T1", "name": "Data migration from legacy system", "size": "S"|"M"|"L",
            "type": optional reference type (discovery, design, configuration, data_migration, integration,
            development, testing, uat, training, content, change_management, procurement, security_review,
            go_live, hypercare, marketing), "depends_on": ["..."], "owner": "..."}.
        contingency_pct: Schedule contingency to recommend (policy: 10 low, 15 default, 20 legacy/third party).

    Returns:
        Per task: matched reference type, optimistic/likely/pessimistic, expected and P80 working days, effort
        person-days, and calendar duration_days ready to pass straight to critical_path; plus totals.
    """
    ref = fixture("smb_projects")["estimation_reference"]
    wt = ref["work_types"]
    if not tasks:
        return err("tasks must not be empty")
    ids = [str(t.get("id", "")) for t in tasks]
    if len(set(ids)) != len(ids) or "" in ids:
        return err("every task needs a unique id")
    out, cp_tasks, effort = [], [], 0.0
    for t in tasks:
        missing = [d for d in t.get("depends_on") or [] if d not in ids]
        if missing:
            return err(f"task {t['id']} depends on unknown ids {missing}")
        typ = str(t.get("type", "")).lower().replace(" ", "_").replace("-", "_")
        matched = True
        if typ not in wt:
            text = (str(t.get("type", "")) + " " + str(t.get("name", ""))).lower()
            best = max(wt, key=lambda k: sum(kw in text for kw in wt[k]["keywords"]))
            matched = any(kw in text for kw in wt[best]["keywords"])
            typ = best if matched else "configuration"
        size = str(t.get("size", "M")).upper()[:1]
        size = size if size in ("S", "M", "L") else "M"
        o, m, p = wt[typ][size]
        exp = (o + 4 * m + p) / 6
        sd = (p - o) / 6
        p80 = exp + 0.84 * sd
        cal = math.ceil(exp * 7 / 5)
        pd = exp * wt[typ]["crew_fte"]
        effort += pd
        row = {"id": t["id"], "name": t.get("name", t["id"]), "type": typ, "size": size,
               "optimistic_wd": o, "likely_wd": m, "pessimistic_wd": p, "expected_wd": round(exp, 1),
               "p80_wd": round(p80, 1), "crew_fte": wt[typ]["crew_fte"], "effort_person_days": round(pd, 1),
               "duration_days": cal, "depends_on": list(t.get("depends_on") or []), "owner": t.get("owner", "")}
        if not matched:
            row["note"] = "no reference match — defaulted to configuration; refine the estimate"
        out.append(row)
        cp_tasks.append({k: row[k] for k in ("id", "name", "duration_days", "depends_on", "owner")})
    return ok(method=ref["method"], estimates=out, tasks_for_critical_path=cp_tasks,
              total_effort_person_days=round(effort, 1), recommended_contingency_pct=contingency_pct,
              contingency_policy=ref["contingency_policy"],
              note="duration_days are calendar days (working days x 7/5) — pass tasks_for_critical_path to critical_path.")


@hive_tool("smb")
def smb_team_capacity(team: str = "", skill: str = "", min_availability_pct: int = 0) -> dict:
    """List Kitewing people with role, team, skills, current allocations and availability for the next 8 weeks.

    Args:
        team: Optional team filter: Leadership, Sales, Customer Success, Marketing, Product & Engineering,
            People & Operations.
        skill: Optional skill keyword, e.g. 'data migration', 'training', 'payments'.
        min_availability_pct: Only people with at least this % availability.

    Returns:
        People (name, role, team, email, availability %, skills, allocations) sorted by availability — use it to
        assign owners and build RACI charts with real names.
    """
    rows = fixture("smb_projects")["team"]
    if team:
        rows = [r for r in rows if _norm(team) in _norm(r["team"])]
    if skill:
        rows = [r for r in rows if any(_norm(skill) in _norm(s) for s in r["skills"]) or _norm(skill) in _norm(r["role"])]
    rows = [r for r in rows if r["availability_pct"] >= min_availability_pct]
    return ok(people=sorted(rows, key=lambda r: -r["availability_pct"]), count=len(rows),
              note="Availability is for the next 8 weeks; new hires are partly allocated to onboarding.")


_PTYPE_WORDS = {
    "customer_implementation": ["implement", "rollout", "roll-out", "onboard", "migration", "go-live", "deploy for",
                                "customer"],
    "product_launch": ["launch", "feature", "portal", "product", "release", "beta", "app"],
    "internal_systems": ["erp", "crm", "internal", "system", "tool", "process", "office"],
    "compliance": ["soc", "audit", "compliance", "iso", "gdpr", "policy"],
    "marketing_campaign": ["campaign", "marketing", "event", "webinar", "brand", "summit"],
}


@hive_tool("smb")
def smb_risk_library(project_type: str, top_n: int = 6) -> dict:
    """Get typical risks for a project type from Kitewing's lessons learned, scored by exposure with mitigations.

    Args:
        project_type: customer_implementation, product_launch, internal_systems, compliance or marketing_campaign —
            or words describing the project (e.g. 'HVAC customer rollout with data migration').
        top_n: Number of risks to return (highest exposure first).

    Returns:
        Risks with likelihood (1-5), impact (1-5), exposure (L x I), rating (High >= 15, Medium >= 8, Low), mitigation
        and owner role, plus a count by rating.
    """
    lib = fixture("smb_projects")["risk_library"]
    key = project_type.strip().lower().replace(" ", "_")
    if key not in lib:
        low = project_type.lower()
        key = max(_PTYPE_WORDS, key=lambda k: sum(w in low for w in _PTYPE_WORDS[k]))
        if not any(w in low for w in _PTYPE_WORDS[key]):
            return err(f"unknown project type {project_type!r}", types=list(lib))
    risks = []
    for r in lib[key]:
        e = r["likelihood"] * r["impact"]
        risks.append({**r, "exposure": e, "rating": "High" if e >= 15 else "Medium" if e >= 8 else "Low"})
    risks.sort(key=lambda r: -r["exposure"])
    risks = risks[:max(1, top_n)]
    return ok(project_type=key, risks=risks,
              by_rating={k: sum(r["rating"] == k for r in risks) for k in ("High", "Medium", "Low")})


# --- Operations: status, retros, tasks ------------------------------------------------------------------------------


def _project(project: str) -> dict | None:
    return _pick(project, fixture("smb_projects")["projects"], ("id", "name", "customer"))


@hive_tool("smb")
def smb_project_status(project: str) -> dict:
    """Compute a project's weekly status from the task tracker: late work, blockers, earned value, forecast and RAG.

    Args:
        project: Project id or name, e.g. 'PRJ-107', 'Customer Portal 2.0', 'Greystone'.

    Returns:
        RAG status with reasons and last week's RAG, % complete, schedule and cost performance (SPI/CPI), budget
        burn, late tasks, blocked tasks, work due in the next 7 days, forecast finish vs target, milestones,
        stakeholders and the status-email distribution list.
    """
    prj = _project(project)
    if not prj:
        return err(f"no project matching {project!r}",
                   projects=[f"{p['id']} {p['name']}" for p in fixture("smb_projects")["projects"]])
    tasks = {t["id"]: t for t in prj["tasks"]}
    total_h = sum(t["hours"] for t in tasks.values())
    ev = pv = 0.0
    late, blocked, due_soon, behind = [], [], [], []
    forecast: dict[str, dt.date] = {}
    order, seen = [], set()

    def visit(k: str) -> None:
        if k in seen:
            return
        seen.add(k)
        for d in tasks[k]["depends_on"]:
            visit(d)
        order.append(k)

    for k in tasks:
        visit(k)
    for k in order:
        t = tasks[k]
        s, d = _date(t["start"]), _date(t["due"])
        dur = max(1, (d - s).days)
        ev += t["hours"] * t["pct"] / 100
        pv += t["hours"] * _clamp((TODAY - s).days / dur, 0, 1)
        dep_end = max((forecast[x] for x in t["depends_on"]), default=None)
        if t["status"] == "done":
            forecast[k] = d
            continue
        remaining = math.ceil((1 - t["pct"] / 100) * dur)
        if t["status"] == "blocked":
            blocked.append({"id": k, "name": t["name"], "owner": t["owner"], "due": t["due"], "blocker": t["blocker"]})
            remaining += 5
        if d < TODAY:
            late.append({"id": k, "name": t["name"], "owner": t["owner"], "due": t["due"],
                         "days_late": (TODAY - d).days, "pct": t["pct"], "status": t["status"],
                         "note": t["blocker"]})
        elif d <= TODAY + dt.timedelta(days=7):
            due_soon.append({"id": k, "name": t["name"], "owner": t["owner"], "due": t["due"], "pct": t["pct"]})
        expected_pct = 100 * _clamp((TODAY - s).days / dur, 0, 1)
        if t["status"] == "in_progress" and t["pct"] + 20 < expected_pct:
            behind.append({"id": k, "name": t["name"], "pct": t["pct"], "expected_pct": round(expected_pct)})
        if s <= TODAY or t["status"] != "not_started":
            end = max(d, TODAY + dt.timedelta(days=remaining))
        else:
            end = d
        if dep_end and dep_end + dt.timedelta(days=dur) > end:
            end = dep_end + dt.timedelta(days=dur)
        forecast[k] = end
    spi = round(ev / pv, 2) if pv else 1.0
    cpi = round(ev / prj["actual_hours"], 2) if prj["actual_hours"] else 1.0
    finish = max(forecast.values())
    target = _date(prj["target_end"])
    slip = (finish - target).days
    reasons = []
    if spi < 0.75 or cpi < 0.75 or slip > 5:
        rag = "Red"
    elif spi < 0.92 or cpi < 0.92 or late or blocked or slip > 0:
        rag = "Amber"
    else:
        rag = "Green"
    reasons.append(f"SPI {spi} (earned {round(ev)} of {round(pv)} planned hours to date)")
    reasons.append(f"CPI {cpi} ({prj['actual_hours']} actual hours for {round(ev)} earned)")
    if late:
        reasons.append(f"{len(late)} late task(s)")
    if blocked:
        reasons.append(f"{len(blocked)} blocked task(s)")
    reasons.append(f"forecast finish {finish.isoformat()} vs target {prj['target_end']} ({slip:+d} days)")
    return ok(project={k: prj[k] for k in ("id", "name", "type", "customer", "pm", "sponsor", "customer_sponsor",
                                           "start", "target_end")},
              as_of=TODAY.isoformat(), rag=rag, last_week_rag=prj["last_week_rag"], rag_reasons=reasons,
              pct_complete=round(100 * ev / total_h, 1), spi=spi, cpi=cpi,
              budget={"budget_hours": prj["budget_hours"], "actual_hours": prj["actual_hours"],
                      "burn_pct": round(100 * prj["actual_hours"] / prj["budget_hours"], 1)},
              late_tasks=late, blocked_tasks=blocked, due_next_7_days=due_soon, behind_pace=behind,
              forecast_finish=finish.isoformat(), slip_days=slip, milestones=prj["milestones"],
              distribution=prj["distribution"],
              tasks=[{**t, "forecast_end": forecast[t["id"]].isoformat()} for t in prj["tasks"]])


@hive_tool("smb")
def smb_retro_board(board: str) -> dict:
    """Load a retrospective board and cluster its cards into themes with votes, plus follow-through on past actions.

    Args:
        board: Board id or name: 'sprint-42' (Portal 2.0 squad) or 'prj-104-pilot' (Greystone Assist pilot).

    Returns:
        Cards grouped by theme (votes, went-well / to-improve / ideas counts), the top issues by votes, team health
        check scores (lowest first), sprint stats and the status of actions from previous retros.
    """
    data = fixture("smb_retro")
    boards = [{"id": k, **v} for k, v in data["boards"].items()]
    b = _pick(board, boards, ("id", "name", "project"))
    if not b:
        return err(f"no retro board matching {board!r}", boards=list(data["boards"]))
    themes: dict[str, dict] = {}
    for c in b["cards"]:
        text = " " + c["text"].lower() + " "
        best = max(data["themes"], key=lambda th: sum(k in text for k in data["themes"][th]))
        if not any(k in text for k in data["themes"][best]):
            best = "Other"
        th = themes.setdefault(best, {"theme": best, "votes": 0, "went_well": 0, "to_improve": 0, "ideas": 0,
                                      "cards": []})
        th["votes"] += c["votes"]
        th[c["column"]] += 1
        th["cards"].append(c)
    for th in themes.values():
        th["improve_votes"] = sum(x["votes"] for x in th["cards"] if x["column"] == "to_improve")
    ranked = sorted(themes.values(), key=lambda t: (-t["improve_votes"], -t["votes"]))
    prev = b["previous_actions"]
    done = sum(a["status"] == "done" for a in prev)
    return ok(board=b["id"], name=b["name"], project=b["project"], period=b["period"], facilitator=b["facilitator"],
              participants=b["participants"], stats=b["sprint_stats"], themes=ranked,
              top_issues=sorted([c for c in b["cards"] if c["column"] == "to_improve"], key=lambda c: -c["votes"])[:4],
              ideas=sorted([c for c in b["cards"] if c["column"] == "ideas"], key=lambda c: -c["votes"]),
              health_check=sorted(({"dimension": k, "score": v} for k, v in b["health_check"].items()),
                                  key=lambda x: x["score"]),
              previous_actions=prev,
              follow_through_pct=round(100 * done / len(prev)) if prev else None,
              carried_over=[a for a in prev if a["status"] != "done"])


@hive_tool("smb", kind="action")
def smb_create_tasks(project: str, tasks: list[dict]) -> dict:
    """Create tasks (e.g. retro actions or plan work packages) in Kitewing's task tracker (simulated).

    Args:
        project: Project id or name (e.g. 'PRJ-107'), or 'NEW: <name>' for a project not yet in the tracker.
        tasks: List of {"title": str, "owner": str, "due_date": "YYYY-MM-DD", "priority": "high"|"medium"|"low"}.

    Returns:
        Created task keys with owner and due date, plus warnings for unknown owners or past due dates.
    """
    if not tasks:
        return err("tasks must not be empty")
    if project.upper().startswith("NEW:"):
        pid, pname = "NEW", project[4:].strip()
    else:
        prj = _project(project)
        if not prj:
            return err(f"no project matching {project!r}; use 'NEW: <name>' to create one")
        pid, pname = prj["id"], prj["name"]
    people = {_norm(p["name"]): p["name"] for p in fixture("smb_projects")["team"]}
    created, warnings = [], []
    for i, t in enumerate(tasks):
        title = str(t.get("title", "")).strip()
        if not title:
            warnings.append(f"task {i + 1} has no title — skipped")
            continue
        owner = str(t.get("owner", "")).strip()
        if owner and _norm(owner) not in people and not any(_norm(owner) in k for k in people):
            warnings.append(f"owner {owner!r} is not a Kitewing team member — check (external owners are allowed)")
        due = _date(t.get("due_date"))
        if not due:
            warnings.append(f"{title!r}: missing/invalid due_date")
        elif due < TODAY:
            warnings.append(f"{title!r}: due date {due} is in the past")
        created.append({"key": _sid("KW", pid, title, lo=1200, span=800), "title": title, "owner": owner or "unassigned",
                        "due_date": due.isoformat() if due else None, "priority": t.get("priority", "medium")})
    return ok(project=pid, project_name=pname, created=created, warnings=warnings, simulated=True)


# --- Operations: AI adoption ----------------------------------------------------------------------------------------


@hive_tool("smb")
def smb_score_ai_readiness(answers: list[dict] | None = None, organisation: str = "Kitewing Software") -> dict:
    """Score an AI-readiness questionnaire (6 dimensions, 12 questions) into a maturity level with gaps and actions.

    Args:
        answers: List of {"question_id": "S1", "score": 1-5} (ids S1-S2, D1-D2, T1-T2, K1-K2, G1-G2, C1-C2) or
            {"dimension": "data", "score": 1-5}. Call with no answers to get the questionnaire.
        organisation: Name of the organisation assessed (for the report).

    Returns:
        With answers: per-dimension scores, weighted overall score, maturity level (1 Exploring - 5 Transforming),
        the weakest dimensions with recommended actions, and unanswered questions. Without answers: the questions.
    """
    ar = fixture("smb_ai_readiness")
    qs = {q["id"]: q for q in ar["questions"]}
    if not answers:
        return ok(mode="questionnaire", scale=ar["scale"], questions=ar["questions"],
                  dimensions={k: v["name"] for k, v in ar["dimensions"].items()})
    per: dict[str, list[float]] = {k: [] for k in ar["dimensions"]}
    answered, bad = set(), []
    for a in answers:
        try:
            sc = float(a.get("score"))
        except (TypeError, ValueError):
            bad.append(a)
            continue
        if not 1 <= sc <= 5:
            bad.append(a)
            continue
        qid = str(a.get("question_id", a.get("id", ""))).upper().strip()
        dim = qs[qid]["dimension"] if qid in qs else _norm(a.get("dimension", "")).split(" ")[0]
        dim = dim if dim in per else next((k for k, v in ar["dimensions"].items()
                                           if dim and dim in _norm(v["name"])), None)
        if not dim:
            bad.append(a)
            continue
        per[dim].append(sc)
        if qid in qs:
            answered.add(qid)
    dims = []
    for k, v in ar["dimensions"].items():
        vals = per[k]
        dims.append({"dimension": k, "name": v["name"], "weight": v["weight"],
                     "score": round(sum(vals) / len(vals), 2) if vals else None})
    scored = [d for d in dims if d["score"] is not None]
    if not scored:
        return err("no valid answers (scores must be 1-5)", invalid=bad)
    overall = round(sum(d["score"] * d["weight"] for d in scored) / sum(d["weight"] for d in scored), 2)
    level = [lv for lv in ar["levels"] if overall >= lv["min"]][-1]
    weakest = sorted(scored, key=lambda d: d["score"])[:3]
    return ok(organisation=organisation, overall_score=overall, maturity_level=level["level"],
              maturity_name=level["name"], level_description=level["description"], dimensions=dims,
              weakest=[{**w, "actions": ar["recommendations"][w["dimension"]]} for w in weakest if w["score"] < 3.5],
              unanswered=[q for q in qs if q not in answered] if answered else None, invalid_answers=bad or None,
              levels=ar["levels"])


@hive_tool("smb")
def smb_prioritise_use_cases(use_cases: list[dict] | None = None, department: str = "",
                             readiness_level: int = 0) -> dict:
    """Prioritise AI use cases on value vs effort and data readiness into quadrants and 90-day waves.

    Args:
        use_cases: Optional list of {"name": str, "value": 1-5, "effort": 1-5, "data_readiness": 1-5,
            "department": str}. Leave empty to score Kitewing's SMB use-case library.
        department: Optional department filter for the library (Sales, Customer Success, Finance, Marketing,
            Product & Engineering, People, Operations).
        readiness_level: Optional maturity level 1-5 from smb_score_ai_readiness (levels 1-2 push big bets out).

    Returns:
        Scored use cases (priority score, quadrant: Quick win / Strategic bet / Fill-in / Deprioritise, wave:
        Days 0-30 / 31-60 / 61-90 / Backlog), a Mermaid quadrant chart and the wave plan.
    """
    lib = fixture("smb_ai_readiness")["use_case_library"]
    wanted = [_norm(d) for d in re.split(r",|/|&| and ", department.lower()) if _norm(d)] if department else []
    src = use_cases or [u for u in lib if not wanted or u["department"] == "All"
                        or any(w in _norm(u["department"]) or _norm(u["department"]) in w for w in wanted)]
    if not src:
        return err(f"no use cases for department {department!r}")
    rows = []
    for i, u in enumerate(src, start=1):
        try:
            v, e, dr = (max(1, min(5, int(u.get(k, 3)))) for k in ("value", "effort", "data_readiness"))
        except (TypeError, ValueError):
            return err(f"use case {i}: value/effort/data_readiness must be integers 1-5")
        quad = ("Quick win" if e <= 2 else "Strategic bet") if v >= 4 else ("Fill-in" if e <= 2 else "Deprioritise")
        if quad == "Quick win":
            wave = "Days 0-30" if dr >= 3 else "Days 31-60 (fix data first)"
        elif quad == "Fill-in":
            wave = "Days 31-60" if dr >= 3 else "Backlog"
        elif quad == "Strategic bet":
            wave = "Days 61-90 (discovery + pilot)" if dr >= 3 and readiness_level != 1 else "Backlog (data/readiness first)"
        else:
            wave = "Backlog"
        rows.append({"id": u.get("id", f"U{i}"), "name": u.get("name", f"Use case {i}"),
                     "department": u.get("department", department or ""), "value": v, "effort": e,
                     "data_readiness": dr, "priority_score": round(v * 2 + dr - e * 1.5, 1), "quadrant": quad,
                     "wave": wave, "kpi": u.get("kpi", ""), "time_to_value_weeks": u.get("time_to_value_weeks")})
    rows.sort(key=lambda r: -r["priority_score"])
    first = [r for r in rows if r["wave"] == "Days 0-30"]
    for r in first[3:]:
        r["wave"] = "Days 31-60"
        r["note"] = "moved: at most 3 launches in the first 30 days"
    chart = ["quadrantChart", "  title AI use cases - value vs effort", "  x-axis Low effort --> High effort",
             "  y-axis Low value --> High value", "  quadrant-1 Strategic bets", "  quadrant-2 Quick wins",
             "  quadrant-3 Fill-ins", "  quadrant-4 Deprioritise"]
    for r in rows:
        x = round(0.05 + 0.9 * (r["effort"] - 1) / 4, 2)
        y = round(0.05 + 0.9 * (r["value"] - 1) / 4, 2)
        chart.append(f"  {re.sub(r'[^A-Za-z0-9]', '', str(r['id']))}: [{x}, {y}]")
    waves: dict[str, list[str]] = {}
    for r in rows:
        waves.setdefault(r["wave"], []).append(f"{r['id']} {r['name']}")
    return ok(use_cases=rows, waves=waves, mermaid_quadrant="\n".join(chart),
              scoring="priority = 2 x value + data readiness - 1.5 x effort; Quick win = value >= 4 and effort <= 2")


# --- People: onboarding ---------------------------------------------------------------------------------------------


_ROLE_WORDS = {"account_executive": ["account executive", "ae", "sales", "seller"],
               "backend_engineer": ["backend", "engineer", "developer", "software"],
               "implementation_consultant": ["implementation", "consultant", "onboarding specialist", "professional services"]}


def _hire(name: str) -> dict | None:
    return _pick(name, fixture("smb_people")["new_hires"], ("name", "title"))


def _role_key(role: str) -> str | None:
    low = f" {role.lower()} "
    for k, words in _ROLE_WORDS.items():
        if k == role or any(f" {w} " in low or (len(w) > 3 and w in low) for w in words):
            return k
    return None


@hive_tool("smb")
def smb_onboarding_pack(new_hire: str = "", role: str = "") -> dict:
    """Get a new hire's onboarding pack: profile, 30/60/90 plan, trainings with due dates, equipment, accounts, contacts.

    Args:
        new_hire: Name of an upcoming hire (e.g. 'Mateo Fernández', 'Samir Haddad', 'Grace Obi').
        role: Alternatively a role ('Account Executive', 'Backend Engineer', 'Implementation Consultant') for the
            generic template when the person is not in the HR system yet.

    Returns:
        Hire profile (manager, buddy, start date, work mode, first assignment), the role's 30/60/90 goals with
        measures, required trainings with calendar due dates, equipment and account lists with provisioning queues,
        and key contacts.
    """
    pp = fixture("smb_people")
    h = _hire(new_hire) if new_hire else None
    if new_hire and not h:
        return err(f"no upcoming hire named {new_hire!r}", new_hires=[x["name"] for x in pp["new_hires"]])
    key = h["role_key"] if h else _role_key(role or "")
    if not key:
        return err("give a new hire name or a role", roles=list(pp["role_templates"]))
    tpl = pp["role_templates"][key]
    start = _date(h["start_date"]) if h else None
    trainings = []
    for t in [*pp["common_trainings"], *tpl["trainings"]]:
        trainings.append({**t, "due_date": (start + dt.timedelta(days=t["due_day"])).isoformat() if start else None})
    cat = pp["provisioning_catalog"]

    def items(names: list[str]) -> list[dict]:
        return [{"item": n, "label": cat[n]["label"], "queue": cat[n]["queue"], "approval": cat[n]["approval"] or None}
                for n in names if n in cat]

    return ok(new_hire=h, role_key=key,
              days_until_start=(start - TODAY).days if start else None,
              plan_30=tpl["plan_30"], plan_60=tpl["plan_60"], plan_90=tpl["plan_90"],
              milestone_dates={"day_30": (start + dt.timedelta(days=30)).isoformat(),
                               "day_60": (start + dt.timedelta(days=60)).isoformat(),
                               "day_90": (start + dt.timedelta(days=90)).isoformat()} if start else None,
              trainings=sorted(trainings, key=lambda t: t["due_day"]), equipment=items(tpl["equipment"]),
              accounts=items(tpl["accounts"]), key_contacts=tpl["key_contacts"])


@hive_tool("smb")
def smb_day_one_schedule(new_hire: str) -> dict:
    """Build a new hire's personalised day-one schedule (office, remote or hybrid) with names, times and prep checklist.

    Args:
        new_hire: Name of an upcoming hire (e.g. 'Mateo Fernández').

    Returns:
        Date, location, the timed agenda with who they meet, remote adjustments, and a 'before day one' checklist
        for the manager, buddy, IT and People team.
    """
    pp = fixture("smb_people")
    h = _hire(new_hire)
    if not h:
        return err(f"no upcoming hire named {new_hire!r}", new_hires=[x["name"] for x in pp["new_hires"]])
    tpl = pp["role_templates"][h["role_key"]]
    d1 = pp["day_one"]
    start = _date(h["start_date"])
    remote = h["work_mode"] == "remote" or (h["work_mode"] == "hybrid" and start.weekday() in (0, 4))
    guide = d1["product_guides"].get(h["team"], "Sofia Petrov")
    subst = {"MANAGER": h["manager"], "BUDDY": h["buddy"], "PRODUCT_GUIDE": guide,
             "ROLE_SESSION": tpl["role_session"]["title"], "ROLE_SESSION_WITH": tpl["role_session"]["with"]}
    agenda = []
    for slot in d1["office"]:
        title = subst.get(slot["title"], slot["title"])
        if remote and slot["time"] in d1["remote_changes"]:
            title = d1["remote_changes"][slot["time"]]
        agenda.append({"start": f"{start.isoformat()}T{slot['time']}", "end": f"{start.isoformat()}T{slot['end']}",
                       "title": title, "with": subst.get(slot["with"], slot["with"]) or "self-paced",
                       "where": "Google Meet (link in invite)" if remote else h["location"]})
    notes = []
    if h["work_mode"] == "hybrid" and remote:
        nxt = start + dt.timedelta(days=1)
        notes.append(f"Day one is a remote day; first office day is {nxt.isoformat()} ({nxt.strftime('%A')}) — badge "
                     "and desk set-up with Erin Walsh at 09:00.")
    if remote:
        notes.append("Laptop and security keys must arrive at home by the Friday before; IT setup runs over video.")
    before = [
        {"owner": h["manager"], "task": "Send a welcome email with the day-one agenda and first-week goals",
         "due": _add_bdays(start, -3).isoformat()},
        {"owner": h["buddy"], "task": "Book the lunch and a 15-minute daily check-in for week one",
         "due": _add_bdays(start, -2).isoformat()},
        {"owner": "Noah Kim", "task": "Laptop, security keys and accounts ready (see provisioning tickets)",
         "due": _add_bdays(start, -1).isoformat()},
        {"owner": "Erin Walsh", "task": "HR portal invite, benefits pack and handbook link sent",
         "due": _add_bdays(start, -5).isoformat()},
    ]
    return ok(new_hire=h["name"], title=h["title"], date=start.isoformat(), weekday=start.strftime("%A"),
              mode="remote" if remote else h["work_mode"], location=h["location"], agenda=agenda, notes=notes,
              before_day_one=before, calendar_invites="Created as drafts only — confirm before sending (simulated).")


@hive_tool("smb", kind="action")
def smb_provision_request(new_hire: str, items: list[str] | None = None) -> dict:
    """Open provisioning tickets for a new hire's equipment and accounts with SLA and readiness check (simulated).

    Args:
        new_hire: Name of an upcoming hire (e.g. 'Samir Haddad').
        items: Items from the provisioning catalog (e.g. 'laptop', 'crm', 'cloud console dev'); empty = everything
            the hire's role template lists.

    Returns:
        One ticket per item with queue, SLA, required approval, the ready-by date and whether it will be ready
        before day one (on time / tight / at risk — expedite), plus items deferred until after day 30.
    """
    pp = fixture("smb_people")
    h = _hire(new_hire)
    if not h:
        return err(f"no upcoming hire named {new_hire!r}", new_hires=[x["name"] for x in pp["new_hires"]])
    tpl = pp["role_templates"][h["role_key"]]
    cat = pp["provisioning_catalog"]
    wanted = items or [*tpl["equipment"], *tpl["accounts"]]
    start = _date(h["start_date"])
    need_by = _add_bdays(start, -1)
    tickets, unknown = [], []
    for raw in wanted:
        k = raw.strip().lower()
        if k not in cat:
            k = next((c for c in cat if _norm(raw) in _norm(c + " " + cat[c]["label"])), None)
        if not k:
            unknown.append(raw)
            continue
        c = cat[k]
        prefix = {"IT": "IT", "Security": "SEC", "People": "PPL", "Finance": "FIN", "Sales Ops": "SOPS",
                  "Engineering": "ENG", "Product": "PRD", "Professional Services": "PS", "Support": "SUP"}[c["queue"]]
        ready = _add_bdays(TODAY, c["sla_business_days"] + (1 if c["approval"] else 0))
        due = need_by
        if c.get("not_before_day"):
            due = start + dt.timedelta(days=c["not_before_day"])
            ready = max(ready, due)
        slack = (due - ready).days
        status = "scheduled after day 30" if c.get("not_before_day") else \
            "on time" if slack >= 2 else "tight" if slack >= 0 else "at risk — expedite"
        approver = None
        if c["approval"]:
            approver = h["manager"] if c["approval"] == "manager" else c["approval"]
        tickets.append({"ticket": _sid(prefix, h["name"], k), "item": c["label"], "queue": c["queue"],
                        "sla_business_days": c["sla_business_days"], "approval": approver,
                        "ready_by": ready.isoformat(), "needed_by": due.isoformat(), "status": status})
    if not tickets:
        return err("no valid items", unknown=unknown, catalog=list(cat))
    return ok(new_hire=h["name"], start_date=h["start_date"], tickets=tickets,
              at_risk=[t for t in tickets if t["status"].startswith("at risk")],
              pending_approvals=[t for t in tickets if t["approval"]], unknown_items=unknown or None, simulated=True)


# --- People: skills -------------------------------------------------------------------------------------------------


def _skill_name(name: str, vocab: list[str]) -> str | None:
    n = _norm(name)
    for v in vocab:
        if n == _norm(v):
            return v
    for v in vocab:
        nv = _norm(v)
        if n and (n in nv or nv in n):
            return v
    return None


@hive_tool("smb")
def smb_skill_gap(target_role: str, employee: str = "", skills: list[dict] | None = None) -> dict:
    """Compare an employee's (or candidate's) skills with a target role in Kitewing's role matrix.

    Args:
        target_role: Role from the matrix, e.g. 'Solutions Architect', 'Senior Software Engineer',
            'Senior Data Engineer', 'Senior Customer Success Manager', 'Implementation Consultant',
            'Senior Implementation Consultant', 'Account Executive'.
        employee: Employee name in the HR system (e.g. 'Ines Duarte'); leave empty for an external candidate.
        skills: For candidates or overrides: [{"skill": "Data migration", "level": 1-4}] (1 Aware, 2 Working,
            3 Practitioner, 4 Expert), e.g. extracted from a CV.

    Returns:
        Readiness % for the role, strengths, gaps (required vs current level) ordered by size, project evidence per
        skill, and transferable skills outside the role profile.
    """
    pp = fixture("smb_people")
    matrix = pp["role_matrix"]
    role = next((r for r in matrix if _norm(r) == _norm(target_role)), None) or \
        next((r for r in matrix if _norm(target_role) in _norm(r)), None)
    if not role:
        return err(f"unknown role {target_role!r}", roles=list(matrix))
    vocab = sorted({s for r in matrix.values() for s in r} | {s for e in pp["employees"] for s in e["skills"]})
    emp = _pick(employee, pp["employees"], ("name",)) if employee else None
    if employee and not emp:
        return err(f"no employee named {employee!r}", employees=[e["name"] for e in pp["employees"]])
    current: dict[str, int] = dict(emp["skills"]) if emp else {}
    unmatched = []
    for s in skills or []:
        nm = _skill_name(str(s.get("skill", "")), vocab)
        try:
            lvl = max(0, min(4, int(s.get("level", 0))))
        except (TypeError, ValueError):
            lvl = 0
        if nm:
            current[nm] = lvl
        else:
            unmatched.append(s.get("skill"))
    if not current:
        return err("no skills: give an employee name or a skills list")
    req = matrix[role]
    names = pp["level_names"]
    gaps, strengths = [], []
    for sk, lvl in req.items():
        cur = current.get(sk, 0)
        evidence = [f"{p['project']} ({p['year']})" for p in (emp or {}).get("projects", []) if sk in p["skills"]]
        row = {"skill": sk, "required": lvl, "required_name": names[str(lvl)], "current": cur,
               "current_name": names.get(str(cur), "None"), "gap": max(0, lvl - cur), "evidence": evidence}
        (gaps if cur < lvl else strengths).append(row)
    gaps.sort(key=lambda r: -r["gap"])
    readiness = round(100 * sum(min(current.get(s, 0), lv) for s, lv in req.items()) / sum(req.values()), 1)
    return ok(person=(emp or {}).get("name", "External candidate"), current_title=(emp or {}).get("title"),
              aspiration=(emp or {}).get("aspiration"), certifications=(emp or {}).get("certifications", []),
              target_role=role, readiness_pct=readiness, strengths=strengths, gaps=gaps,
              transferable=[{"skill": s, "level": v} for s, v in current.items() if s not in req],
              unmatched_skills=unmatched or None, level_scale=names)


@hive_tool("smb")
def smb_learning_path(skills: list[str], weekly_hours: int = 4, budget_usd: float = 1500.0) -> dict:
    """Turn skill gaps into a sequenced learning path (courses, on-the-job work, Google Cloud certifications).

    Args:
        skills: Skills to develop, e.g. ['Google Cloud fundamentals', 'Solution design', 'Data governance'].
        weekly_hours: Learning hours per week (company policy: 4, 'focus Fridays').
        budget_usd: Learning budget available (policy: $1,500 per employee per year; certification exam fees are
            reimbursed on pass and do not count).

    Returns:
        Ordered steps with week ranges, hours and cost, total weeks, budget used vs available, certifications with
        exam fees, and skills with no catalog entry.
    """
    pp = fixture("smb_people")
    cat = pp["learning_catalog"]
    if not skills:
        return err("skills must not be empty")
    if weekly_hours < 1:
        return err("weekly_hours must be >= 1")
    steps, missing = [], []
    for i, s in enumerate(skills):
        nm = _skill_name(s, list(cat))
        if not nm:
            missing.append(s)
            continue
        for it in cat[nm]:
            steps.append({"skill": nm, **it, "_i": i})
    # courses first, then on-the-job practice, then certifications (Associate/foundational before Professional)
    rank = {"course": 0, "on-the-job": 1, "certification": 2}
    steps.sort(key=lambda x: (rank.get(x["type"], 1), "Professional" in x["title"], x["_i"]))
    for st in steps:
        st.pop("_i")
    week, total_h, budget_cost, exam_fees = 1, 0, 0.0, 0.0
    for st in steps:
        w = max(1, math.ceil(st["hours"] / weekly_hours))
        st["weeks"] = f"{week}-{week + w - 1}" if w > 1 else str(week)
        week += w
        total_h += st["hours"]
        if st["type"] == "certification" and st["provider"] == "Google Cloud":
            exam_fees += st["cost_usd"]
            st["funding"] = "exam fee reimbursed on pass"
        else:
            budget_cost += st["cost_usd"]
            st["funding"] = "learning budget" if st["cost_usd"] else "free (company subscription / internal)"
    return ok(steps=steps, total_hours=total_h, total_weeks=week - 1, weekly_hours=weekly_hours,
              budget={"available_usd": budget_usd, "used_usd": budget_cost, "remaining_usd": budget_usd - budget_cost,
                      "within_budget": budget_cost <= budget_usd},
              certification_exam_fees_usd=exam_fees, policy=pp["learning_policy"], skills_not_in_catalog=missing or None)

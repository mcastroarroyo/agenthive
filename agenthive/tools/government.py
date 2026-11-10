"""Government realm tools: City of Port Alder services (311, benefits, grants, licensing, permits, public records,
legal, procurement) and Republic of Valdoria national programmes (producer registry, business registry, housing
credit). All data is synthetic (fixtures/gov_*.json); actions are simulated; dates are evaluated "as of" the demo
clock in gov_city.json so every demo is reproducible.
"""
from __future__ import annotations

import calendar
import datetime as dt
import difflib
import hashlib
import math
import re
import unicodedata
from typing import Any

from ._base import doc_text, err, fixture, hive_tool, ok

try:  # ADK injects the context; the web image builds the catalog without ADK installed
    from google.adk.tools import ToolContext
except ImportError:  # pragma: no cover
    ToolContext = Any  # type: ignore[misc,assignment]

# --- shared helpers ----------------------------------------------------------------------------------------------


def _as_of() -> dt.datetime:
    return dt.datetime.fromisoformat(fixture("gov_city")["as_of"])


def _today() -> dt.date:
    return _as_of().date()


def _holidays() -> dict[str, str]:
    return {h["date"]: h["name"] for h in fixture("gov_city")["holidays"]}


def _is_business_day(d: dt.date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in _holidays()


def _add_business_days(d: dt.date, n: int) -> dt.date:
    while n > 0:
        d += dt.timedelta(days=1)
        if _is_business_day(d):
            n -= 1
    return d


def _business_days_between(a: dt.date, b: dt.date) -> int:
    """Business days after a up to and including b (negative when b < a)."""
    if b == a:
        return 0
    sign, lo, hi = (1, a, b) if b > a else (-1, b, a)
    n, d = 0, lo
    while d < hi:
        d += dt.timedelta(days=1)
        if _is_business_day(d):
            n += 1
    return sign * n


def _next_business_day(d: dt.date) -> dt.date:
    while not _is_business_day(d):
        d += dt.timedelta(days=1)
    return d


def _date(s: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(s.strip()[:10])
    except (ValueError, AttributeError):
        return None


_WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
             "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2, "jueves": 3, "viernes": 4, "sabado": 5,
             "sábado": 5, "domingo": 6}


def _weekday_date(s: str) -> dt.date | None:
    """'next Tuesday', 'Tuesday', 'el martes' -> the first such day after the demo clock's today."""
    t = (s or "").lower()
    for name, wd in _WEEKDAYS.items():
        if re.search(rf"\b{name}\b", t):
            return _today() + dt.timedelta(days=(wd - _today().weekday() - 1) % 7 + 1)
    if "tomorrow" in t or re.match(r"\s*(pasado\s+)?mañana\b", t):
        return _today() + dt.timedelta(days=2 if "pasado" in t else 1)
    return None


def _add_months(d: dt.date, months: int) -> dt.date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return dt.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9& ]", " ", s.lower())).strip()


def _sid(prefix: str, *parts: object) -> str:
    return prefix + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:6].upper()


def _money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


_STREET_ABBR = {"st": "Street", "ave": "Avenue", "av": "Avenue", "blvd": "Boulevard", "rd": "Road", "dr": "Drive",
                "ln": "Lane", "ter": "Terrace", "terr": "Terrace", "way": "Way", "pl": "Place"}


def _parse_address(address: str) -> tuple[int, str]:
    """Return (house number or 0, normalised street name) from '1427 Harbor St' or 'Quarry Rd at Mill St'."""
    a = re.split(r"\s+(?:at|and|&|/)\s+|,|\(", address.strip(), maxsplit=1, flags=re.I)[0].strip()
    m = re.match(r"^(\d{1,5})\s+(.+)$", a)
    num, street = (int(m.group(1)), m.group(2)) if m else (0, a)
    words = [w.strip(".") for w in street.split()]
    words = [_STREET_ABBR.get(w.lower(), w.capitalize() if w.islower() else w) for w in words]
    return num, " ".join(words)


# =================================================================================================================
# Citizen 311
# =================================================================================================================


def _sla_status(req: dict, cats: dict) -> dict:
    created = dt.datetime.fromisoformat(req["created"])
    hours = cats[req["category"]]["sla_hours"][req["priority"]]
    due = created + dt.timedelta(hours=hours)
    if req.get("closed"):
        closed = dt.datetime.fromisoformat(req["closed"])
        took = (closed - created).total_seconds() / 3600
        return {"sla_hours": hours, "due": due.isoformat(timespec="minutes"), "met": closed <= due,
                "hours_to_close": round(took, 1), "state": "closed within SLA" if closed <= due else "closed late"}
    left = (due - _as_of()).total_seconds() / 3600
    state = "breached" if left < 0 else "at risk" if left < hours * 0.25 else "on track"
    return {"sla_hours": hours, "due": due.isoformat(timespec="minutes"), "hours_remaining": round(left, 1), "state": state}


@hive_tool("government")
def gov_311_triage(description: str, address: str = "", category: str = "") -> dict:
    """Classify a resident's 311 report, set priority and SLA, route it to a department and find duplicate requests.

    Call this BEFORE creating any request. It applies the Port Alder 311 Service Standards (category keywords,
    P1 triggers such as arterial streets or hazards) and searches open requests on the same block.

    Args:
        description: The resident's words, e.g. 'Deep pothole outside my house, my tyre almost burst'.
        address: Street address or intersection, e.g. '1427 Harbor Street' or 'Quarry Road at Mill Street'.
        category: Optional category code if already known (POTHOLE, STREETLIGHT_OUT, MISSED_COLLECTION, BULKY_ITEM,
            ILLEGAL_DUMPING, GRAFFITI, TRAFFIC_SIGNAL, SIGN_DAMAGE, WATER_LEAK, TREE_DOWN, ABANDONED_VEHICLE,
            SIDEWALK_DAMAGE, DEAD_ANIMAL).

    Returns:
        Category, department, priority and SLA due time, duplicates (add the resident as a follower instead of
        creating a new request), recently resolved requests nearby, referrals for non-311 issues, and the questions
        still needed before a request can be filed.
    """
    data = fixture("gov_311")
    text = description.lower()
    referral = ""
    for i, rule in enumerate(data["not_311"]):
        if any(re.search(rf"\b{re.escape(k)}\b", text) for k in rule["keywords"]):
            known = any(k in text for c in data["categories"] for k in c["keywords"])
            if i == 0 or not known:   # rule 0 = emergencies: always refer first
                note = "If there is also a 311 issue, file it after the emergency is handled." if i == 0 else ""
                return ok(is_311=False, emergency=i == 0, referral=rule["referral"], also_file_311=known, note=note)
            referral = rule["referral"]
    cats = {c["code"]: c for c in data["categories"]}
    cat = cats.get(category.strip().upper()) if category else None
    if cat is None:
        scored = sorted(((sum(1 for k in c["keywords"] if k in text), c["code"]) for c in data["categories"]), reverse=True)
        if not scored or scored[0][0] == 0:
            return ok(is_311=True, category=None, message="Could not classify - ask what the problem is.",
                      categories=[{"code": c["code"], "name": c["name"]} for c in data["categories"]])
        cat = cats[scored[0][1]]
    num, street = _parse_address(address) if address else (0, "")
    triggers = [t for t in cat.get("p1_triggers", []) if t in text]
    on_arterial = street in data["arterial_streets"]
    priority = cat["default_priority"]
    reasons = []
    if triggers:
        priority, reasons = "P1", [f"hazard keywords: {', '.join(triggers)}"]
    if cat.get("p1_on_arterial") and on_arterial:
        priority = "P1"
        reasons.append(f"{street} is a designated arterial street")
    hours = cat["sla_hours"][priority]
    dupes, recent = [], []
    for r in data["requests"]:
        if r["category"] != cat["code"] or not street or r["street"].lower() != street.lower():
            continue
        near = (num and r["number"] and abs(r["number"] - num) <= 50) or (not num or not r["number"])
        if not near:
            continue
        row = {"id": r["id"], "address": r["address"], "status": r["status"], "created": r["created"],
               "priority": r["priority"], "followers": r.get("followers", 0)}
        if r["status"] != "closed":
            dupes.append(row)
        elif (_as_of() - dt.datetime.fromisoformat(r["closed"])).total_seconds() <= 72 * 3600:
            recent.append({**row, "closed": r["closed"], "resolution": r.get("resolution", "")})
    ask = []
    if not num and not re.search(r"\bat\b|&", address or "", re.I):
        ask.append("Exact house number or nearest cross street")
    ask += [q for q in cat.get("ask", []) if not (num and re.search(r"house number|cross street", q, re.I))]
    dept = data["departments"][cat["department"]]
    return ok(is_311=True, category=cat["code"], category_name=cat["name"], department=cat["department"],
              department_name=dept["name"], department_hours=dept["hours"], priority=priority,
              priority_reasons=reasons or ["default priority for this category"], sla_hours=hours,
              sla_due_if_filed_now=(_as_of() + dt.timedelta(hours=hours)).isoformat(timespec="minutes"),
              normalised_address=f"{num} {street}".strip() if street else "", on_arterial=on_arterial,
              duplicates=dupes, recently_resolved=recent,
              recommendation=("add_as_follower" if dupes else "reopen_or_new" if recent else "create_new"),
              follow_request_id=dupes[0]["id"] if dupes else "", questions_to_ask=ask[:3],
              other_referral=referral or None)


@hive_tool("government", kind="action")
def gov_311_create_request(category: str, address: str, description: str, priority: str = "",
                           follow_request_id: str = "", contact_name: str = "", channel: str = "messaging") -> dict:
    """File a 311 service request, or add the resident as a follower of an existing duplicate (simulated).

    Args:
        category: Category code from gov_311_triage (e.g. 'POTHOLE').
        address: Normalised address from gov_311_triage.
        description: Short description in the resident's words.
        priority: P1, P2 or P3 from gov_311_triage (default: the category's default priority).
        follow_request_id: When triage found a duplicate, its request id - the resident is added as a follower and
            no new request is created.
        contact_name: Optional resident name for status notifications.
        channel: Intake channel: messaging, app, web, phone or walk-in.

    Returns:
        The tracking number, department, SLA due time and what the resident should expect next.
    """
    data = fixture("gov_311")
    cats = {c["code"]: c for c in data["categories"]}
    if follow_request_id:
        req = next((r for r in data["requests"] if r["id"] == follow_request_id.strip().upper()), None)
        if not req:
            return err(f"unknown request {follow_request_id!r}")
        if req["status"] == "closed":
            return err(f"{req['id']} is closed - create a new request instead", closed=req.get("closed"))
        sla = _sla_status(req, cats)
        return ok(action="follower_added", request_id=req["id"], followers=req.get("followers", 0) + 1,
                  request_status=req["status"], sla_due=sla["due"], sla_state=sla["state"],
                  message=f"Added to {req['id']}; the resident will be notified when the status changes.",
                  simulated=True)
    cat = cats.get(category.strip().upper())
    if not cat:
        return err(f"unknown category {category!r}", categories=sorted(cats))
    if not address.strip() or len(description.strip()) < 5:
        return err("address and description are required")
    prio = priority.strip().upper() or cat["default_priority"]
    if prio not in cat["sla_hours"]:
        return err("priority must be P1, P2 or P3")
    rid = "SR-2026-1183" + str(int(hashlib.sha1(f"{category}{address}{description}".encode()).hexdigest(), 16) % 90 + 10)
    due = _as_of() + dt.timedelta(hours=cat["sla_hours"][prio])
    dept = data["departments"][cat["department"]]
    return ok(action="request_created", request_id=rid, category=cat["code"], priority=prio, department=dept["name"],
              queue=dept["queue"], sla_due=due.isoformat(timespec="minutes"), channel=channel,
              contact=contact_name or "anonymous", request_status="new",
              message=f"Request {rid} filed with {dept['name']}; target resolution by {due:%a %d %b %H:%M}.",
              simulated=True)


@hive_tool("government")
def gov_311_lookup_request(request_id: str) -> dict:
    """Look up a 311 service request: status, department, crew, history and SLA status as of now.

    Args:
        request_id: Tracking number, e.g. 'SR-2026-117952'.

    Returns:
        Request details, timeline, SLA due time and state (on track / at risk / breached / closed within SLA /
        closed late), hold reason if any, and number of followers.
    """
    data = fixture("gov_311")
    rid = request_id.strip().upper()
    req = next((r for r in data["requests"] if r["id"] == rid), None)
    if not req:
        return err(f"no request {rid!r}", hint="check the number - format SR-YYYY-NNNNNN")
    cats = {c["code"]: c for c in data["categories"]}
    dept = data["departments"][cats[req["category"]]["department"]]
    return ok(request=req, category_name=cats[req["category"]]["name"], department=dept["name"],
              sla=_sla_status(req, cats), as_of=_as_of().isoformat(timespec="minutes"))


# =================================================================================================================
# Benefits
# =================================================================================================================


def _income_limit(b: dict, pct: int, hh: int) -> int:
    table = b["monthly_income_limits"][str(pct)]
    if hh <= 8:
        return table[max(hh, 1) - 1]
    return round(table[7] + 0.08 * table[3] * (hh - 8))


@hive_tool("government")
def gov_benefits_screen(household_size: int, monthly_gross_income: float, children_under_13: int = 0,
                        adults_65_plus: int = 0, has_disability: bool = False, renter: bool = True,
                        monthly_rent: float = 0, eviction_notice_or_arrears: bool = False, months_in_city: int = 12,
                        work_or_study_hours_per_week: int = 0, monthly_utility_bill: float = 0) -> dict:
    """Screen a household for Port Alder food, utility, rent, child-care and transit programmes (preliminary check).

    Non-binding eligibility screening with estimated benefits and the document checklist for each programme.

    Args:
        household_size: People who live and share meals together (including the applicant).
        monthly_gross_income: Total household income before tax per month, all sources.
        children_under_13: Number of children younger than 13.
        adults_65_plus: Number of household members aged 65 or older.
        has_disability: True if a household member has a certified disability.
        renter: True if the household rents its home.
        monthly_rent: Monthly rent (for Rental Bridge Assistance).
        eviction_notice_or_arrears: True if the household has an eviction notice or at least 1 month of rent arrears.
        months_in_city: Months the household has lived in Port Alder.
        work_or_study_hours_per_week: Hours per week the parent(s) work, study or train (for child care).
        monthly_utility_bill: Average monthly water/sewer/trash bill (for the Utility Relief Credit).

    Returns:
        Per programme: likely eligible / not eligible / needs more information, the reason with the income limit used,
        estimated benefit, processing time and the documents to bring; plus the common documents list.
    """
    if household_size < 1 or monthly_gross_income < 0:
        return err("household_size must be >= 1 and income >= 0")
    b = fixture("gov_benefits")
    progs = {p["code"]: p for p in b["programs"]}
    inc = float(monthly_gross_income)
    out = []

    def row(code: str, verdict: str, reason: str, estimate: str = "") -> None:
        p = progs[code]
        out.append({"program": code, "name": p["name"], "verdict": verdict, "reason": reason, "estimated_benefit": estimate,
                    "processing_days": p.get("processing_days"), "programme_documents": p["extra_documents"]})

    lim = _income_limit(b, 50, household_size)
    afa_ok = inc <= lim
    if afa_ok:
        p = progs["AFA"]
        maxa = p["max_allotment"][min(household_size, 8) - 1] + max(0, household_size - 8) * 155
        est = max(p["minimum_benefit"], round(maxa - p["benefit_reduction_rate"] * max(0.0, inc - p["standard_deduction"])))
        note = " Expedited (7 days) likely: income under $150." if inc < 150 else ""
        row("AFA", "likely eligible", f"Income ${inc:,.0f} <= 50% AMI limit ${lim:,} for {household_size}.{note}",
            f"about ${est}/month (max ${maxa})")
    else:
        row("AFA", "not eligible", f"Income ${inc:,.0f} is above the 50% AMI limit ${lim:,} for {household_size}.")

    lim = _income_limit(b, 60, household_size)
    if inc <= lim:
        p = progs["URC"]
        est = (f"${min(p['credit_cap_monthly'], round(p['credit_rate'] * monthly_utility_bill, 2)):.2f}/month"
               if monthly_utility_bill else f"30% of the bill, up to ${p['credit_cap_monthly']}/month")
        row("URC", "likely eligible", f"Income ${inc:,.0f} <= 60% AMI limit ${lim:,}.", est)
    else:
        row("URC", "not eligible", f"Income ${inc:,.0f} is above the 60% AMI limit ${lim:,}.")

    lim = _income_limit(b, 80, household_size)
    p = progs["RBA"]
    if not renter:
        row("RBA", "not eligible", "Only for households that rent their home.")
    elif inc > lim:
        row("RBA", "not eligible", f"Income ${inc:,.0f} is above the 80% AMI limit ${lim:,}.")
    elif not eviction_notice_or_arrears:
        row("RBA", "needs more information", "Requires an eviction notice or at least one month of rent arrears.")
    elif months_in_city < p["min_residency_months"]:
        row("RBA", "not eligible", f"Requires {p['min_residency_months']} months living in Port Alder ({months_in_city} reported).")
    else:
        est = (f"up to ${min(p['max_amount'], p['max_months'] * monthly_rent):,.0f} paid to the landlord" if monthly_rent
               else f"up to {p['max_months']} months of rent, max ${p['max_amount']:,}")
        row("RBA", "likely eligible", f"Renter at risk of eviction; income ${inc:,.0f} <= 80% AMI limit ${lim:,}.", est)

    lim = _income_limit(b, 85, household_size)
    p = progs["CCS"]
    if children_under_13 <= 0:
        row("CCS", "not eligible", "No children under 13 reported.")
    elif inc > lim:
        row("CCS", "not eligible", f"Income ${inc:,.0f} is above the 85% AMI limit ${lim:,}.")
    elif work_or_study_hours_per_week < p["min_hours_per_week"]:
        row("CCS", "needs more information",
            f"Parent(s) must work, study or train at least {p['min_hours_per_week']} hours a week (reported {work_or_study_hours_per_week}).")
    else:
        rate = p["copay_rate_low"] if inc <= _income_limit(b, 60, household_size) else p["copay_rate_high"]
        row("CCS", "likely eligible", f"Income ${inc:,.0f} <= 85% AMI limit ${lim:,}; {children_under_13} child(ren) under 13.",
            f"family co-pay about ${inc * rate:,.0f}/month ({rate:.0%} of income); DHS pays the rest to a licensed provider")

    p = progs["SDTP"]
    if adults_65_plus > 0 or has_disability:
        price = "free (AFA household)" if afa_ok else f"${p['pass_price']}/month instead of ${p['full_price']}"
        row("SDTP", "likely eligible", "Household member aged 65+ or with a certified disability (no income test).", price)
    else:
        row("SDTP", "not eligible", "Requires a member aged 65+ or with a certified disability.")

    return ok(household_size=household_size, monthly_gross_income=inc, results=out,
              likely_eligible=[r["program"] for r in out if r["verdict"] == "likely eligible"],
              common_documents=b["common_documents"],
              disclaimer="Preliminary screening only - DHS makes the final determination on a complete application.")


@hive_tool("government")
def gov_benefits_application_status(application_id: str) -> dict:
    """Get the status of a benefits application: decision, missing documents, deadlines and next steps.

    Args:
        application_id: Application number, e.g. 'BEN-2026-04417'.

    Returns:
        Applicant, programmes, status, missing documents with the due date and days left, decision or appeal
        deadline, caseworker and where documents can be uploaded.
    """
    b = fixture("gov_benefits")
    aid = application_id.strip().upper()
    app = next((a for a in b["applications"] if a["id"] == aid), None)
    if not app:
        return err(f"no application {aid!r}")
    names = {p["code"]: p["name"] for p in b["programs"]}
    extra = {}
    for key in ("documents_due", "appeal_deadline", "decision_expected"):
        if app.get(key):
            extra[f"days_until_{key}"] = (_date(app[key]) - _today()).days
    return ok(application={**app, "program_names": [names[c] for c in app["programs"]]}, as_of=_today().isoformat(), **extra)


# =================================================================================================================
# Grants
# =================================================================================================================


def _focus_match(wanted: list[str], offered: list[str]) -> list[str]:
    hits = []
    for w in wanted:
        k = _norm(w).replace(" ", "_")
        for o in offered:
            if k and (k in o or o in k or any(t in o for t in k.split("_") if len(t) > 3)):
                hits.append(o)
    return sorted(set(hits))


@hive_tool("government")
def gov_grants_match(applicant_type: str, focus_areas: list[str], requested_amount: float, annual_budget: float = 0,
                     years_operating: int = 0, employees: int = 0, annual_revenue: float = 0,
                     neighborhood: str = "") -> dict:
    """Match a nonprofit, community group, school or small business to open Port Alder grant opportunities.

    Args:
        applicant_type: nonprofit, community_group, school or small_business.
        focus_areas: What the project does, e.g. ['youth_employment', 'summer_jobs'] or ['facade', 'signage'].
        requested_amount: Amount the applicant wants to request (USD).
        annual_budget: Organisation's annual operating budget (nonprofits/schools).
        years_operating: Years the organisation has operated.
        employees: Number of employees (small businesses).
        annual_revenue: Annual revenue (small businesses).
        neighborhood: Neighbourhood of the project (some grants require a commercial corridor).

    Returns:
        Each opportunity with verdict (strong fit / eligible - weaker fit / not eligible / closed), eligibility
        reasons, matched focus areas, award range, required match, deadline and days left - best fits first.
    """
    g = fixture("gov_grants")
    at = _norm(applicant_type).replace(" ", "_")
    rows = []
    for o in g["opportunities"]:
        reasons, blocking = [], []
        days_left = (_date(o["deadline"]) - _today()).days
        if o["status"] != "open" or days_left < 0:
            rows.append({"id": o["id"], "name": o["name"], "verdict": "closed", "deadline": o["deadline"]})
            continue
        if at not in o["applicant_types"]:
            blocking.append(f"applicant type '{at}' not eligible (accepts {', '.join(o['applicant_types'])})")
        if at in o.get("fiscal_sponsor_required_for", []):
            reasons.append("needs a fiscal sponsor (registered nonprofit)")
        if o.get("min_annual_budget") and annual_budget and annual_budget < o["min_annual_budget"]:
            blocking.append(f"annual budget below ${o['min_annual_budget']:,}")
        if o.get("min_years_operating") and years_operating and years_operating < o["min_years_operating"]:
            blocking.append(f"needs {o['min_years_operating']}+ years of operation")
        if o.get("max_employees") and employees > o["max_employees"]:
            blocking.append(f"more than {o['max_employees']} employees")
        if o.get("max_annual_revenue") and annual_revenue > o["max_annual_revenue"]:
            blocking.append(f"revenue above ${o['max_annual_revenue']:,}")
        if o.get("corridor_required") and neighborhood and neighborhood.title() not in g["corridors"]:
            blocking.append(f"project must be in a commercial corridor ({', '.join(g['corridors'])})")
        if not o["award_min"] <= requested_amount <= o["award_max"]:
            reasons.append(f"request ${requested_amount:,.0f} outside the ${o['award_min']:,}-${o['award_max']:,} range "
                           f"(adjust to {'the maximum' if requested_amount > o['award_max'] else 'the minimum'})")
        fit = _focus_match(focus_areas, o["focus_areas"])
        verdict = "not eligible" if blocking else "strong fit" if fit else "eligible - weaker fit"
        match_amt = round(min(requested_amount, o["award_max"]) * o.get("match_pct", 0) / 100)
        rows.append({"id": o["id"], "name": o["name"], "verdict": verdict, "blocking": blocking, "notes": reasons,
                     "matched_focus": fit, "award_range": f"${o['award_min']:,}-${o['award_max']:,}",
                     "match_required": f"{o.get('match_pct', 0)}% ({o.get('match_type', 'n/a')}) = ${match_amt:,}" if o.get("match_pct") else "none",
                     "deadline": o["deadline"], "days_left": days_left,
                     "rubric": [f"{c['name']} ({c['weight']})" for c in o["rubric"]]})
    order = {"strong fit": 0, "eligible - weaker fit": 1, "not eligible": 2, "closed": 3}
    rows.sort(key=lambda r: (order[r["verdict"]], r.get("days_left", 999)))
    return ok(applicant_type=at, opportunities=rows, focus_vocabulary=sorted({f for o in g["opportunities"] for f in o["focus_areas"]}))


@hive_tool("government")
def gov_grants_application(application_id: str) -> dict:
    """Load a submitted grant application with its opportunity rubric and automatic eligibility/completeness checks.

    Args:
        application_id: Application number, e.g. 'GA-2026-0147'.

    Returns:
        Application facts, the narrative document key (read it with get_sample_document), the opportunity's scoring
        rubric (criteria and weights), pass/fail threshold checks and missing attachments.
    """
    g = fixture("gov_grants")
    aid = application_id.strip().upper()
    app = next((a for a in g["applications"] if a["id"] == aid), None)
    if not app:
        return err(f"no application {aid!r}", available=[a["id"] for a in g["applications"]])
    o = next(x for x in g["opportunities"] if x["id"] == app["opportunity"])
    checks = []

    def chk(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})

    chk("Applicant type", app["applicant_type"] in o["applicant_types"], f"{app['applicant_type']} (accepts {', '.join(o['applicant_types'])})")
    chk("Award range", o["award_min"] <= app["requested"] <= o["award_max"],
        f"requested ${app['requested']:,} vs ${o['award_min']:,}-${o['award_max']:,}")
    if o.get("min_annual_budget"):
        chk("Minimum annual budget", app.get("annual_budget", 0) >= o["min_annual_budget"], f"${app.get('annual_budget', 0):,} vs ${o['min_annual_budget']:,}")
    if o.get("min_years_operating"):
        chk("Years operating", app.get("years_operating", 0) >= o["min_years_operating"], f"{app.get('years_operating', 0)} vs {o['min_years_operating']}")
    if o.get("match_pct"):
        need = round(app["requested"] * o["match_pct"] / 100)
        chk("Match documented", app.get("match_documented", 0) >= need,
            f"${app.get('match_documented', 0):,} documented vs ${need:,} required ({o['match_pct']}% {o.get('match_type', '')})")
    if o.get("max_employees"):
        chk("Employees", app.get("employees", 0) <= o["max_employees"], f"{app.get('employees')} (max {o['max_employees']})")
    if o.get("max_annual_revenue"):
        chk("Revenue", app.get("annual_revenue", 0) <= o["max_annual_revenue"], f"${app.get('annual_revenue', 0):,} (max ${o['max_annual_revenue']:,})")
    if o.get("corridor_required"):
        chk("Commercial corridor", app.get("neighborhood") in g["corridors"], f"{app.get('neighborhood')}")
    if "fiscal_sponsor_required_for" in o and app["applicant_type"] in o["fiscal_sponsor_required_for"]:
        chk("Fiscal sponsor", bool(app.get("fiscal_sponsor")), app.get("fiscal_sponsor") or "none")
    if app.get("tenant"):
        chk("Property-owner consent (tenant)", app["attachments"].get("property-owner consent letter", False), "required for tenants")
    missing = [k for k, v in app.get("attachments", {}).items() if not v]
    return ok(application=app, opportunity={"id": o["id"], "name": o["name"], "deadline": o["deadline"]},
              rubric=o["rubric"], score_scale=g["score_scale"], funding_bands=g["funding_bands"],
              threshold_checks=checks, failed_checks=[c["check"] for c in checks if c["result"] == "fail"],
              missing_attachments=missing, narrative_doc=app.get("narrative_doc"))


@hive_tool("government")
def gov_grants_score_rubric(opportunity_id: str, scores: list[dict]) -> dict:
    """Validate reviewer scores against an opportunity's rubric and compute the weighted total and funding band.

    Args:
        opportunity_id: Opportunity id, e.g. 'YOF-27'.
        scores: One entry per rubric criterion: {"criterion": "<criterion id>", "score": 0-5, "evidence": "<quote or
            fact from the application>"}. Call gov_grants_application first to get the criterion ids.

    Returns:
        Points per criterion (score / 5 x weight), total out of 100, funding band (Highly recommended >= 85,
        Recommended >= 70, Fund if money remains >= 60, Not recommended) and validation issues to fix.
    """
    g = fixture("gov_grants")
    o = next((x for x in g["opportunities"] if x["id"] == opportunity_id.strip().upper()), None)
    if not o or not o["rubric"]:
        return err(f"unknown or closed opportunity {opportunity_id!r}")
    crit = {c["id"]: c for c in o["rubric"]}
    issues, lines, seen = [], [], set()
    for s in scores:
        cid = str(s.get("criterion", "")).strip()
        if cid not in crit:
            issues.append(f"unknown criterion {cid!r} (use: {', '.join(crit)})")
            continue
        if cid in seen:
            issues.append(f"criterion {cid} scored twice")
            continue
        seen.add(cid)
        try:
            sc = float(s.get("score"))
        except (TypeError, ValueError):
            issues.append(f"{cid}: score must be a number 0-5")
            continue
        if not 0 <= sc <= 5:
            issues.append(f"{cid}: score {sc} outside 0-5")
            continue
        if len(str(s.get("evidence", "")).strip()) < 10:
            issues.append(f"{cid}: add evidence from the application")
        lines.append({"criterion": cid, "name": crit[cid]["name"], "weight": crit[cid]["weight"], "score": sc,
                      "points": round(sc / 5 * crit[cid]["weight"], 1), "evidence": s.get("evidence", "")})
    for cid in crit:
        if cid not in seen:
            issues.append(f"missing score for {cid} ({crit[cid]['name']})")
    total = round(sum(line["points"] for line in lines), 1)
    band = next(b["label"] for b in g["funding_bands"] if total >= b["min"])
    return ok(opportunity=o["id"], lines=lines, total=total, max_total=100, band=band, complete=not issues, issues=issues)


# =================================================================================================================
# Licensing
# =================================================================================================================

_LIC_SYNONYMS = [
    (("food truck", "mobile food", "mobile vend", "street food", "taco truck"), "MFV"),
    (("restaurant", "food service", "cafe", "café", "bakery", "kitchen", "diner"), "FSE"),
    (("short-term", "short term", "vacation rental", "guest suite", "holiday let"), "STR"),
    (("home occupation", "home-based", "home based", "from home"), "HOC"),
    (("contractor", "builder", "roofing", "electrician", "plumber"), "CTR"),
    (("taxi", "ride", "livery", "chauffeur", "driver"), "LDP"),
    (("alcohol", "liquor", "bar", "beer", "wine"), "ABE"),
    (("general", "business licence", "business license", "shop", "retail", "office"), "GBL"),
]


def _lic_type(q: str) -> dict | None:
    types = {t["code"]: t for t in fixture("gov_licensing")["license_types"]}
    code = q.strip().upper()
    if code in types:
        return types[code]
    ql = q.lower()
    for keys, c in _LIC_SYNONYMS:
        if any(k in ql for k in keys):
            return types[c]
    return None


def _lic_fee(t: dict, employees: int = 0, seats: int = 0) -> tuple[float, list[dict]]:
    if "fee_by_employees" in t:
        fee = next(b["fee"] for b in t["fee_by_employees"] if employees <= b["max"])
        return fee, [{"item": f"{t['name']} ({employees} employees)", "usd": fee}]
    lines = [{"item": f"{t['name']} base fee", "usd": t["base_fee"]}]
    if t.get("per_50_seats_fee"):
        blocks = max(1, math.ceil(seats / 50)) if seats else 1
        lines.append({"item": f"Seating fee ({blocks} x 50-seat block{'s' if blocks > 1 else ''})", "usd": blocks * t["per_50_seats_fee"]})
    if t.get("fire_inspection_fee"):
        lines.append({"item": "Fire inspection", "usd": t["fire_inspection_fee"]})
    return sum(x["usd"] for x in lines), lines


@hive_tool("government")
def gov_license_requirements(license_type: str, employees: int = 0, seats: int = 0) -> dict:
    """Get the requirements, fees, inspections and processing time for a Port Alder business or professional licence.

    Args:
        license_type: Code (GBL, FSE, MFV, STR, HOC, CTR, LDP, ABE) or plain words such as 'food truck',
            'restaurant', 'short-term rental', 'contractor', 'taxi driver'.
        employees: Number of employees (sets the General Business Licence fee band).
        seats: Seating capacity (Food Service Establishment fee).

    Returns:
        Licence name, requirements checklist, inspections, fee lines and total, processing time, prerequisite
        licences (e.g. the General Business Licence) with their fees, first-year total and renewal rules.
    """
    lic = fixture("gov_licensing")
    t = _lic_type(license_type)
    if not t:
        return err(f"unknown licence type {license_type!r}", types={x["code"]: x["name"] for x in lic["license_types"]})
    fee, lines = _lic_fee(t, employees, seats)
    prereq = []
    if t["code"] != "GBL" and any("General Business Licence" in r for r in t["requirements"]):
        g = next(x for x in lic["license_types"] if x["code"] == "GBL")
        gfee, glines = _lic_fee(g, employees)
        prereq.append({"code": "GBL", "name": g["name"], "fee": gfee, "requirements": g["requirements"]})
    total = fee + sum(p["fee"] for p in prereq)
    return ok(code=t["code"], name=t["name"], requirements=t["requirements"], inspections=t["inspections"],
              fee_lines=lines, fee_total=fee, processing_business_days=t["processing_business_days"],
              prerequisite_licences=prereq, first_year_total=total, notes=t.get("notes", ""),
              renewal_rules=lic["renewal_rules"])


@hive_tool("government")
def gov_license_lookup(license_number: str = "", business_name: str = "") -> dict:
    """Look up an existing licence and compute today's renewal position: window, late penalty, amount due or cancellation.

    Args:
        license_number: Licence number, e.g. 'LIC-GBL-2023-04411'.
        business_name: Alternatively, part of the business name (e.g. 'Tidewater').

    Returns:
        Licence record, renewal status (active / renewal window open / expired - late renewal / cancelled), days to
        expiry or days expired, renewal fee lines with late penalty, total due and open items to fix before renewal.
    """
    lic = fixture("gov_licensing")
    rules = lic["renewal_rules"]
    q = license_number.strip().upper()
    rec = next((x for x in lic["licenses"] if x["number"] == q), None) if q else None
    if not rec and business_name:
        rec = next((x for x in lic["licenses"] if business_name.lower() in x["business"].lower()), None)
    if not rec:
        return err("licence not found", known=[f"{x['number']} - {x['business']}" for x in lic["licenses"]])
    t = next(x for x in lic["license_types"] if x["code"] == rec["type"])
    fee, lines = _lic_fee(t, rec.get("employees", 0), rec.get("seats", 0))
    exp = _date(rec["expires"])
    days = (exp - _today()).days
    out = {"licence": rec, "type_name": t["name"], "expires": rec["expires"], "as_of": _today().isoformat()}
    if days >= 0:
        opens = exp - dt.timedelta(days=rules["window_opens_days_before_expiry"])
        status = "renewal window open" if _today() >= opens else "active"
        return ok(**out, renewal_status=status, days_to_expiry=days, renewal_window_opens=opens.isoformat(),
                  fee_lines=lines, total_due=fee, open_items=rec.get("open_items", []))
    expired = -days
    if expired > rules["cancel_after_days_expired"]:
        return ok(**out, renewal_status="cancelled - new application required", days_expired=expired,
                  rule=rules["reinstatement"], new_application_fee=fee, fee_lines=lines,
                  citation_risk=f"Operating without a licence can be cited ${rules['operating_without_licence_citation']}.",
                  open_items=rec.get("open_items", []))
    months = math.ceil(expired / 30)
    pct = min(rules["late_penalty_pct_per_month"] * months, rules["late_penalty_cap_pct"])
    penalty = _money(fee * pct / 100)
    return ok(**out, renewal_status="expired - late renewal allowed", days_expired=expired,
              late_months=months, late_penalty_pct=pct,
              fee_lines=lines + [{"item": f"Late penalty {pct}% ({months} month{'s' if months > 1 else ''} or part)", "usd": penalty}],
              total_due=_money(fee + penalty),
              cancellation_date=(exp + dt.timedelta(days=rules["cancel_after_days_expired"])).isoformat(),
              open_items=rec.get("open_items", []))


# =================================================================================================================
# Permits
# =================================================================================================================

_USE_SYNONYMS = {"accessory dwelling": "adu", "granny flat": "adu", "backyard cottage": "adu", "adu": "adu",
                 "deck": "deck", "porch": "deck", "addition": "addition", "extension": "addition", "fence": "fence",
                 "solar": "solar_pv", "demolition": "demolition", "event": "special_event", "festival": "special_event",
                 "market": "special_event", "restaurant": "restaurant", "cafe": "restaurant", "bar": "bar",
                 "retail": "retail", "shop": "retail", "office": "office", "warehouse": "warehouse",
                 "tenant improvement": "tenant_improvement", "house": "single_family", "single family": "single_family",
                 "duplex": "duplex", "daycare": "small_daycare", "brewery": "brewery"}


def _parcel(q: str) -> dict | None:
    q = q.strip().lower()
    if not q:
        return None
    for p in fixture("gov_permits")["parcels"]:
        if q in (p["apn"], p["address"].lower()) or q.replace("apn", "").strip() == p["apn"] or p["address"].lower() in q:
            return p
    return None


@hive_tool("government")
def gov_permit_zoning_check(parcel: str, proposed_use: str, floor_area_sqft: float = 0, footprint_sqft: float = 0,
                            height_ft: float = 0, front_setback_ft: float = -1, side_setback_ft: float = -1,
                            rear_setback_ft: float = -1) -> dict:
    """Check a proposed project or use against the parcel's zoning district, ADU standards and overlay districts.

    Args:
        parcel: Assessor parcel number (e.g. '104-221-017') or street address (e.g. '2218 Willow Terrace').
        proposed_use: e.g. 'ADU', 'deck', 'addition', 'restaurant', 'special event', 'retail'.
        floor_area_sqft: New floor area (for ADUs and additions).
        footprint_sqft: New ground footprint added to lot coverage (defaults to floor_area_sqft when omitted).
        height_ft: Height of the new structure.
        front_setback_ft: Distance to the front lot line (-1 = not provided).
        side_setback_ft: Distance to the nearest side lot line (-1 = not provided).
        rear_setback_ft: Distance to the rear lot line (-1 = not provided).

    Returns:
        Parcel facts, zone, whether the use is allowed / conditional / prohibited, a pass/fail table for height,
        coverage, setbacks and ADU standards, overlay requirements (historic, flood) and the overall verdict.
    """
    pm = fixture("gov_permits")
    p = _parcel(parcel)
    if not p:
        return err(f"parcel {parcel!r} not found", parcels=[f"{x['apn']} {x['address']}" for x in pm["parcels"]])
    z = pm["zoning_districts"][p["zone"]]
    use_l = proposed_use.lower()
    use = next((v for k, v in _USE_SYNONYMS.items() if k in use_l), _norm(proposed_use).replace(" ", "_"))
    if use in z["allowed"]:
        use_status = "allowed"
    elif use in z["conditional"]:
        use_status = "conditional - needs a Conditional Use Permit (Planning Commission hearing)"
    else:
        use_status = "not allowed in this zone"
    checks = []

    def chk(name: str, value: float, limit: float, ok_: bool, unit: str = "ft") -> None:
        checks.append({"check": name, "proposed": f"{value:g} {unit}", "limit": f"{limit:g} {unit}", "result": "pass" if ok_ else "fail"})

    adu = pm["adu_standards"]
    foot = footprint_sqft or floor_area_sqft
    if foot:
        cov = (p["existing_coverage_sqft"] + foot) / p["lot_sqft"] * 100
        chk("Lot coverage", round(cov, 1), z["max_lot_coverage_pct"], cov <= z["max_lot_coverage_pct"], "%")
    if use == "adu":
        if floor_area_sqft:
            chk("ADU floor area", floor_area_sqft, adu["max_floor_area_sqft"], floor_area_sqft <= adu["max_floor_area_sqft"], "sq ft")
        if height_ft:
            chk("ADU height", height_ft, adu["max_height_ft"], height_ft <= adu["max_height_ft"])
        for label, v in (("ADU side setback", side_setback_ft), ("ADU rear setback", rear_setback_ft)):
            if v >= 0:
                chk(label, v, adu["min_side_rear_setback_ft"], v >= adu["min_side_rear_setback_ft"])
    else:
        if height_ft:
            chk("Height", height_ft, z["max_height_ft"], height_ft <= z["max_height_ft"])
        for side, v in (("front", front_setback_ft), ("side", side_setback_ft), ("rear", rear_setback_ft)):
            if v >= 0:
                chk(f"{side.title()} setback", v, z["setbacks_ft"][side], v >= z["setbacks_ft"][side])
    overlays = [{"overlay": o, **pm["overlays"][o]} for o in p["overlays"]]
    missing = [] if use not in ("adu", "addition", "deck") else [
        n for n, v in (("height", height_ft), ("floor area or footprint", foot),
                       ("side setback", side_setback_ft if side_setback_ft >= 0 else 0)) if not v]
    if use_status.startswith("not allowed") or any(c["result"] == "fail" for c in checks):
        verdict = "does not comply"
    elif use_status.startswith("conditional") or overlays:
        verdict = "complies with conditions"
    elif missing:
        verdict = "needs information"
    else:
        verdict = "complies"
    return ok(parcel=p, zone=p["zone"], zone_name=z["name"], use=use, use_status=use_status, checks=checks,
              overlay_requirements=overlays, missing_inputs=missing, verdict=verdict,
              zone_standards={"max_height_ft": z["max_height_ft"], "max_lot_coverage_pct": z["max_lot_coverage_pct"],
                              "setbacks_ft": z["setbacks_ft"]},
              adu_standards=adu if use == "adu" else None)


def _valuation_fee(v: float) -> float:
    for t in fixture("gov_permits")["fees"]["valuation_tiers"]:
        if v <= t["up_to"]:
            return _money(t["base"] + t["rate_per_1000"] * max(0.0, v - t["over"]) / 1000)
    return 0.0


@hive_tool("government")
def gov_permit_estimate(permit_type: str, valuation_usd: float = 0, new_floor_area_sqft: float = 0, parcel: str = "",
                        expedited: bool = False, attendance: int = 0, event_date: str = "", event_days: int = 1,
                        street_closure_blocks: int = 0, food_vendors: int = 0, alcohol: bool = False,
                        amplified_sound: bool = False) -> dict:
    """Estimate building or special-event permit fees with documents, plan-review checklist, inspections and timing.

    Args:
        permit_type: ADU, RES_ADDITION, DECK, COMMERCIAL_TI, SOLAR_PV, DEMOLITION, FENCE or SPECIAL_EVENT.
        valuation_usd: Construction valuation (building permits).
        new_floor_area_sqft: New habitable floor area (impact fee) or deck area for DECK.
        parcel: Parcel number or address - adds historic/flood overlay fees and park site fees.
        expedited: Request expedited plan review (+50% of the plan review fee, about half the review time).
        attendance: Expected peak attendance (SPECIAL_EVENT).
        event_date: First event day YYYY-MM-DD (SPECIAL_EVENT) - checks the application lead time.
        event_days: Number of event days (SPECIAL_EVENT).
        street_closure_blocks: City blocks closed to traffic (SPECIAL_EVENT).
        food_vendors: Number of food vendors needing temporary food permits (SPECIAL_EVENT).
        alcohol: Alcohol will be served (SPECIAL_EVENT).
        amplified_sound: Amplified music or PA system (SPECIAL_EVENT).

    Returns:
        Fee lines and total (estimate; final fees are set at intake), documents, plan-review checklist, inspection
        sequence and review time; for events also the apply-by date, insurance, toilets, security and police detail.
    """
    pm = fixture("gov_permits")
    code = permit_type.strip().upper().replace(" ", "_").replace("-", "_")
    code = {"EVENT": "SPECIAL_EVENT", "ACCESSORY_DWELLING_UNIT": "ADU", "ADDITION": "RES_ADDITION", "TI": "COMMERCIAL_TI",
            "TENANT_IMPROVEMENT": "COMMERCIAL_TI", "SOLAR": "SOLAR_PV"}.get(code, code)
    t = pm["permit_types"].get(code)
    if not t:
        return err(f"unknown permit type {permit_type!r}", types=sorted(pm["permit_types"]))
    f = pm["fees"]
    p = _parcel(parcel) if parcel else None
    lines: list[dict] = []
    extra: dict = {}
    if code == "SPECIAL_EVENT":
        if attendance <= 0:
            return err("attendance is required for a special event estimate")
        band = next(b for b in t["base_fee_by_attendance"] if attendance <= b["max"])
        days = max(1, event_days)
        lines.append({"item": f"Special event permit ({attendance:,} attendees)", "usd": band["fee"]})
        if street_closure_blocks:
            lines.append({"item": f"Street closure {street_closure_blocks} block(s) x {days} day(s)",
                          "usd": street_closure_blocks * days * t["street_closure_per_block_per_day"]})
        if p and p.get("site_fee_per_day"):
            lines.append({"item": f"Park site fee - {p['address']} x {days} day(s)", "usd": p["site_fee_per_day"] * days})
            if attendance > p.get("event_capacity", 10 ** 9):
                extra["capacity_warning"] = f"Attendance exceeds the site capacity of {p['event_capacity']:,}."
        if food_vendors:
            lines.append({"item": f"Temporary food permits x {food_vendors}", "usd": food_vendors * t["temporary_food_permit_per_vendor"]})
        if alcohol:
            lines.append({"item": "Temporary alcohol endorsement", "usd": t["temporary_alcohol_endorsement"]})
        if amplified_sound:
            lines.append({"item": "Amplified sound permit (sound must end by 22:00)", "usd": t["amplified_sound_permit"]})
        toilets = math.ceil(attendance / t["toilets_per_attendees"])
        extra.update(lead_time_days=band["lead_days"], insurance_required=f"${band['insurance']:,} general liability, City named as additional insured",
                     toilets_required=toilets, accessible_toilets=max(1, math.ceil(toilets * t["accessible_toilet_share"])),
                     security_guards=math.ceil(attendance / t["security_guard_per_attendees"]),
                     police_detail_required=attendance >= t["police_detail_from_attendance"])
        ev = _date(event_date) if event_date else None
        if ev:
            apply_by = ev - dt.timedelta(days=band["lead_days"])
            extra.update(apply_by=apply_by.isoformat(), days_left_to_apply=(apply_by - _today()).days,
                         lead_time_ok=_today() <= apply_by)
    else:
        if t["fee_basis"] == "flat":
            lines.append({"item": f"{t['name']} (flat fee)", "usd": t["flat_fee"]})
        else:
            if valuation_usd <= 0:
                return err("valuation_usd is required for this permit type")
            bp = _valuation_fee(valuation_usd)
            lines.append({"item": f"Building permit fee (valuation ${valuation_usd:,.0f})", "usd": bp})
            needs_review = t["plan_review"] is True or (code == "DECK" and new_floor_area_sqft > 200)
            if code == "DECK" and not needs_review:
                extra["plan_review_note"] = "Plan review only if the deck is more than 30 in above grade or larger than 200 sq ft."
            if needs_review:
                pr = _money(bp * f["plan_review_pct"] / 100)
                lines.append({"item": f"Plan review ({f['plan_review_pct']}% of permit fee)", "usd": pr})
                if expedited:
                    lines.append({"item": f"Expedited review (+{f['expedite_pct_of_plan_review']}% of plan review)",
                                  "usd": _money(pr * f["expedite_pct_of_plan_review"] / 100)})
        if code in ("ADU", "RES_ADDITION") and new_floor_area_sqft:
            waived = code == "ADU" and new_floor_area_sqft < pm["adu_standards"]["impact_fee_waiver_below_sqft"]
            lines.append({"item": f"Development impact fee ({new_floor_area_sqft:g} sq ft x ${f['impact_fee_per_sqft']})"
                                  + (" - WAIVED (ADU under 750 sq ft)" if waived else ""),
                          "usd": 0 if waived else _money(new_floor_area_sqft * f["impact_fee_per_sqft"])})
        if p:
            for o in p["overlays"]:
                ov = pm["overlays"][o]
                lines.append({"item": f"{ov['name']} review", "usd": ov["fee"]})
        days = t["expedited_review_business_days"] if expedited else t["review_business_days"]
        extra.update(review_business_days=days, earliest_decision=_add_business_days(_today(), days).isoformat())
    subtotal = _money(sum(x["usd"] for x in lines))
    sur = _money(subtotal * f["technology_surcharge_pct"] / 100)
    lines.append({"item": f"Technology & records surcharge ({f['technology_surcharge_pct']}%)", "usd": sur})
    return ok(permit_type=code, name=t["name"], parcel=p["address"] if p else None, fee_lines=lines,
              total_usd=_money(subtotal + sur), documents=t["documents"], plan_review_checklist=t["plan_review_checklist"],
              inspections=t["inspections"], **extra, note="Estimate - final fees are confirmed at intake.")


_INSP_ALIASES = {"rough": "rough_mep", "mep": "rough_mep", "electrical": "rough_mep", "plumbing": "rough_mep",
                 "mechanical": "rough_mep", "foundation": "foundation", "footing": "footing", "framing": "framing",
                 "insulation": "insulation", "final": "final", "sprinkler": "fire_sprinkler", "health": "health"}


@hive_tool("government", kind="action")
def gov_permit_schedule_inspection(permit_number: str, inspection_type: str, preferred_date: str = "",
                                   preferred_window: str = "AM") -> dict:
    """Book a building inspection for an issued permit after checking status, contractor and sequence (simulated).

    Checks permit status, contractor registration, the inspection sequence (prerequisites must have passed) and
    inspector availability.

    Args:
        permit_number: Permit number, e.g. 'BP-2026-04127'.
        inspection_type: e.g. 'rough electrical/plumbing' (rough_mep), 'framing', 'insulation', 'final'.
        preferred_date: YYYY-MM-DD, or a weekday such as 'next Tuesday' / 'martes' (resolved against the demo
            clock); default: earliest available business day.
        preferred_window: 'AM' (08:00-12:00) or 'PM' (12:30-16:00).

    Returns:
        Booking confirmation with date and window, or the reason it cannot be booked; alternative slots and what to
        have ready on site.
    """
    pm = fixture("gov_permits")
    permit = next((x for x in pm["permits"] if x["number"] == permit_number.strip().upper()), None)
    if not permit:
        return err(f"permit {permit_number!r} not found")
    seq = pm["permit_types"][permit["type"]]["inspections"]
    il = inspection_type.lower()
    itype = next((v for k, v in _INSP_ALIASES.items() if k in il), _norm(inspection_type).replace(" ", "_"))
    if permit["status"] != "issued":
        return err(f"permit status is '{permit['status']}' - inspections need an issued permit",
                   corrections=permit.get("corrections", []))
    if not permit.get("contractor_registration_active", True):
        return err("contractor registration is not active - inspections are on hold", notes=permit.get("notes", ""),
                   fix="Renew the contractor registration or have the owner substitute a registered contractor.")
    if itype not in seq:
        return err(f"{itype} is not an inspection for {permit['type']}", sequence=seq)
    passed = {i["type"] for i in permit["inspections"] if i["result"] == "passed"}
    if itype in passed:
        return err(f"{itype} inspection already passed", inspections=permit["inspections"])
    missing = [s for s in seq[: seq.index(itype)] if s not in passed]
    if missing:
        return err(f"prerequisite inspections not passed yet: {', '.join(missing)}", sequence=seq)
    cal = pm["inspection_calendar"]
    earliest = _next_business_day(_today() + dt.timedelta(days=1))
    want = (_date(preferred_date) or _weekday_date(preferred_date)) if preferred_date else earliest
    want = max(want or earliest, earliest)
    win = "PM" if preferred_window.strip().upper().startswith("P") else "AM"
    notes = []
    if want.isoformat() in _holidays():
        notes.append(f"{want} is {_holidays()[want.isoformat()]} (city holiday).")
    d, options = want, []
    for _ in range(15):
        if _is_business_day(d):
            slots = cal["overrides"].get(d.isoformat(), cal["default_open_slots"])
            for w in ([win, "PM" if win == "AM" else "AM"]):
                if slots.get(w, 0) > 0:
                    options.append({"date": d.isoformat(), "weekday": d.strftime("%A"), "window": w, "time": cal["windows"][w],
                                    "open_slots": slots[w]})
        if len(options) >= 3:
            break
        d += dt.timedelta(days=1)
    first = options[0]
    if (first["date"], first["window"]) != (want.isoformat(), win):
        notes.append(f"Requested {want} {win} is not available; booked the next open slot.")
    conf = _sid("INSP-", permit["number"], itype, first["date"], first["window"])
    return ok(confirmation=conf, permit=permit["number"], address=permit["address"], inspection=itype,
              date=first["date"], weekday=first["weekday"], window=first["window"], time=first["time"],
              alternatives=options[1:], notes=notes,
              prepare=["Permit card and approved plans on site", "Work uncovered and accessible",
                       "Adult (18+) present to let the inspector in", f"Cancel by {cal['request_cutoff']} to avoid a re-inspection fee"],
              simulated=True)


# =================================================================================================================
# Public records (FOIA-style)
# =================================================================================================================


def _prr_deadlines(r: dict, rules: dict) -> dict:
    rec = _date(r["received"])
    out = {"received": r["received"], "acknowledge_by": _add_business_days(rec, rules["acknowledge_business_days"]).isoformat()}
    original = _add_business_days(rec, rules["response_business_days"])
    out["original_due"] = original.isoformat()
    due = original
    c = r.get("clarification")
    if c:
        sent = _date(c["sent"])
        used = _business_days_between(rec, sent)
        out["clock_paused_on"] = c["sent"]
        out["business_days_used_before_pause"] = used
        if c.get("answered"):
            due = _add_business_days(_date(c["answered"]), rules["response_business_days"] - used)
        else:
            out["auto_close_if_no_reply"] = (sent + dt.timedelta(days=rules["clarification_auto_close_calendar_days"])).isoformat()
            out["due"] = "paused - waiting for requester"
            return out
    if r.get("extension"):
        notice = _date(r.get("extension_notice_sent", ""))
        out["extension_notice_timely"] = bool(notice and notice <= original)
        due = _add_business_days(original, rules["extension_business_days"])
    out["due"] = due.isoformat()
    if r["status"] != "closed":
        left = _business_days_between(_today(), due)
        out["business_days_left"] = left
        out["risk"] = "overdue" if left < 0 else "due today" if left == 0 else "at risk" if left <= 2 else "on track"
    if r.get("acknowledged") is None and r["status"] != "closed":
        out["acknowledgement_overdue"] = _today() > _date(out["acknowledge_by"])
    return out


@hive_tool("government")
def gov_foia_request_status(request_id: str = "") -> dict:
    """Get a public-records request with its statutory deadlines, or the deadline tracker for all open requests.

    Deadlines follow the Public Records Ordinance: acknowledge in 2 business days, respond in 10 business days, one
    10-day extension with written notice, clock paused while waiting for a clarification (city holidays excluded).

    Args:
        request_id: Request number, e.g. 'PRR-2026-0418'. Leave empty to list every open request by due date.

    Returns:
        Request details with acknowledge-by, due date, business days left, risk (on track / at risk / due today /
        overdue / paused) and a copy-fee estimate; or the list of open requests sorted by urgency.
    """
    f = fixture("gov_foia")
    rules = f["rules"]
    if request_id.strip():
        r = next((x for x in f["requests"] if x["id"] == request_id.strip().upper()), None)
        if not r:
            return err(f"no request {request_id!r}", open=[x["id"] for x in f["requests"] if x["status"] != "closed"])
        pages = r.get("estimated_pages", 0)
        fee = _money(max(0, pages - rules["free_pages"]) * rules["copy_fee_per_page"])
        return ok(request=r, deadlines=_prr_deadlines(r, rules), as_of=_today().isoformat(),
                  fee_estimate={"pages": pages, "paper_copies_usd": fee, "electronic_delivery_usd": 0,
                                "deposit_required": fee > rules["deposit_required_over"],
                                "note": f"First {rules['free_search_hours']} search hours and {rules['free_pages']} pages free; "
                                        f"staff time beyond that ${rules['staff_time_per_hour']}/hour."})
    rows = []
    for r in f["requests"]:
        if r["status"] == "closed":
            continue
        d = _prr_deadlines(r, rules)
        rows.append({"id": r["id"], "requester": r["requester"], "status": r["status"], "assigned_to": r["assigned_to"],
                     "due": d["due"], "business_days_left": d.get("business_days_left"), "risk": d.get("risk", "paused"),
                     "acknowledgement_overdue": d.get("acknowledgement_overdue", False)})
    rows.sort(key=lambda x: (x["business_days_left"] is None, x["business_days_left"] if x["business_days_left"] is not None else 0))
    return ok(as_of=_today().isoformat(), open_requests=rows,
              summary={k: sum(1 for x in rows if x["risk"] == k) for k in ("overdue", "due today", "at risk", "on track", "paused")})


def _record_flags(text: str) -> list[str]:
    flags = []
    if "PRIVILEGED" in text.upper():
        flags.append("E3 attorney-client privilege")
    if re.search(r"\bDRAFT\b|pre-decisional", text, re.I):
        flags.append("E4 deliberative (release facts)")
    if "PROPRIETARY" in text.upper():
        flags.append("E5 proprietary bidder information")
    if re.search(r"VID \d{4}|date of birth|ACCT|home address|mobile \(", text, re.I):
        flags.append("E1 personal information")
    return flags


@hive_tool("government")
def gov_foia_search_records(query: str, date_from: str = "", date_to: str = "", custodian: str = "") -> dict:
    """Search the city's records index (emails, memos, reports, bid files) for records responsive to a request.

    Args:
        query: Keywords from the request in English (the index is in English; translate other languages), e.g.
            'Harbor Street Coastline Paving repaving'.
        date_from: Earliest record date YYYY-MM-DD (optional).
        date_to: Latest record date YYYY-MM-DD (optional).
        custodian: Restrict to one custodian, e.g. 'Gordon Achterberg' (optional).

    Returns:
        Matching records (id, date, custodian, from/to, subject, pages, excerpt) ranked by relevance, likely
        exemptions to review, and total pages.
    """
    f = fixture("gov_foia")
    terms = [t for t in re.findall(r"[a-z0-9\-]+", query.lower()) if len(t) > 2 and t not in {"the", "and", "all", "about", "between", "emails", "records"}]
    if not terms:
        return err("query needs at least one meaningful keyword")
    d0, d1 = _date(date_from) if date_from else None, _date(date_to) if date_to else None
    hits = []
    for r in f["records"]:
        d = _date(r["date"])
        if (d0 and d < d0) or (d1 and d > d1):
            continue
        if custodian and custodian.lower() not in r["custodian"].lower():
            continue
        hay = " ".join([r["subject"], r["text"], r["from"], r["to"], " ".join(r["keywords"])]).lower()
        score = sum(1 for t in terms if t in hay)
        if score >= min(2, len(terms)):
            hits.append((score, r))
    hits.sort(key=lambda x: (-x[0], x[1]["date"]))
    rows = [{"id": r["id"], "date": r["date"], "type": r["type"], "custodian": r["custodian"], "from": r["from"],
             "to": r["to"], "subject": r["subject"], "pages": r["pages"], "excerpt": r["text"][:160],
             "likely_exemptions": _record_flags(r["text"]), "relevance": s} for s, r in hits]
    return ok(query=query, records=rows, count=len(rows), total_pages=sum(r["pages"] for r in rows))


@hive_tool("government")
def gov_foia_suggest_redactions(record_ids: list[str], text: str = "") -> dict:
    """Suggest redactions with exemption codes (personal data, privilege, deliberative, proprietary) before release.

    Covers personal data (E1), attorney-client privilege (E3), deliberative opinions (E4) and proprietary bidder data
    (E5), each with the Public Records Ordinance exemption code.

    Args:
        record_ids: Record ids from gov_foia_search_records, e.g. ['REC-0418-004', 'REC-0418-008']. May be empty
            when text is given.
        text: Optional free text (or a sample document key) to scan instead of / in addition to records.

    Returns:
        Per record: decision (release in full / release with redactions / withhold in full), each suggested redaction
        with exemption code and reason, the redacted text, and a redaction log for the response letter. Suggestions
        need staff review before release.
    """
    f = fixture("gov_foia")
    by_id = {r["id"]: r for r in f["records"]}
    items = []
    for rid in record_ids:
        r = by_id.get(str(rid).strip().upper())
        if not r:
            return err(f"unknown record {rid!r}")
        items.append((r["id"], r["subject"], r["text"]))
    if text.strip():
        t = doc_text(text.strip()) if re.fullmatch(r"[a-z0-9_]+", text.strip()) else None
        items.append(("TEXT", "Pasted text", t or text))
    if not items:
        return err("pass record_ids or text")
    public_domains, public_numbers = set(f["public_domains"]), set(f["public_numbers"])
    patterns = [
        (r"VID[ -]?\d{4}-\d{4}-\d", "E1", "national ID number"),
        (r"(?i)(?:date of birth|DOB)[:\s]+\d{4}-\d{2}-\d{2}", "E1", "date of birth"),
        (r"ACCT[ #:]*[\d-]{8,}", "E1", "bank account number"),
        (r"(?i:home address is|resides at|lives at|my address is)\s+(\d{1,5} [A-Z][\w ]+?(?:Street|Avenue|Drive|Lane|Road|Terrace|Way|Boulevard))", "E1", "private home address"),
    ]
    out, log = [], []
    for rid, subject, body in items:
        if "PRIVILEGED" in body.upper():
            out.append({"record": rid, "subject": subject, "decision": "withhold in full", "redactions": [],
                        "exemption": "E3", "reason": "Attorney-client privileged communication - list it on the privilege log."})
            log.append(f"{rid}: withheld in full - E3 attorney-client privilege")
            continue
        reds = []
        for pat, code, why in patterns:
            for m in re.finditer(pat, body):
                reds.append({"text": m.group(m.lastindex or 0), "exemption": code, "reason": why})
        for m in re.finditer(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", body):
            if m.group(1).lower() not in public_domains:
                reds.append({"text": m.group(0), "exemption": "E1", "reason": "personal email of a private individual"})
        for m in re.finditer(r"\(\d{3}\) \d{3}-\d{4}", body):
            if m.group(0) not in public_numbers:
                reds.append({"text": m.group(0), "exemption": "E1", "reason": "personal phone number"})
        if re.search(r"\bDRAFT\b|pre-decisional", body, re.I):
            for s in re.split(r"(?<=[.!?])\s+", body):
                if re.search(r"(?i)\bopinion\b|recommend|looks high|not for distribution", s):
                    reds.append({"text": s.strip(), "exemption": "E4", "reason": "pre-decisional opinion (facts are released)"})
        if "PROPRIETARY" in body.upper():
            reds.append({"text": "audited financial statements", "exemption": "E5",
                         "reason": "bidder's proprietary financial statements; bid prices are public after award"})
        redacted = body
        for rd in sorted(reds, key=lambda x: -len(x["text"])):
            redacted = redacted.replace(rd["text"], f"[REDACTED {rd['exemption']}]")
        decision = "release with redactions" if reds else "release in full"
        note = ""
        if re.search(r"\bclaim\b", body, re.I):
            note = "Relates to a pending claim - confirm with the City Attorney before release (not privileged on its face)."
        out.append({"record": rid, "subject": subject, "decision": decision, "redactions": reds,
                    "redacted_text": redacted, "review_note": note})
        for rd in reds:
            log.append(f"{rid}: '{rd['text'][:40]}' - {rd['exemption']} ({rd['reason']})")
    return ok(records=out, redaction_log=log, exemption_codes=f["exemptions"],
              summary={k: sum(1 for o in out if o["decision"] == k) for k in ("release in full", "release with redactions", "withhold in full")},
              note="Suggestions only - a records analyst must review every redaction before release.")


# =================================================================================================================
# Legal case review
# =================================================================================================================


@hive_tool("government")
def gov_legal_case_chronology(case_id: str) -> dict:
    """Build a City Attorney case chronology with intervals, statutory deadlines, linked records, gaps and authority.

    Linked references include 311 requests, public-records items and procurement files; the settlement authority
    level is derived from the amount at stake.

    Args:
        case_id: Case number, e.g. 'CLM-2026-0083' (government claim) or 'LIT-2026-0012' (bid protest).

    Returns:
        Parties, amounts, the sorted chronology (with day counts from the first event), deadlines with status
        (met / missed / pending with days left), SLA analysis of any linked 311 request, record gaps and who can
        approve a settlement at the claimed amount.
    """
    lg = fixture("gov_legal")
    case = next((c for c in lg["cases"] if c["id"] == case_id.strip().upper()), None)
    if not case:
        return err(f"no case {case_id!r}", cases=[c["id"] for c in lg["cases"]])
    events = sorted(case["events"], key=lambda e: e["date"])
    start = _date(events[0]["date"])
    chron = [{**e, "day": (_date(e["date"]) - start).days} for e in events]
    deadlines = []
    for rule in case["deadline_rules"]:
        frm = _date(rule["from"])
        if rule["kind"] == "business":
            dl = _add_business_days(frm, rule["days"])
        elif rule["kind"] == "months":
            dl = _add_months(frm, rule["months"])
        else:
            dl = frm + dt.timedelta(days=rule["days"])
        row = {"deadline": rule["name"], "date": dl.isoformat()}
        if rule.get("met_by"):
            met = _date(rule["met_by"])
            row.update(acted_on=rule["met_by"], status="met" if met <= dl else "missed",
                       margin_days=(dl - met).days if rule["kind"] != "business" else _business_days_between(met, dl))
        else:
            row.update(status="pending", days_left=(dl - _today()).days)
        deadlines.append(row)
    refs = sorted(set(re.findall(r"\b(?:SR-\d{4}-\d{6}|PRR-\d{4}-\d{4}|REC-\d{4}-\d{3}|ITB-\d{4}-\d{3}|RFP-\d{4}-\d{3}|WO-\d{4}-\d{5})\b",
                                 " ".join(e["event"] + " " + e["source"] for e in events))))
    sla = []
    s311 = fixture("gov_311")
    cats = {c["code"]: c for c in s311["categories"]}
    incident = next((e for e in events if e.get("tag") == "incident"), None)
    for r in s311["requests"]:
        if r["id"] in refs:
            st = _sla_status(r, cats)
            row = {"request": r["id"], "priority_assigned": r["priority"], "sla_due": st["due"], "closed": r.get("closed"),
                   "hours_to_close": st.get("hours_to_close"), "met": st.get("met")}
            if r["street"] in s311["arterial_streets"] and r["category"] == "POTHOLE":
                p1_due = dt.datetime.fromisoformat(r["created"]) + dt.timedelta(hours=cats[r["category"]]["sla_hours"]["P1"])
                row["arterial_rule"] = f"{r['street']} is an arterial: standard requires P1 (due {p1_due:%Y-%m-%d %H:%M})"
            if incident:
                inc = _date(incident["date"])
                row["days_from_report_to_incident"] = (inc - _date(r["created"])).days
                row["sla_expired_before_incident"] = dt.datetime.fromisoformat(st["due"]).date() < inc
            sla.append(row)
    amount = case.get("demand_letter_amount") or case.get("amount_claimed") or case.get("contract_value", 0)
    who = next(a["who"] for a in lg["settlement_authority"] if amount <= a["max"])
    return ok(case={k: v for k, v in case.items() if k not in ("events", "deadline_rules")}, chronology=chron,
              deadlines=deadlines, linked_references=refs, sla_analysis=sla, record_gaps=case.get("record_gaps", []),
              settlement_authority={"amount": amount, "approver": who}, as_of=_today().isoformat(),
              case_file_doc=case.get("case_file_doc"))


# =================================================================================================================
# Public procurement
# =================================================================================================================

_PROC_CATS = [(("construction", "paving", "repaving", "public works", "road", "building works"), "construction"),
              (("architect", "engineering", "a/e", "surveying", "design services"), "professional_services")]


def _solicitation(sid: str) -> dict | None:
    return next((s for s in fixture("gov_procurement")["solicitations"] if s["id"] == sid.strip().upper()), None)


@hive_tool("government")
def gov_proc_method_check(estimated_value_usd: float = 0, category: str = "goods_services", solicitation_id: str = "",
                          term_years: int = 1, option_years: int = 0, option_value_per_year: float = 0,
                          sole_source: bool = False, emergency: bool = False, quotes_received: int = 0) -> dict:
    """Determine the required procurement method and approvals, or check an existing solicitation's compliance.

    Uses the Procurement Manual thresholds; for an existing solicitation also checks the advertising period, bonds,
    evaluation set-up and approvals.

    Args:
        estimated_value_usd: Estimated contract value for the base term (ignored when solicitation_id is given).
        category: goods_services, construction or professional_services (plain words like 'IT services' or 'paving'
            are mapped).
        solicitation_id: Existing solicitation to check, e.g. 'RFP-2026-031', 'ITB-2026-044', 'RFQ-2026-118'.
        term_years: Base term in years.
        option_years: Number of optional renewal years.
        option_value_per_year: Value of each option year.
        sole_source: True if a sole-source award is proposed.
        emergency: True if an emergency purchase is proposed.
        quotes_received: Number of written quotes obtained (informal purchases).

    Returns:
        Total potential value (base + options), the threshold band and required method, approval level (department,
        CPO, City Council >= $250,000), advertising minimum, and a pass/fail findings list for an existing solicitation.
    """
    pr = fixture("gov_procurement")
    sol = _solicitation(solicitation_id) if solicitation_id else None
    if solicitation_id and not sol:
        return err(f"unknown solicitation {solicitation_id!r}", known=[s["id"] for s in pr["solicitations"]])
    if sol:
        category, estimated_value_usd = sol["category"], sol["estimated_value"]
        option_years, option_value_per_year = sol.get("option_years", 0), sol.get("option_value_per_year", 0)
        quotes_received = len(sol.get("quotes", [])) or quotes_received
    cl = category.lower()
    cat = next((v for keys, v in _PROC_CATS if any(k in cl for k in keys)), "goods_services")
    if cat not in pr["thresholds"]:
        cat = "goods_services"
    total = float(estimated_value_usd) + option_years * float(option_value_per_year)
    if total <= 0:
        return err("estimated_value_usd must be > 0")
    band = next(b for b in pr["thresholds"][cat] if total < b["below"])
    council = total >= pr["council_approval_from"]
    approval = "City Council" if council else "Chief Procurement Officer" if band["method"] not in ("micro_purchase", "informal_quotes", "informal_qualifications") else "Department head"
    adv = 21 if cat == "construction" and band["method"].startswith("formal") else 14 if band["method"] in ("formal", "formal_itb", "qbs") else 0
    findings = []

    def fnd(check: str, passed: bool, detail: str) -> None:
        findings.append({"check": check, "result": "pass" if passed else "fail", "detail": detail})

    if sole_source:
        findings.append({"check": "Sole source", "result": "attention", "detail": "Written justification and CPO approval required; post a 5-business-day notice of intent when >= $50,000."})
    if emergency:
        findings.append({"check": "Emergency", "result": "attention", "detail": "Only for an immediate threat to life or property; City Manager/CPO authorisation; report to Council within 30 days when >= $50,000."})
    if sol:
        m = sol["method"].upper()
        expected = {"formal": ("ITB", "RFP"), "formal_itb": ("ITB",), "qbs": ("RFQ-QBS", "QBS"), "informal_quotes": ("INFORMAL_QUOTES",),
                    "micro_purchase": ("MICRO_PURCHASE",), "informal_qualifications": ("INFORMAL",)}[band["method"]]
        fnd("Method matches threshold", m in expected, f"{sol['method']} used; {band['label']} required for ${total:,.0f}")
        if sol.get("advertised") and sol.get("closed") and adv:
            days = (_date(sol["closed"]) - _date(sol["advertised"])).days
            fnd("Advertising period", days >= adv, f"{days} days advertised (minimum {adv})")
        if m == "RFP":
            pw = next((c["weight"] for c in sol.get("criteria", []) if c["id"] == "price"), 0)
            lo, hi = pr["rfp_price_weight_range"]
            fnd("Price weight", lo <= pw <= hi, f"price weight {pw}% (allowed {lo}-{hi}%)")
            fnd("Evaluation committee size", len(sol.get("evaluators", [])) >= pr["min_evaluators"],
                f"{len(sol.get('evaluators', []))} evaluators (minimum {pr['min_evaluators']})")
            unsigned = [e["name"] for e in sol.get("evaluators", []) if not e.get("coi_form_signed")]
            fnd("Conflict-of-interest forms signed", not unsigned, "all signed" if not unsigned else f"missing: {', '.join(unsigned)}")
        if cat == "construction" and band["method"] == "formal_itb":
            fnd("Bid bond required", sol.get("bid_bond_pct", 0) >= 5, f"{sol.get('bid_bond_pct', 0)}% bid bond in the ITB (5% required)")
        if band["method"] == "informal_quotes":
            fnd("Three written quotes", quotes_received >= 3, f"{quotes_received} quote(s) received")
        if council:
            done = sol.get("council_resolution")
            findings.append({"check": "City Council approval", "result": "pass" if done else "pending",
                             "detail": f"Resolution {done}" if done else f"Required - scheduled {sol.get('council_date', 'not yet scheduled')}"})
    elif band["method"] == "informal_quotes" and quotes_received:
        fnd("Three written quotes", quotes_received >= 3, f"{quotes_received} quote(s) received")
    return ok(category=cat, base_value=float(estimated_value_usd), option_value=option_years * float(option_value_per_year),
              total_potential_value=total, threshold_band=band["label"], required_method=band["method"],
              requirement=band["requirement"], approval_level=approval, council_approval_required=council,
              min_advertising_days=adv, findings=findings, solicitation=sol["id"] if sol else None,
              rules=["Thresholds apply to the total potential value including option years.",
                     "Splitting a requirement to stay under a threshold is prohibited (same need within 12 months is aggregated)."])


@hive_tool("government")
def gov_proc_evaluate_bids(solicitation_id: str, exclude_evaluators: str = "") -> dict:
    """Compute a solicitation's bid evaluation matrix (RFP weighted scores or ITB evaluated prices) with outlier checks.

    RFP: weighted scores with price points and evaluator outlier analysis. ITB: responsiveness and lowest evaluated
    bid with the local preference applied.

    Args:
        solicitation_id: e.g. 'RFP-2026-031', 'ITB-2026-044' or 'RFQ-2026-118'.
        exclude_evaluators: Optional comma-separated evaluator names to drop (e.g. after a recusal).

    Returns:
        Ranked matrix with points per criterion and totals (RFP), or responsive/non-responsive bids with evaluated
        prices (ITB) / quote compliance (RFQ); outlier evaluators and how the ranking changes without each of them;
        the recommended awardee.
    """
    pr = fixture("gov_procurement")
    sol = _solicitation(solicitation_id)
    if not sol:
        return err(f"unknown solicitation {solicitation_id!r}", known=[s["id"] for s in pr["solicitations"]])
    if sol["method"] == "RFP":
        names = [e["name"] for e in sol["evaluators"]]
        drop = {n.strip().lower() for n in exclude_evaluators.split(",") if n.strip()}
        unknown = [d for d in drop if d not in {n.lower() for n in names}]
        if unknown:
            return err(f"unknown evaluator(s): {', '.join(unknown)}", evaluators=names)

        def matrix(skip: set[str]) -> list[dict]:
            idx = [i for i, n in enumerate(names) if n.lower() not in skip]
            low = min(p["price"] for p in sol["proposals"])
            rows = []
            for p in sol["proposals"]:
                pts, total = {}, 0.0
                for c in sol["criteria"]:
                    if c["id"] == "price":
                        v = round(low / p["price"] * c["weight"], 2)
                    else:
                        avg = sum(p["scores"][c["id"]][i] for i in idx) / len(idx)
                        v = round(avg / 10 * c["weight"], 2)
                    pts[c["id"]] = v
                    total += v
                rows.append({"vendor": p["vendor"], "price": p["price"], "points": pts, "total": round(total, 2)})
            rows.sort(key=lambda r: -r["total"])
            for i, r in enumerate(rows, 1):
                r["rank"] = i
            return rows

        main = matrix(drop)
        outliers = []
        non_price = [c["id"] for c in sol["criteria"] if c["id"] != "price"]
        for i, n in enumerate(names):
            if n.lower() in drop:
                continue
            for p in sol["proposals"]:
                mine = sum(p["scores"][c][i] for c in non_price) / len(non_price)
                others = [j for j in range(len(names)) if j != i and names[j].lower() not in drop]
                theirs = sum(p["scores"][c][j] for c in non_price for j in others) / (len(non_price) * len(others))
                if abs(mine - theirs) >= 1.5:
                    outliers.append({"evaluator": n, "vendor": p["vendor"], "evaluator_avg": round(mine, 2),
                                     "others_avg": round(theirs, 2), "deviation": round(mine - theirs, 2)})
        sensitivity = []
        for n in sorted({o["evaluator"] for o in outliers}):
            alt = matrix(drop | {n.lower()})
            sensitivity.append({"without": n, "ranking": [f"{r['rank']}. {r['vendor']} ({r['total']})" for r in alt],
                                "winner_changes": alt[0]["vendor"] != main[0]["vendor"]})
        return ok(solicitation=sol["id"], title=sol["title"], method="RFP", criteria=sol["criteria"],
                  scale=sol["score_scale"], evaluators_used=[n for n in names if n.lower() not in drop], matrix=main,
                  outliers=outliers, sensitivity=sensitivity, recommended=main[0]["vendor"],
                  local_preference_note="Local preference does not apply to RFPs (best value).")
    lp = pr["local_preference"]
    if sol["method"] == "ITB":
        rows = []
        for b in sol["bids"]:
            issues = []
            if not b.get("bid_bond"):
                issues.append("no bid bond enclosed at bid opening (material, non-waivable)")
            if not b.get("registered_contractor", True):
                issues.append("not a registered contractor")
            pref = 0 if sol.get("nationally_funded") or not b.get("local") else min(b["price"] * lp["pct"] / 100, lp["cap"])
            rows.append({"vendor": b["vendor"], "bid_price": b["price"], "local": b.get("local", False),
                         "local_preference": _money(pref), "evaluated_price": _money(b["price"] - pref),
                         "responsive": not issues, "issues": issues, "notes": b.get("notes", "")})
        resp = sorted([r for r in rows if r["responsive"]], key=lambda r: r["evaluated_price"])
        for i, r in enumerate(resp, 1):
            r["rank"] = i
        return ok(solicitation=sol["id"], title=sol["title"], method="ITB", bids=rows, recommended=resp[0]["vendor"] if resp else None,
                  contract_price=resp[0]["bid_price"] if resp else None,
                  local_preference_rule=f"{lp['pct']}% of bid price, capped at ${lp['cap']:,}, for evaluation only - the contract is awarded at the bid price.",
                  estimate=sol["estimated_value"])
    quotes = sorted(sol.get("quotes", []), key=lambda q: q["price"])
    return ok(solicitation=sol["id"], title=sol["title"], method=sol["method"], quotes=quotes,
              quotes_compliant=len(quotes) >= 3, lowest=quotes[0] if quotes else None,
              issue=None if len(quotes) >= 3 else f"Only {len(quotes)} quote(s); 3 written quotes are required between $10,000 and $49,999.")


@hive_tool("government")
def gov_proc_conflict_check(solicitation_id: str) -> dict:
    """Screen a solicitation's evaluators and vendor contacts for conflicts of interest and cone-of-silence breaches.

    Cross-checks evaluators' declarations against HR family declarations, prior employment, the gift register and
    vendor officers, and lists cone-of-silence contacts.

    Args:
        solicitation_id: e.g. 'RFP-2026-031' or 'ITB-2026-044'.

    Returns:
        Per evaluator: findings with severity (recusal required / disclose only / clear) and whether the conflict was
        declared; undeclared conflicts; cone-of-silence contacts needing a CPO determination; recommended actions.
    """
    pr = fixture("gov_procurement")
    sol = _solicitation(solicitation_id)
    if not sol:
        return err(f"unknown solicitation {solicitation_id!r}", known=[s["id"] for s in pr["solicitations"]])
    parties = pr["parties"]
    vendors = [p["vendor"] for p in sol.get("proposals", [])] + [b["vendor"] for b in sol.get("bids", [])] + \
              [q["vendor"] for q in sol.get("quotes", [])]
    officers = {v: parties["vendor_officers"].get(v, []) for v in vendors}
    ref = _date(sol.get("closed", "")) or _today()
    results = []
    for e in sol.get("evaluators", []):
        f_ = []
        for fam in parties["hr_family_declarations"]:
            if fam["employee"] != e["name"]:
                continue
            for v, offs in officers.items():
                if any(fam["relative"] in o for o in offs):
                    declared = fam["relative"].split()[-1].lower() in e["declared"].lower() or v.lower() in e["declared"].lower()
                    f_.append({"severity": "recusal required", "vendor": v, "declared": declared,
                               "detail": f"{fam['relative']} ({fam['relationship']}) is an officer of {v}: "
                                         f"{next(o for o in offs if fam['relative'] in o)}. Source: {fam['source']}."})
        for job in parties["employment_history"]:
            if job["employee"] == e["name"] and job["employer"] in vendors:
                months = (ref.year - _date(job["ended"]).year) * 12 + ref.month - _date(job["ended"]).month
                sev = "recusal required" if months < 24 else "disclose only"
                f_.append({"severity": sev, "vendor": job["employer"], "declared": job["employer"].lower() in e["declared"].lower(),
                           "detail": f"Employed by {job['employer']} until {job['ended']} ({months} months before evaluation; rule: 24 months)."})
        for g in parties["gift_register"]:
            if g["employee"] == e["name"] and g["source"] in vendors:
                within = (ref - _date(g["date"])).days <= 365
                sev = "recusal required" if within and g["value"] > 50 else "disclose only"
                f_.append({"severity": sev, "vendor": g["source"], "declared": g["source"].split()[0].lower() in e["declared"].lower(),
                           "detail": f"{g['description']} on {g['date']} valued ${g['value']} (rule: gifts over $50 in the last 12 months require recusal)."})
        results.append({"evaluator": e["name"], "title": e["title"], "declared": e["declared"],
                        "findings": f_ or [{"severity": "clear", "detail": "No relationships found in HR, employment or gift records."}]})
    undeclared = [f"{r['evaluator']} - {x['vendor']}" for r in results for x in r["findings"]
                  if x["severity"] == "recusal required" and not x.get("declared")]
    cone = sol.get("cone_of_silence_contacts", [])
    actions = []
    for r in results:
        for x in r["findings"]:
            if x["severity"] == "recusal required":
                actions.append(f"Recuse {r['evaluator']} and re-run the evaluation without their scores (gov_proc_evaluate_bids exclude_evaluators).")
    if undeclared:
        actions.append("Refer the undeclared conflict(s) to the Ethics Officer; the CPO documents the remedy in the file.")
    for c in cone:
        if not c.get("cpo_determination"):
            actions.append(f"CPO to document a determination on the {c['date']} cone-of-silence contact by {c['vendor']} (record {c['record']}).")
    return ok(solicitation=sol["id"], title=sol["title"], evaluators=results, undeclared_conflicts=undeclared,
              cone_of_silence_contacts=cone, recommended_actions=sorted(set(actions)) or ["No integrity issues found."],
              note="Evaluator conflicts apply to RFP committees; ITB awards are price-based but cone-of-silence rules still apply.")


# =================================================================================================================
# Farmer Desk (agriculture ministry, national)
# =================================================================================================================


def _producer(q: str) -> dict | None:
    ql = q.strip().lower()
    for p in fixture("gov_agriculture")["producers"]:
        if ql in (p["npr"].lower(), p["national_id"].lower(), p["national_id"].lower().replace("vid ", "")) or ql == p["name"].lower():
            return p
    return None


def _farm_eligibility(p: dict, plots: list[dict]) -> list[dict]:
    ag = fixture("gov_agriculture")
    progs = {x["code"]: x for x in ag["programs"]}
    if not p["identity_verified"]:
        return [{"program": c, "name": progs[c]["name"], "eligible": False,
                 "reason": "Identity not verified with the national identity provider."} for c in progs]
    total = round(sum(x["area_ha"] for x in plots), 2)
    staple = [x for x in plots if x["crop"] in ag["crops"]["staple"]]
    enrolled = {(e["program"], e.get("season")) for e in p["enrolments"]}
    out = []
    r = progs["SIP"]["rules"]
    out.append({"program": "SIP", "name": progs["SIP"]["name"], "eligible": total <= r["max_total_ha"] and bool(staple),
                "reason": (f"Total {total} ha <= {r['max_total_ha']} ha and staple plot registered" if total <= r["max_total_ha"] and staple
                           else f"Total {total} ha exceeds {r['max_total_ha']} ha" if total > r["max_total_ha"]
                           else "Needs a registered staple-crop plot (maize, beans, rice or sorghum)"),
                "enrol_by": progs["SIP"]["enrol_by"], "benefit": progs["SIP"]["benefit"]})
    r = progs["FVP"]["rules"]
    got = ("FVP", "2026-27-dry") in enrolled
    out.append({"program": "FVP", "name": progs["FVP"]["name"], "eligible": total <= r["max_total_ha"] and not got,
                "reason": "Voucher already issued this season (one per season)" if got else
                          (f"Total {total} ha <= {r['max_total_ha']} ha" if total <= r["max_total_ha"] else f"Total {total} ha exceeds {r['max_total_ha']} ha"),
                "enrol_by": progs["FVP"]["enrol_by"], "benefit": progs["FVP"]["benefit"]})
    r = progs["PCI"]["rules"]
    sub = r["subsidy_pct_small"] if total <= r["small_max_ha"] else r["subsidy_pct_large"]
    out.append({"program": "PCI", "name": progs["PCI"]["name"], "eligible": total > 0,
                "reason": f"Premium subsidy {sub}% ({'<=' if total <= r['small_max_ha'] else '>'} {r['small_max_ha']} ha)" if total > 0 else "No registered plots",
                "enrol_by": progs["PCI"]["enrol_by"], "benefit": progs["PCI"]["benefit"]})
    r = progs["CRR"]["rules"]
    coffee = [x for x in plots if x["crop"] == "coffee"]
    ok_plots = [x for x in coffee if x.get("georeferenced") and x["tenure"] in r["requires_tenure"]
                and (x.get("rust_incidence_pct", 0) >= r["min_rust_pct"] or x.get("plant_age_years", 0) >= r["or_min_plant_age_years"])]
    ha = min(sum(x["area_ha"] for x in ok_plots), r["max_ha"])
    out.append({"program": "CRR", "name": progs["CRR"]["name"], "eligible": bool(ok_plots),
                "reason": (f"{', '.join(x['id'] for x in ok_plots)}: georeferenced, eligible tenure, rust/age criteria met" if ok_plots
                           else "Needs a georeferenced coffee plot with title/lease/usufruct/cooperative tenure and rust >= 20% or plants >= 15 years" if coffee
                           else "Only for coffee producers"),
                "max_credit_usd": round(ha * r["per_ha"]) if ok_plots else 0,
                "terms": f"{r['rate_pct']}% a year, {r['term_years']} years, {r['grace_years']} years' grace",
                "enrol_by": progs["CRR"]["enrol_by"], "benefit": progs["CRR"]["benefit"]})
    return out


@hive_tool("government")
def gov_farm_producer_lookup(producer: str) -> dict:
    """Look up a producer in the National Producer Registry with plots, enrolments and programme eligibility.

    Args:
        producer: Producer registry number (e.g. 'NPR-2024-018832'), national ID (e.g. 'VID 0412-7789-3') or full name.

    Returns:
        Identity verification status, registered plots (crop, hectares, tenure, georeference), total area,
        programme enrolments, eligibility for each 2026-27 programme with reason and enrol-by date, and the
        producer's agro-service centre.
    """
    ag = fixture("gov_agriculture")
    p = _producer(producer)
    if not p:
        return err(f"producer {producer!r} not found in the National Producer Registry",
                   next_step="Register as a producer: verify identity with the national identity provider, then visit an agro-service centre.")
    elig = _farm_eligibility(p, p["plots"])
    return ok(producer={k: v for k, v in p.items() if k != "plots"}, plots=p["plots"],
              total_area_ha=round(sum(x["area_ha"] for x in p["plots"]), 2), eligibility=elig,
              service_centre=ag["service_centres"].get(p["municipality"]), season_calendar=ag["season_calendar"],
              as_of=_today().isoformat())


@hive_tool("government", kind="action")
def gov_farm_register_plot(producer: str, crop: str, area_ha: float, tenure_type: str, season: str = "2027-wet",
                           location_shared: bool = False, landowner_id: str = "") -> dict:
    """Register a new plantation/crop plot for a producer in the National Producer Registry (simulated submission).

    Args:
        producer: Producer registry number, national ID or full name.
        crop: maize, beans, rice, sorghum, coffee, cacao, avocado, plantain, vegetables or sugarcane.
        area_ha: Plot area in hectares (0.1-50).
        tenure_type: owner_title, lease, cooperative, usufruct or informal.
        season: '2026-27-dry' or '2027-wet' (planting season).
        location_shared: True if the producer already shared a location pin for the plot on the channel.
        landowner_id: Landowner's national ID (required for leases).

    Returns:
        Submission number, validation results, documents still needed, whether a field verification visit is
        required, review time, and programmes the producer becomes eligible for once approved.
    """
    ag = fixture("gov_agriculture")
    p = _producer(producer)
    if not p:
        return err(f"producer {producer!r} not found - register as a producer first")
    if not p["identity_verified"]:
        return err("identity not verified with the national identity provider - plots cannot be registered yet",
                   issue=p.get("verification_issue"), fix=f"Re-verify identity or visit {ag['service_centres'].get(p['municipality'])}.")
    crops = [c for group in ag["crops"].values() for c in group]
    c = crop.strip().lower()
    if c not in crops:
        return err(f"unknown crop {crop!r}", crops=crops)
    if not 0.1 <= area_ha <= 50:
        return err("area_ha must be between 0.1 and 50")
    tenure = tenure_type.strip().lower().replace(" ", "_")
    tenure = {"owner": "owner_title", "title": "owner_title", "rent": "lease", "rented": "lease", "renting": "lease"}.get(tenure, tenure)
    if tenure not in ag["tenure_documents"]:
        return err(f"unknown tenure type {tenure_type!r}", tenure_types=sorted(ag["tenure_documents"]))
    cal = ag["season_calendar"].get(season)
    if not cal:
        return err(f"unknown season {season!r}", seasons=sorted(ag["season_calendar"]))
    if _today() > _date(cal["registration_closes"]):
        return err(f"registration for {season} closed on {cal['registration_closes']}")
    docs = [ag["tenure_documents"][tenure]]
    issues = []
    if tenure == "lease" and not landowner_id:
        issues.append("Landowner's national ID number is required for a lease.")
    if not location_shared:
        docs.append("Plot location: share a location pin from the plot on the messaging channel, or an agro-technician will georeference it")
    if c == "coffee":
        docs.append("Plant count and approximate plant age")
    field_visit = area_ha > 5 or tenure == "informal"
    new_plot = {"id": "NEW", "crop": c, "area_ha": area_ha, "tenure": tenure, "georeferenced": location_shared, "status": "pending"}
    before = {e["program"] for e in _farm_eligibility(p, p["plots"]) if e["eligible"]}
    after = _farm_eligibility(p, p["plots"] + [new_plot])
    sub = _sid("PLT-2026-", p["npr"], c, area_ha, tenure, season)
    return ok(submission=sub, producer=p["name"], npr=p["npr"], crop=c, area_ha=area_ha, tenure=tenure, season=season,
              planting=cal["planting"], submission_status="submitted - pending review" if not issues else "submitted - incomplete",
              issues=issues, documents_needed=docs, field_verification_required=field_visit,
              review_business_days=10 if field_visit else 5,
              newly_eligible=[e for e in after if e["eligible"] and e["program"] not in before],
              service_centre=ag["service_centres"].get(p["municipality"]), simulated=True)


# --- Farmer Desk: procedure menu and form filling -----------------------------------------------------------------

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_FORM_TEXT = {
    "en": {"field": "Field", "value": "Value", "source": "Source", "registry": "Registry", "farmer": "Producer",
           "simulated": "SIMULATED APPLICATION — synthetic demo data, not a real submission",
           "submission": "Submission", "date": "Date", "applicant": "Applicant", "requirements": "Requirements",
           "next": "Next steps", "fee": "Fee", "review": "Review time", "days": "business days", "free": "No fee",
           "same_day": "Issued at once", "footer": "Filled in by Farmer Desk on the messaging channel"},
    "es": {"field": "Campo", "value": "Valor", "source": "Origen", "registry": "Registro", "farmer": "Productor",
           "simulated": "SOLICITUD SIMULADA — datos sintéticos de demostración, no es un trámite real",
           "submission": "Trámite", "date": "Fecha", "applicant": "Solicitante", "requirements": "Requisitos",
           "next": "Próximos pasos", "fee": "Costo", "review": "Tiempo de respuesta", "days": "días hábiles",
           "free": "Sin costo", "same_day": "Se emite al instante", "footer": "Llenado por la Mesa del Productor en el canal de mensajería"},
}


def _lang(language: str) -> str:
    return "es" if (language or "").strip().lower()[:2] == "es" else "en"


def _loc(item: dict, key: str, lang: str) -> Any:
    return item.get(f"{key}_es", item.get(key)) if lang == "es" else item.get(key)


def _procedure(query: str) -> dict | None:
    ag = fixture("gov_agriculture")
    q = _norm(query)
    if not q:
        return None
    for pr in ag["procedures"]:
        if q in (pr["code"].lower(), pr["form"].lower()):
            return pr
    best, score = None, 0.0
    for pr in ag["procedures"]:
        for k in pr["keywords"] + [pr["name"], pr["name_es"]]:
            kn = _norm(k)
            s = 1.0 if kn in q or q in kn else difflib.SequenceMatcher(None, q, kn).ratio()
            if s > score:
                best, score = pr, s
    return best if score >= 0.6 else None


def _proc_card(pr: dict, lang: str, n: int | None = None) -> dict:
    card = {"code": pr["code"], "name": _loc(pr, "name", lang), "for": _loc(pr, "for", lang), "form": pr["form"],
            "fee_usd": pr["fee_usd"], "review_business_days": pr["business_days"], "channel": _loc(pr, "channel", lang)}
    if "fee_usd_per_head" in pr:
        card["fee_usd_per_head"] = pr["fee_usd_per_head"]
    if n is not None:
        card = {"option": n, **card}
    return card


@hive_tool("government")
def gov_farm_procedures(query: str = "", language: str = "en") -> dict:
    """List the agriculture ministry's procedures (tramites) a producer can do on the channel, or explain one in detail.

    Args:
        query: Empty for the numbered menu of procedures; a procedure code ('PHY'), a menu number or plain words
            ('export coffee', 'mover ganado', 'constancia') for the detail of one procedure.
        language: 'es' or 'en' — the language of the conversation (labels come back in it).

    Returns:
        The menu (option number, code, name, who it is for, fee, review time, channel) or, for one procedure, its
        requirements and the form fields to collect (id, label, type, choices, required). Plot registration is done
        with gov_farm_register_plot; every other form is filled with gov_farm_fill_form.
    """
    ag = fixture("gov_agriculture")
    lang = _lang(language)
    procs = ag["procedures"]
    q = (query or "").strip()
    if q.isdigit() and 1 <= int(q) <= len(procs):
        q = procs[int(q) - 1]["code"]
    pr = _procedure(q) if q else None
    if q and not pr:
        return err(f"no procedure matches {query!r}", menu=[_proc_card(x, lang, i) for i, x in enumerate(procs, 1)])
    if not pr:
        return ok(agency=_loc(ag, "agency", lang), menu=[_proc_card(x, lang, i) for i, x in enumerate(procs, 1)],
                  how="Reply with the option number or the procedure's name.", as_of=_today().isoformat())
    fields = [{"id": f["id"], "label": _loc(f, "label", lang), "type": f["type"], "required": f["required"],
               **({"choices": [c["es"] if lang == "es" else c["value"] for c in f["choices"]]} if "choices" in f else {})}
              for f in pr["fields"]]
    return ok(procedure=_proc_card(pr, lang), requirements=_loc(pr, "requirements", lang), fields=fields,
              filled_by=pr.get("handled_by", "gov_farm_fill_form"),
              prefilled_from_registry="Name, national ID, municipality and plots come from the producer's registry record.")


def _num(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    t = re.sub(r"[^\d.,]", "", str(v))
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", t):          # 3,000 / 3.000 → thousands
        t = re.sub(r"[.,]", "", t)
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return None


def _parse_day(v: Any) -> dt.date | None:
    t = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    return None


def _choice(f: dict, v: Any) -> str | None:
    t = _norm(str(v))
    for c in f["choices"]:
        for name in (_norm(c["value"]), _norm(c["es"])):
            if t == name or name in t or (len(t) >= 4 and t in name):
                return c["value"]
    names = {_norm(c["value"]): c["value"] for c in f["choices"]} | {_norm(c["es"]): c["value"] for c in f["choices"]}
    m = difflib.get_close_matches(t, list(names), n=1, cutoff=0.75)
    return names[m[0]] if m else None


def _form_docx(pr: dict, lang: str, rows: list[tuple[str, str, str]], meta: dict) -> bytes:
    import io

    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    T = _FORM_TEXT[lang]
    ag = fixture("gov_agriculture")
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)
    head = doc.add_paragraph()
    r = head.add_run(_loc(ag, "agency", lang).split(" (")[0] + " · " + ("República de Valdoria" if lang == "es" else "Republic of Valdoria"))
    r.bold, r.font.size, r.font.color.rgb = True, Pt(10), RGBColor(0x40, 0x40, 0x40)
    head.add_run("\n" + _loc(ag, "registry", lang)).font.size = Pt(9)
    doc.add_heading(f"{pr['form']} · {_loc(pr, 'name', lang)}", level=1)
    warn = doc.add_paragraph().add_run(T["simulated"])
    warn.bold, warn.font.size, warn.font.color.rgb = True, Pt(9), RGBColor(0xC2, 0x41, 0x2D)
    doc.add_paragraph(f"{T['submission']}: {meta['submission']}    {T['date']}: {meta['date']}    {T['applicant']}: {meta['applicant']}")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, (T["field"], T["value"], T["source"])):
        cell.text = ""
        cell.paragraphs[0].add_run(text).bold = True
    for label, value, src in rows:
        cells = table.add_row().cells
        cells[0].text, cells[1].text, cells[2].text = label, value, T[src]
    doc.add_heading(T["requirements"], level=2)
    for x in _loc(pr, "requirements", lang):
        doc.add_paragraph(x, style="List Bullet")
    doc.add_heading(T["next"], level=2)
    for x in meta["next_steps"]:
        doc.add_paragraph(x, style="List Number")
    fee = f"{T['fee']}: " + (f"US${meta['fee_usd']:.2f}" if meta["fee_usd"] else T["free"])
    review = f"{T['review']}: " + (f"{pr['business_days']} {T['days']}" if pr["business_days"] else T["same_day"])
    doc.add_paragraph(f"{fee}    {review}")
    foot = doc.add_paragraph(T["footer"])
    foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    foot.runs[0].font.size, foot.runs[0].italic = Pt(8), True
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@hive_tool("government", kind="action")
def gov_farm_fill_form(procedure: str, producer: str, answers: str = "", language: str = "en", *,
                       tool_context: ToolContext = None) -> dict:
    """Fill in an agriculture-ministry form for a producer: pre-fill from the registry, validate, attach the filled form.

    Call it as soon as you know the procedure and the producer, then again with the producer's answers. When every
    required field is valid it attaches the filled form (.docx) to the session for download (simulated submission).

    Args:
        procedure: Procedure code from gov_farm_procedures: PRD, PRG, PHY, MOV or CER (PLT uses gov_farm_register_plot).
        producer: Producer registry number (NPR-...), national ID or full name. For PRD (new producer): the national ID.
        answers: The producer's answers as a JSON object {field_id: value}, using the field ids from
            gov_farm_procedures; dates as YYYY-MM-DD. Empty to see what the registry pre-fills and what is missing.
        language: 'es' or 'en' — the language of the conversation; the form is written in it.

    Returns:
        status 'incomplete' with the missing fields (label, type, choices) and validation errors to fix, or status
        'ready' with the submission number, the filled fields and their source (registry or producer), fee, review
        time, next steps and the attached file name.
    """
    import base64
    import json

    ag = fixture("gov_agriculture")
    lang = _lang(language)
    pr = _procedure(procedure)
    if not pr:
        return err(f"unknown procedure {procedure!r}", procedures=[x["code"] for x in ag["procedures"]])
    if pr.get("handled_by"):
        return err(f"{pr['code']} is filed with {pr['handled_by']}, not with a form", use=pr["handled_by"])
    try:   # models sometimes send the object itself instead of its JSON text
        given = answers if isinstance(answers, dict) else json.loads(answers) if answers and str(answers).strip() else {}
        if not isinstance(given, dict):
            raise ValueError
    except (ValueError, TypeError):
        return err("answers must be a JSON object such as {\"quantity_kg\": 3000, \"shipment_date\": \"2026-12-04\"}")
    given = {str(k).strip(): v for k, v in given.items() if v not in (None, "")}
    p = _producer(producer)
    if pr["code"] == "PRD":
        if p:
            return err(f"{p['name']} is already registered as {p['npr']}", npr=p["npr"],
                       next_step="Use CER for a registration certificate, or PLT/PRG for plots and programmes.")
        given.setdefault("national_id", producer.strip())
    else:
        if not p:
            return err(f"producer {producer!r} not found in the National Producer Registry",
                       next_step="Register as a producer first (procedure PRD).")
        if not p["identity_verified"]:
            return err("identity not verified with the national identity provider — forms cannot be filed yet",
                       issue=p.get("verification_issue"), fix=f"Re-verify identity or visit {ag['service_centres'].get(p['municipality'])}.")
    crops = [c for group in ag["crops"].values() for c in group]
    plots = {x["id"]: x for x in (p["plots"] if p else [])}
    values: dict[str, Any] = {}
    source: dict[str, str] = {}
    errors: list[str] = []
    for f in pr["fields"]:
        fid, raw = f["id"], given.get(f["id"])
        if raw is None:
            continue
        if f["type"] == "number":
            v = _num(raw)
            if v is None or not f["min"] <= v <= f["max"]:
                errors.append(f"{fid}: a number between {f['min']} and {f['max']} is needed (got {raw!r})")
                continue
            values[fid] = int(v) if v == int(v) else round(v, 2)
        elif f["type"] == "date":
            d = _parse_day(raw)
            if not d:
                errors.append(f"{fid}: use a date like 2026-12-04 (got {raw!r})")
                continue
            values[fid] = d
        elif f["type"] == "choice":
            v = _choice(f, raw)
            if not v:
                errors.append(f"{fid}: choose one of {[c['es'] if lang == 'es' else c['value'] for c in f['choices']]} (got {raw!r})")
                continue
            values[fid] = v
        elif f["type"] == "crop":
            v = _norm(str(raw))
            if v not in crops:
                errors.append(f"{fid}: choose one of {crops} (got {raw!r})")
                continue
            values[fid] = v
        elif f["type"] == "plot":
            v = str(raw).strip().upper()
            if v not in plots:
                errors.append(f"{fid}: {raw!r} is not one of this producer's plots {sorted(plots)}")
                continue
            values[fid] = v
        else:
            values[fid] = str(raw).strip()
        source[fid] = "farmer"
    # registry pre-fill
    if p:
        crop_field = values.get("product")
        if "plot_id" in {f["id"] for f in pr["fields"]} and "plot_id" not in values:
            match = [x for x in p["plots"] if not crop_field or x["crop"] == crop_field]
            if len(match) == 1:
                values["plot_id"], source["plot_id"] = match[0]["id"], "registry"
    if pr["code"] == "PRD" and "national_id" in values:
        source["national_id"] = "farmer"
    # procedure rules
    today = _today()
    plot = plots.get(values.get("plot_id", ""))
    if pr["code"] == "PHY" and plot:
        if "product" in values and plot["crop"] != values["product"]:
            errors.append(f"plot_id: {plot['id']} grows {plot['crop']}, not {values['product']}")
        if not plot.get("georeferenced"):
            errors.append(f"plot_id: {plot['id']} is not georeferenced yet — share a location pin first")
        cap = pr["max_kg_per_ha"].get(plot["crop"], 0) * plot["area_ha"]
        if "quantity_kg" in values and values["quantity_kg"] > cap:
            errors.append(f"quantity_kg: {values['quantity_kg']} kg exceeds what {plot['area_ha']} ha of {plot['crop']} can yield in a season ({cap:,.0f} kg)")
    if pr["code"] == "PRG" and plot and "program" in values:
        e = next(x for x in _farm_eligibility(p, p["plots"]) if x["program"] == values["program"])
        if not e["eligible"]:
            errors.append(f"program: not eligible for {values['program']} — {e['reason']}")
        if values.get("area_ha", 0) > plot["area_ha"]:
            errors.append(f"area_ha: plot {plot['id']} has {plot['area_ha']} ha")
    for fid in ("shipment_date", "movement_date"):
        if fid in values:
            need = _add_business_days(today, pr.get("min_notice_business_days", 1))
            if values[fid] < need:
                errors.append(f"{fid}: must be on or after {need.isoformat()} ({pr.get('min_notice_business_days', 1)} business days' notice)")
    missing = [{"id": f["id"], "label": _loc(f, "label", lang), "type": f["type"],
                **({"choices": [c["es"] if lang == "es" else c["value"] for c in f["choices"]]} if "choices" in f else {}),
                **({"choices": sorted(plots)} if f["type"] == "plot" else {})}
               for f in pr["fields"] if f["required"] and f["id"] not in values]
    applicant = p["name"] if p else values.get("full_name", "")
    prefilled = ({"applicant": p["name"], "npr": p["npr"], "national_id": p["national_id"], "municipality": p["municipality"]}
                 if p else {})
    if missing or errors:
        return ok(status="incomplete", procedure=_proc_card(pr, lang), prefilled_from_registry=prefilled,
                  filled={k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in values.items()},
                  missing=missing, errors=errors,
                  next="Ask for the first missing field (one question at a time) or the fix for the first error, then call again with all answers.")
    # complete: build the form
    fee = pr["fee_usd"] + pr.get("fee_usd_per_head", 0) * values.get("head_count", 0)
    sub = _sid(f"{pr['code']}-2026-", p["npr"] if p else values.get("national_id"), sorted((k, str(v)) for k, v in values.items()))
    label = {f["id"]: _loc(f, "label", lang) for f in pr["fields"]}
    show = lambda f, v: (next((c["es"] if lang == "es" else c["value"]) for c in f["choices"] if c["value"] == v)
                         if f["type"] == "choice" else v.isoformat() if isinstance(v, dt.date)
                         else f"{v:,}" if isinstance(v, (int, float)) else str(v))
    rows = []
    if p:
        rows += [(("Productor" if lang == "es" else "Producer"), f"{p['name']} · {p['npr']}", "registry"),
                 (("Documento de identidad" if lang == "es" else "National ID"), p["national_id"], "registry"),
                 (("Municipio" if lang == "es" else "Municipality"), f"{p['municipality']}, {p['province']}", "registry")]
    for f in pr["fields"]:
        if f["id"] in values:
            v = values[f["id"]]
            text = show(f, v)
            if f["type"] == "plot" and plot:
                crop = ag.get("crop_names_es", {}).get(plot["crop"], plot["crop"]) if lang == "es" else plot["crop"]
                text = f"{v} · {crop} · {plot['area_ha']} ha"
            elif f["type"] == "crop" and lang == "es":
                text = ag.get("crop_names_es", {}).get(v, v)
            rows.append((label[f["id"]], text, source[f["id"]]))
    centre = ag["service_centres"].get(p["municipality"] if p else values.get("municipality", ""), "")
    nxt = {
        "PHY": [("Un inspector visitará el lote para la inspección previa al embarque; tenga el lote separado y etiquetado."
                 if lang == "es" else "An inspector will visit for the pre-shipment inspection; keep the lot separated and labelled."),
                ("Pague la tarifa en el centro de servicios o en línea con el número de trámite."
                 if lang == "es" else "Pay the fee at the service centre or online with the submission number."),
                ("El certificado se emite tras la inspección y viaja con el embarque."
                 if lang == "es" else "The certificate is issued after the inspection and travels with the shipment.")],
        "MOV": [("Lleve la guía impresa o en el teléfono durante el traslado." if lang == "es" else "Carry the permit (printed or on the phone) during the move."),
                ("Los puestos de control verifican el fierro y el certificado de vacunación." if lang == "es" else "Checkpoints verify the brand and the vaccination certificate.")],
        "PRG": [("Recibirá la confirmación de inscripción por este canal." if lang == "es" else "You will get the enrolment confirmation on this channel."),
                ("Los beneficios se entregan en el centro de servicios agropecuarios." if lang == "es" else "Benefits are delivered at the agro-service centre.")],
        "PRD": [("Recibirá su número de productor por este canal." if lang == "es" else "You will receive your producer number on this channel."),
                ("Luego registre sus parcelas (trámite PLT)." if lang == "es" else "Then register your plots (procedure PLT).")],
        "CER": [("Presente la constancia ante la entidad indicada; tiene validez de 90 días." if lang == "es" else "Present the certificate to the named entity; it is valid for 90 days.")],
    }[pr["code"]]
    if centre:
        nxt.append(("Centro de servicios: " if lang == "es" else "Service centre: ") + centre)
    meta = {"submission": sub, "date": today.isoformat(), "applicant": applicant, "fee_usd": fee, "next_steps": nxt}
    st = getattr(tool_context, "state", None) if tool_context is not None else None
    file_name = None
    if st is not None:
        try:
            data = _form_docx(pr, lang, rows, meta)
        except Exception as e:  # noqa: BLE001 — tools must not raise
            return err(f"form render failed: {type(e).__name__}: {e}"[:300])
        plain = unicodedata.normalize("NFKD", _loc(pr, "name", lang)).encode("ascii", "ignore").decode().lower()
        file_name = f"{re.sub(r'[^a-z0-9]+', '-', plain).strip('-')}-{sub}.docx"
        st[f"hive_file:gov-{sub.lower()}"] = {"name": file_name, "mime": _DOCX_MIME, "size": len(data),
                                             "b64": base64.b64encode(data).decode()}
    return ok(status="ready", submission=sub, procedure=_proc_card(pr, lang), applicant=applicant,
              form=[{"field": a, "value": b, "source": c} for a, b, c in rows],
              fee_usd=fee, review_business_days=pr["business_days"], next_steps=nxt,
              file=file_name, delivered="attached to this session for download" if file_name else "no session to attach the file to",
              simulated=True)


# =================================================================================================================
# Business Registry (business registry agency, national)
# =================================================================================================================


def _name_key(name: str, ignored: list[str]) -> str:
    words = [w for w in _norm(name).replace("'s", "s").split() if w not in ignored]
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words)


@hive_tool("government")
def gov_registry_guide(entity_type: str, proposed_name: str = "", shareholders: int = 1, employees: int = 0,
                       home_based: bool = False) -> dict:
    """Plan a micro/small business registration step by step: fees, timeline, name check and post-registration steps.

    Covers entity rules, documents, name availability and the post-registration actions (tax ID, social security,
    municipal licence).

    Args:
        entity_type: SP (sole proprietorship), SLC (simplified limited company) or LLC; plain words are mapped.
        proposed_name: Business name to check (optional).
        shareholders: Number of owners/shareholders.
        employees: Planned employees (adds social security registration and sets the municipal licence fee).
        home_based: True if run from home (adds a Home Occupation Permit in Port Alder).

    Returns:
        Ordered steps with owner and fee, documents, total registration fees, estimated business days, name check
        (available / conflict with similar names / restricted words) with suggestions, and post-registration actions.
    """
    rg = fixture("gov_registry")
    et = entity_type.strip().upper()
    el = entity_type.lower()
    if et not in rg["entity_types"]:
        et = "SP" if ("sole" in el or "individual" in el) else "SLC" if "simplified" in el else "LLC" if ("llc" in el or "liability" in el) else et
    t = rg["entity_types"].get(et)
    if not t:
        return err(f"unknown entity type {entity_type!r}", types={k: v["name"] for k, v in rg["entity_types"].items()})
    warnings = []
    if et == "SP" and shareholders > 1:
        warnings.append("A sole proprietorship has exactly one owner - use an SLC for partners.")
    if et == "LLC" and shareholders < 2:
        warnings.append("An LLC needs at least 2 partners - an SLC allows a single shareholder.")
    name_check = None
    if proposed_name.strip():
        ign = rg["ignored_in_name_comparison"]
        key = _name_key(proposed_name, ign)
        restricted = [w for w in rg["restricted_words"] if re.search(rf"\b{w}\b", proposed_name.lower())]
        conflicts = []
        for n in rg["registered_names"]:
            k2 = _name_key(n, ign)
            ratio = difflib.SequenceMatcher(None, key, k2).ratio()
            if k2 == key or ratio >= 0.88:
                conflicts.append({"registered": n, "similarity": round(ratio, 2), "identical_after_normalising": k2 == key})
        status = "restricted word" if restricted else "not available" if conflicts else "available"
        base = proposed_name.strip()
        name_check = {"proposed": base, "comparison_key": key, "status": status, "conflicts": conflicts, "restricted_words": restricted,
                      "suggestions": [] if status == "available" else [f"{base.split()[0]} {s} {' '.join(base.split()[1:])}".strip() for s in ("Harbor", "Artisan")][:2]
                      + [f"{base} of Port Alder"],
                      "rule": "Names are compared ignoring case, punctuation, legal suffixes, 'the', '&/and' and plurals."}
    fees = [{"item": "Name reservation (valid 30 days)", "usd": rg["name_reservation"]["fee"]},
            {"item": f"{t['name']} registration", "usd": t["registration_fee"]}]
    lic = fixture("gov_licensing")
    gbl = next(x for x in lic["license_types"] if x["code"] == "GBL")
    gfee, _ = _lic_fee(gbl, employees)
    post = [{"step": "Tax ID", "owner": "Revenue Service (automatic)", "when": "1 business day after registration", "fee": 0}]
    if employees:
        post.append({"step": "Employer registration with Social Security", "owner": "applicant", "when": "within 10 days of the first hire", "fee": 0})
    post.append({"step": "Port Alder General Business Licence", "owner": "applicant", "when": "before opening", "fee": gfee})
    if home_based:
        post.append({"step": "Port Alder Home Occupation Permit", "owner": "applicant", "when": "before opening", "fee": 85})
    days = 1 + t["agency_review_business_days"] + 1
    return ok(entity_type=et, entity=t, steps=rg["steps"], documents=t["documents"], registration_fees=fees,
              registration_total=sum(f["usd"] for f in fees), estimated_business_days=days,
              estimated_registration_date=_add_business_days(_today(), days).isoformat(), name_check=name_check,
              post_registration=post, warnings=warnings)


@hive_tool("government")
def gov_registry_tracker(application_id: str) -> dict:
    """Track a business registration application's pending actions, owners, due dates, blockers and next best action.

    Action Tracker pattern: completed steps, pending actions with owner and due date, deadline risks.

    Args:
        application_id: Application number, e.g. 'BRA-2026-55120'.

    Returns:
        Status, completed actions, pending actions with days left (negative = overdue) and blocking flag, risks such as
        name-reservation expiry, reminders already sent and the next best action per owner.
    """
    rg = fixture("gov_registry")
    app = next((a for a in rg["applications"] if a["id"] == application_id.strip().upper()), None)
    if not app:
        return err(f"no application {application_id!r}", known=[a["id"] for a in rg["applications"]])
    done, pending, risks = [], [], []
    for a in app["actions"]:
        row = dict(a)
        if a.get("due"):
            row["days_left"] = (_date(a["due"]) - _today()).days
        if a["status"] == "done":
            done.append(row)
        else:
            pending.append(row)
        if a.get("expires"):
            left = (_date(a["expires"]) - _today()).days
            risks.append({"risk": f"Name reservation expires {a['expires']} ({left} days)",
                          "consequence": "If it lapses the name is released: re-reserve for $10 (the name may be taken) and blocking actions restart.",
                          "days_left": left})
    blockers = [p for p in pending if p.get("blocking")]
    nxt = (blockers or [p for p in pending if p["status"] in ("pending", "in_progress", "not_started")] or [None])[0]
    by_owner: dict[str, list[str]] = {}
    for p in pending:
        if p["status"] in ("pending", "in_progress", "not_started", "optional"):
            by_owner.setdefault(p["owner"], []).append(p["task"])
    return ok(application={k: v for k, v in app.items() if k != "actions"}, completed=done, pending=pending,
              blockers=blockers, risks=risks, next_best_action=nxt, actions_by_owner=by_owner,
              reminders_sent=app.get("reminders_sent", []), as_of=_today().isoformat())


# =================================================================================================================
# Housing & Credit Advisor (public and partner lenders)
# =================================================================================================================


def _payment(principal: float, rate_pct: float, years: int) -> float:
    r, n = rate_pct / 100 / 12, years * 12
    return principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)


@hive_tool("government")
def gov_housing_compare(monthly_income: float, home_price: float = 0, down_payment: float = 0, monthly_debts: float = 0,
                        loan_amount: float = 0, product_type: str = "mortgage", first_time_buyer: bool = True,
                        energy_certified_home: bool = False) -> dict:
    """Compare public and partner-lender housing and credit products against a household's needs and affordability.

    Works like a requirements matrix: each product is checked against the household's requirements, with
    affordability ratios, monthly payments and total cost.

    Args:
        monthly_income: Gross household income per month.
        home_price: Purchase price (mortgages). Leave 0 with loan_amount 0 for an affordability-only answer.
        down_payment: Cash available for the down payment.
        monthly_debts: Existing monthly debt payments (car, cards, other loans).
        loan_amount: Amount to borrow (home improvement / personal loans).
        product_type: 'mortgage', 'home_improvement', 'personal' or a comma list like 'home_improvement,personal'.
        first_time_buyer: True if no household member has owned a home.
        energy_certified_home: True if the home has an energy-efficiency certificate (Green Home Loan).

    Returns:
        Per product: eligible yes/no with failed requirements, loan amount, rate, monthly payment (and housing
        payment with tax and insurance), housing and debt-to-income ratios, upfront cash needed, total interest and
        total cost; ranked eligible products; and the maximum affordable price per mortgage product.
    """
    hs = fixture("gov_housing")
    rules = hs["rules"]
    if monthly_income <= 0:
        return err("monthly_income must be > 0")
    types = [t.strip().lower() for t in product_type.split(",") if t.strip()]
    prods = [p for p in hs["products"] if p["type"] in types]
    if not prods:
        return err(f"no products of type {product_type!r}", types=sorted({p["type"] for p in hs["products"]}))
    tax_m = lambda price: price * rules["property_tax_pct_per_year"] / 100 / 12  # noqa: E731
    rows, afford = [], []
    subsidy = rules["first_home_subsidy"]
    for p in prods:
        fails = []
        if p["type"] == "mortgage":
            sub = subsidy["amount"] if (p["id"] in subsidy["applies_to"] and first_time_buyer and monthly_income <= subsidy["max_household_income"]) else 0
            if home_price > 0:
                down = down_payment + sub
                loan = max(0.0, home_price - down)
                if down < home_price * p["min_down_pct"] / 100:
                    fails.append(f"down payment {down / home_price:.1%} < {p['min_down_pct']}%")
            else:
                loan = 0.0
        else:
            sub, loan = 0, loan_amount
            if loan <= 0:
                return err("loan_amount is required for home_improvement / personal loans")
        if p.get("first_time_buyer_only") and not first_time_buyer:
            fails.append("first-time buyers only")
        if p.get("max_household_income") and monthly_income > p["max_household_income"]:
            fails.append(f"household income above ${p['max_household_income']:,}/month")
        if p["id"] == "VDB-GREEN25" and not energy_certified_home:
            fails.append("home must have an energy-efficiency certificate")
        if p["type"] == "mortgage":
            rate_test = p.get("stress_rate_pct", p["rate_pct"])
            f = _payment(1, rate_test, p["term_years"])
            cap = min(p["max_housing_ratio_pct"] / 100 * monthly_income, p["max_dti_pct"] / 100 * monthly_income - monthly_debts)
            maxp = (cap - rules["home_insurance_per_month"] + f * (down_payment + sub)) / (f + rules["property_tax_pct_per_year"] / 100 / 12)
            maxp = min(maxp, p["max_loan"] + down_payment + sub)
            if not (p.get("first_time_buyer_only") and not first_time_buyer) and not (p.get("max_household_income") and monthly_income > p["max_household_income"]):
                afford.append({"product": p["id"], "lender": p["lender"], "max_price": round(max(0, maxp), -2),
                               "tested_rate_pct": rate_test, "subsidy_included": sub})
            if home_price <= 0:
                continue
        if loan > p["max_loan"]:
            fails.append(f"loan ${loan:,.0f} above maximum ${p['max_loan']:,}")
        pay = _payment(loan, p["rate_pct"], p["term_years"])
        test_pay = _payment(loan, p.get("stress_rate_pct", p["rate_pct"]), p["term_years"])
        row = {"product": p["id"], "lender": p["lender"], "name": p["name"], "public": p["public"], "rate_pct": p["rate_pct"],
               "rate_type": p["rate_type"], "term_years": p["term_years"], "loan": round(loan, 2), "monthly_payment": round(pay, 2)}
        if p["type"] == "mortgage":
            housing = test_pay + tax_m(home_price) + rules["home_insurance_per_month"]
            hr = housing / monthly_income * 100
            dti = (housing + monthly_debts) / monthly_income * 100
            if hr > p["max_housing_ratio_pct"]:
                fails.append(f"housing ratio {hr:.1f}% > {p['max_housing_ratio_pct']}%")
            if dti > p["max_dti_pct"]:
                fails.append(f"debt-to-income {dti:.1f}% > {p['max_dti_pct']}%")
            closing = home_price * rules["closing_costs_pct"] / 100
            row.update(housing_payment=round(pay + tax_m(home_price) + rules["home_insurance_per_month"], 2),
                       housing_ratio_pct=round(hr, 1), dti_pct=round(dti, 1), subsidy=sub,
                       upfront_cash=round(down_payment + closing + loan * p["origination_fee_pct"] / 100, 2))
            if "stress_rate_pct" in p:
                row["stress_tested_at_pct"] = p["stress_rate_pct"]
        else:
            dti = (pay + monthly_debts) / monthly_income * 100
            if dti > p["max_dti_pct"]:
                fails.append(f"debt-to-income {dti:.1f}% > {p['max_dti_pct']}%")
            row.update(dti_pct=round(dti, 1), upfront_fee=round(loan * p["origination_fee_pct"] / 100, 2))
        interest = pay * p["term_years"] * 12 - loan
        row.update(total_interest=round(interest, 2), total_cost=round(interest + loan * p["origination_fee_pct"] / 100, 2),
                   requirements_failed=fails, eligible=not fails, conditions=p.get("requires", ""), notes=p.get("notes", ""))
        rows.append(row)
    ranked = sorted([r for r in rows if r["eligible"]], key=lambda r: (r["monthly_payment"], r["total_cost"]))
    return ok(inputs={"monthly_income": monthly_income, "home_price": home_price, "down_payment": down_payment,
                      "monthly_debts": monthly_debts, "loan_amount": loan_amount, "first_time_buyer": first_time_buyer},
              products=rows, ranked_eligible=[f"{i}. {r['product']} ({r['lender']}) ${r['monthly_payment']:,.2f}/month"
                                              for i, r in enumerate(ranked, 1)],
              affordability=sorted(afford, key=lambda a: -a["max_price"]),
              assumptions={"property_tax": f"{rules['property_tax_pct_per_year']}% of price a year",
                           "home_insurance": f"${rules['home_insurance_per_month']}/month",
                           "closing_costs": f"{rules['closing_costs_pct']}% of price", "first_home_subsidy": subsidy},
              disclaimer="Indicative comparison - lenders confirm rates and approval after a full application.")

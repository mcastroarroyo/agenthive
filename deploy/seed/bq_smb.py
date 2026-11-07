"""Synthetic BigQuery rows for the SMB realm — Kitewing Software (fictional B2B field-service SaaS).

    tables() -> {"smb_customers": [...], "smb_products": [...], "smb_orders": [...], "smb_pipeline": [...],
                 "smb_support_tickets": [...], "smb_invoices": [...], "smb_product_usage": [...]}

Deterministic (random.Random(SEED)). The six named customers and eight open opportunities in
agenthive/tools/fixtures/smb_crm.json are included with the same ids and figures, so the BigQuery Data agent and the
Account Indexer tell the same story. Every company and person is fictional.
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

SEED = 20261106
TODAY = dt.date(2026, 11, 6)
FIX = Path(__file__).resolve().parents[2] / "agenthive" / "tools" / "fixtures"

PRODUCTS = [
    ("PRD-STARTER", "Starter plan", "plan", 39.0, "per_technician_month", "2021-03-01"),
    ("PRD-GROWTH", "Growth plan", "plan", 69.0, "per_technician_month", "2021-03-01"),
    ("PRD-ENTERPRISE", "Enterprise plan", "plan", 99.0, "per_technician_month", "2022-06-01"),
    ("PRD-ROUTE", "Route Optimizer", "add_on", 15.0, "per_technician_month", "2022-02-01"),
    ("PRD-ASSIST", "Kitewing Assist (AI copilot)", "add_on", 20.0, "per_technician_month", "2025-09-15"),
    ("PRD-INSIGHTS", "Insights (BigQuery analytics)", "add_on", 600.0, "flat_month", "2023-05-01"),
    ("PRD-IMPL-QS", "QuickStart implementation", "service", 4500.0, "one_time", "2021-03-01"),
    ("PRD-IMPL-STD", "Standard implementation", "service", 12000.0, "one_time", "2021-03-01"),
    ("PRD-IMPL-PREM", "Premium implementation", "service", 28000.0, "one_time", "2022-06-01"),
    ("PRD-MIGR", "Data migration (per legacy source)", "service", 3500.0, "one_time", "2021-03-01"),
    ("PRD-TRAIN", "Onsite training day", "service", 1800.0, "one_time", "2021-03-01"),
]
PLAN_PRD = {"Starter": "PRD-STARTER", "Growth": "PRD-GROWTH", "Enterprise": "PRD-ENTERPRISE"}
ADDON_PRD = {"Route Optimizer": "PRD-ROUTE", "Assist": "PRD-ASSIST", "Insights": "PRD-INSIGHTS"}
PRICE = {p[0]: p[3] for p in PRODUCTS}
ASSIST_LAUNCH = dt.date(2025, 9, 15)

INDUSTRIES = {
    "hvac_plumbing": ("HVAC & plumbing", ["Heating & Cooling", "Plumbing", "Home Services", "Mechanical", "Comfort Systems", "Electric"], 0.42),
    "facilities": ("Facilities management", ["Facilities", "Property Services", "Building Care"], 0.18),
    "fire_security": ("Fire & security", ["Fire Protection", "Security Systems", "Alarm & Access"], 0.16),
    "elevator": ("Elevator maintenance", ["Elevator", "Lift Services"], 0.08),
    "pest_landscaping": ("Pest control & landscaping", ["Pest Control", "Landscaping", "Lawn Care", "Pool Care"], 0.16),
}
FIXTURE_INDUSTRY = {"hvac_plumbing": "HVAC & plumbing", "facilities": "Facilities management",
                    "fire_security": "Fire & security", "elevator": "Elevator maintenance",
                    "pest_landscaping": "Pest control & landscaping"}
PREFIXES = ["Ambermoor", "Ashgrove", "Birchwick", "Brightwater", "Calderbrook", "Cobblestone", "Copperwood",
            "Deerholt", "Elmsworth", "Fairhollow", "Fenwick Vale", "Foxbriar", "Glenhaven", "Granitefall",
            "Hartwell", "Hollowmere", "Ironleaf", "Juniper Ridge", "Kestrel Bay", "Larkmoor", "Lindenshaw",
            "Maplewyck", "Mossbank", "Netherfold", "Northwold", "Oakhurst", "Orchard Gate", "Pebblebrook",
            "Pinehollow", "Quillstone", "Ravensbrook", "Redfern", "Rosewyn", "Saltmarsh", "Silverbirch",
            "Stonewick", "Sunderly", "Tamarind", "Thistledown", "Umberfield", "Valebrook", "Westerhaze",
            "Willowmere", "Wrenhaven", "Yarrowby", "Zephyr Hill"]
SUFFIXES = ["Co.", "Inc.", "Group", "Services", "LLC", "Partners", ""]
CITIES = ["Cedar Harbor", "Millbrook", "Rivergate", "Westmere", "Brookhaven Falls", "Port Alder", "Lindenfield",
          "Stonehaven", "Marlow Bay", "Ashby Cross", "Fernvale", "Kestrel Point", "Halden", "Northwick", "Glenmoor"]
REGIONS = ["North", "South", "East", "West", "Central"]
AES = ["Jamie Cho", "Priya Natarajan", "Ethan Caldwell"]
CSMS = ["Kwame Mensah", "Ruth Adebayo", "Paul Ngata", "Hannah Brooks"]
AGENTS = ["Liam O'Connor", "Ava Lindholm", "Jonah Petit", "Zara Quinn", "Kofi Asante"]
CHANNELS = ["Inbound", "Webinar", "Referral", "Outbound", "Partner", "Trade show"]
SEG_BENCH = {"hvac_plumbing": (3.4, 76, 33), "facilities": (3.0, 74, 30), "fire_security": (2.6, 80, 39),
             "elevator": (2.2, 84, 38), "pest_landscaping": (7.5, 92, 17)}   # jobs/tech/day, FTF %, drive min/job
FIXED_HEALTH = {"C-1001": 36, "C-1002": 88, "C-1003": 100, "C-1004": 95, "C-1005": 100, "C-1006": 98}


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _band(techs: int) -> str:
    return "SMB" if techs < 35 else "Mid-market" if techs < 150 else "Enterprise"


def _vol(techs: int) -> float:
    return 10.0 if techs >= 200 else 5.0 if techs >= 100 else 0.0


def _anniv(d: dt.date, years: int) -> dt.date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def _arr(plan: str, addons: list[str], licensed: int) -> float:
    per = PRICE[PLAN_PRD[plan]] + sum(PRICE[ADDON_PRD[a]] for a in addons if a != "Insights")
    flat = 600.0 * 12 if "Insights" in addons and plan != "Enterprise" else 0.0
    return round(per * licensed * 12 * (1 - _vol(licensed) / 100) + flat, 2)


def _customers(rng: random.Random) -> list[dict]:
    crm = json.loads((FIX / "smb_crm.json").read_text())["accounts"]
    out = []
    for a in crm:
        if a["type"] != "customer":
            continue
        out.append({"customer_id": a["id"], "company_name": a["name"], "industry": FIXTURE_INDUSTRY[a["segment"]],
                    "size_band": _band(a["technicians"]), "region": "North" if a["hq"] in ("Cedar Harbor", "Millbrook") else "East",
                    "city": a["hq"], "technicians": a["technicians"], "licensed_technicians": a["licensed_technicians"],
                    "plan": a["plan"], "addons": ", ".join(a["addons"]), "signup_date": a["customer_since"],
                    "renewal_date": a["renewal_date"], "arr_usd": float(a["arr_usd"]),
                    "health_score": FIXED_HEALTH[a["id"]], "csm_owner": a["csm"], "account_owner": a["account_owner"],
                    "acquisition_channel": "Referral" if a["id"] in ("C-1002", "C-1004") else "Inbound",
                    "is_active": True, "churn_date": None, "_segment": a["segment"]})
    names = {c["company_name"] for c in out}
    segs = list(INDUSTRIES)
    weights = [INDUSTRIES[s][2] for s in segs]
    start, span = dt.date(2022, 1, 10), (dt.date(2026, 9, 30) - dt.date(2022, 1, 10)).days
    for i in range(174):
        seg = rng.choices(segs, weights)[0]
        label, words, _ = INDUSTRIES[seg]
        while True:
            name = f"{rng.choice(PREFIXES)} {rng.choice(words)} {rng.choice(SUFFIXES)}".strip()
            if name not in names:
                names.add(name)
                break
        r = rng.random()
        techs = rng.randint(6, 30) if r < 0.4 else rng.randint(31, 120) if r < 0.87 else rng.randint(121, 320)
        if techs <= 25:
            plan = "Starter" if rng.random() < 0.8 else "Growth"
        elif techs < 50:
            plan = "Growth"
        elif techs < 150:
            plan = "Enterprise" if rng.random() < 0.15 else "Growth"
        else:
            plan = "Enterprise" if rng.random() < 0.7 else "Growth"
        if plan == "Growth" and techs < 10:
            techs = 10
        signup = start + dt.timedelta(days=int(span * (rng.random() ** 0.8)))
        licensed = max(5 if plan == "Starter" else 10, techs - rng.randint(0, max(1, techs // 8)))
        if plan == "Enterprise":
            licensed = max(50, licensed)
            techs = max(techs, licensed)
        addons = []
        if plan != "Starter":
            if rng.random() < (0.6 if plan == "Enterprise" else 0.45):
                addons.append("Route Optimizer")
            if rng.random() < (0.35 if plan == "Enterprise" else 0.22):
                addons.append("Assist")
            if plan == "Growth" and rng.random() < 0.2:
                addons.append("Insights")
        churned = signup < dt.date(2025, 6, 1) and rng.random() < 0.1
        years = 1
        while _anniv(signup, years) <= TODAY:
            years += 1
        if churned:
            churn_years = rng.randint(1, max(1, years - 1))
            churn = _anniv(signup, churn_years)
            renewal = churn
        else:
            churn, renewal = None, _anniv(signup, years)
        out.append({"customer_id": f"C-{1007 + i}", "company_name": name, "industry": label,
                    "size_band": _band(techs), "region": rng.choice(REGIONS), "city": rng.choice(CITIES),
                    "technicians": techs, "licensed_technicians": licensed, "plan": plan, "addons": ", ".join(addons),
                    "signup_date": signup.isoformat(), "renewal_date": renewal.isoformat(),
                    "arr_usd": 0.0 if churned else _arr(plan, addons, licensed), "health_score": 0,
                    "csm_owner": "Hannah Brooks" if techs >= 150 else rng.choice(CSMS[:3]),
                    "account_owner": "Jamie Cho" if techs >= 100 else rng.choice(AES),
                    "acquisition_channel": rng.choice(CHANNELS), "is_active": not churned,
                    "churn_date": churn.isoformat() if churn else None, "_segment": seg})
    return out


def _orders(rng: random.Random, customers: list[dict]) -> list[dict]:
    rows, n = [], 0

    def line(oid, c, d, prd, otype, qty, disc, term):
        unit = PRICE[prd]
        months = term if term else 1
        amount = round(qty * unit * months * (1 - disc / 100), 2) if term else round(unit * qty * (1 - disc / 100), 2)
        rows.append({"order_id": oid, "customer_id": c["customer_id"], "order_date": d.isoformat(), "product_id": prd,
                     "order_type": otype, "quantity": qty, "unit_price_usd": unit, "discount_pct": disc,
                     "term_months": term, "amount_usd": amount, "sales_rep": c["account_owner"],
                     "channel": "Partner" if c["acquisition_channel"] == "Partner" else "Direct"})

    for c in customers:
        signup = _d(c["signup_date"])
        end = _d(c["churn_date"]) if c["churn_date"] else TODAY
        final = c["licensed_technicians"]
        addons = [a for a in c["addons"].split(", ") if a]
        years = []
        y = 0
        while _anniv(signup, y) <= TODAY and (not c["churn_date"] or _anniv(signup, y) < end):
            years.append(_anniv(signup, y))
            y += 1
        k = len(years)
        start_seats = max(5, round(final * rng.uniform(0.7, 0.95))) if k > 1 else final
        if c["plan"] == "Enterprise":
            start_seats = max(50, start_seats)
        # add-ons owned at signup vs added later (Assist only after launch)
        addon_start = {}
        for a in addons:
            if a == "Assist":
                addon_start[a] = max(ASSIST_LAUNCH, signup) + dt.timedelta(days=rng.randint(0, 200))
            else:
                addon_start[a] = signup if rng.random() < 0.6 else signup + dt.timedelta(days=rng.randint(60, 500))
            addon_start[a] = min(addon_start[a], TODAY - dt.timedelta(days=5))
        disc_extra = rng.choice([0, 0, 0, 5, 10, 15])
        for idx, d in enumerate(years):
            seats = round(start_seats + (final - start_seats) * (idx / max(1, k - 1)))
            disc = _vol(seats) + (disc_extra if idx == 0 else 0)
            n += 1
            oid = f"ORD-{20000 + n}"
            otype = "new" if idx == 0 else "renewal"
            line(oid, c, d, PLAN_PRD[c["plan"]], otype, seats, disc, 12)
            for a, a_d in addon_start.items():
                if a_d <= d:
                    qty = 1 if a == "Insights" else seats
                    if not (a == "Insights" and c["plan"] == "Enterprise"):
                        line(oid, c, d, ADDON_PRD[a], otype, qty, _vol(seats) if a != "Insights" else 0, 12)
            if idx == 0:
                impl = "PRD-IMPL-PREM" if c["plan"] == "Enterprise" or seats > 150 else \
                    "PRD-IMPL-STD" if seats > 25 or c["plan"] == "Growth" else "PRD-IMPL-QS"
                line(oid, c, d, impl, "new", 1, rng.choice([0, 0, 0, 10, 25]), 0)
                if rng.random() < 0.4:
                    line(oid, c, d, "PRD-MIGR", "new", rng.randint(1, 2), 0, 0)
        for a, a_d in addon_start.items():
            prev = [d for d in years if d < a_d]
            if prev and not (a == "Insights" and c["plan"] == "Enterprise") and a_d < end:
                n += 1
                qty = 1 if a == "Insights" else final
                line(f"ORD-{20000 + n}", c, a_d, ADDON_PRD[a], "expansion", qty, 0, 12)
        if k > 1 and rng.random() < 0.25:
            d = years[-1] + dt.timedelta(days=rng.randint(40, 300))
            if d < end:
                n += 1
                line(f"ORD-{20000 + n}", c, d, PLAN_PRD[c["plan"]], "expansion", rng.randint(2, 12), 0, 12)
        if rng.random() < 0.08:
            d = signup + dt.timedelta(days=rng.randint(20, 400))
            if d < end:
                n += 1
                line(f"ORD-{20000 + n}", c, d, "PRD-TRAIN", "expansion", rng.randint(1, 3), 0, 0)
    return rows


def _pipeline(rng: random.Random, customers: list[dict]) -> list[dict]:
    crm = json.loads((FIX / "smb_crm.json").read_text())["accounts"]
    prob = {"Prospecting": 5, "Discovery": 10, "Solution Validation": 30, "Proposal": 50, "Negotiation": 75,
            "Closed Won": 100, "Closed Lost": 0}
    rows = []
    for a in crm:
        for o in a.get("opportunities", []):
            rows.append({"opportunity_id": o["id"], "account_name": a["name"],
                         "customer_id": a["id"] if a["type"] == "customer" else None,
                         "opportunity_type": o["type"], "stage": o["stage"], "amount_usd": float(o["amount_usd"]),
                         "probability_pct": prob[o["stage"]],
                         "created_date": (TODAY - dt.timedelta(days=rng.randint(20, 70))).isoformat(),
                         "expected_close_date": o["close_date"], "closed_date": None, "is_closed": False,
                         "is_won": False, "owner": o["owner"],
                         "lead_source": "Customer base" if a["type"] == "customer" else
                         ("Webinar" if "Webinar" in a.get("lead_source", "") else "Referral" if "referral" in
                          a.get("lead_source", "").lower() else "Outbound" if "Outbound" in a.get("lead_source", "")
                          else "Trade show"),
                         "size_band": _band(a["technicians"]), "industry": FIXTURE_INDUSTRY[a["segment"]],
                         "competitor": "Fieldnest" if any("Fieldnest" in c for c in a.get("competitors", [])) else
                         "ServiceGrid Pro" if any("ServiceGrid" in c for c in a.get("competitors", [])) else "None",
                         "loss_reason": None})
    win = {"Referral": 0.45, "Webinar": 0.30, "Inbound": 0.28, "Outbound": 0.15, "Trade show": 0.20, "Partner": 0.35}
    segs = list(INDUSTRIES)
    active = [c for c in customers if c["is_active"]]
    start = dt.date(2025, 1, 1)
    span = (TODAY - dt.timedelta(days=1) - start).days
    for i in range(592):
        created = start + dt.timedelta(days=rng.randint(0, span))
        kind = rng.choices(["new_logo", "expansion", "renewal"], [0.62, 0.23, 0.15])[0]
        if kind == "new_logo":
            seg = rng.choices(segs, [INDUSTRIES[s][2] for s in segs])[0]
            name = f"{rng.choice(PREFIXES)} {rng.choice(INDUSTRIES[seg][1])} {rng.choice(SUFFIXES)}".strip()
            techs = rng.randint(8, 30) if rng.random() < 0.45 else rng.randint(31, 140) if rng.random() < 0.85 else rng.randint(141, 300)
            per = 39 if techs <= 25 else rng.choice([69, 84, 89, 104]) if techs < 150 else rng.choice([99, 114, 134])
            amount = round(techs * per * 12 * rng.uniform(0.85, 1.0), -2)
            source = rng.choices(list(win), [0.22, 0.14, 0.12, 0.30, 0.10, 0.12])[0]
            cust, industry = None, INDUSTRIES[seg][0]
            competitor = rng.choices(["Fieldnest", "ServiceGrid Pro", "DispatchPro 7", "None"], [0.35, 0.1, 0.2, 0.35])[0]
            p_win = win[source]
        else:
            c = rng.choice(active)
            name, techs, cust, industry = c["company_name"], c["technicians"], c["customer_id"], c["industry"]
            amount = round((c["arr_usd"] or 20000) * (rng.uniform(0.08, 0.35) if kind == "expansion" else 1.0), -1)
            source, competitor = "Customer base", "None"
            p_win = 0.6 if kind == "expansion" else 0.88
        cycle = rng.randint(25, 70) if techs < 35 else rng.randint(45, 110) if techs < 150 else rng.randint(75, 160)
        exp_close = created + dt.timedelta(days=cycle)
        closed_d = created + dt.timedelta(days=int(cycle * rng.uniform(0.8, 1.4)))
        if closed_d < TODAY:
            won = rng.random() < p_win
            stage = "Closed Won" if won else "Closed Lost"
            loss = None if won else rng.choices(["Price", "No decision", "Chose Fieldnest", "Chose ServiceGrid Pro",
                                                 "Timing", "Missing feature"], [0.22, 0.3, 0.2, 0.06, 0.12, 0.1])[0]
            if loss == "Chose Fieldnest":
                competitor = "Fieldnest"
            elif loss == "Chose ServiceGrid Pro":
                competitor = "ServiceGrid Pro"
            closed, is_closed = closed_d.isoformat(), True
        else:
            frac = (TODAY - created).days / max(1, cycle)
            stage = "Prospecting" if frac < 0.15 else "Discovery" if frac < 0.4 else "Solution Validation" if frac < 0.65 \
                else "Proposal" if frac < 0.85 else "Negotiation"
            won, loss, closed, is_closed = False, None, None, False
            if exp_close < TODAY:
                exp_close = TODAY + dt.timedelta(days=rng.randint(7, 45))
        rows.append({"opportunity_id": f"OPP-{2000 + i}", "account_name": name, "customer_id": cust,
                     "opportunity_type": kind, "stage": stage, "amount_usd": float(amount),
                     "probability_pct": prob[stage], "created_date": created.isoformat(),
                     "expected_close_date": exp_close.isoformat(), "closed_date": closed, "is_closed": is_closed,
                     "is_won": bool(won), "owner": "Jamie Cho" if techs >= 100 else rng.choice(AES),
                     "lead_source": source, "size_band": _band(techs), "industry": industry,
                     "competitor": competitor, "loss_reason": loss})
    return rows


SLA = {"P1": 30, "P2": 120, "P3": 480, "P4": 1440}
CATS = ["Mobile app", "Scheduling", "Billing", "Integrations", "Reporting", "Training", "Single sign-on",
        "Permissions", "Feature request", "Route Optimizer", "Assist"]


def _tickets(rng: random.Random, customers: list[dict]) -> list[dict]:
    act = json.loads((FIX / "smb_account_activity.json").read_text())["accounts"]
    rows, n = [], 0
    start = dt.date(2025, 1, 1)

    def ts(d: dt.date, minutes: int) -> str:
        return (dt.datetime.combine(d, dt.time(0, 0)) + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")

    for c in customers:
        fixed = act.get(c["customer_id"])
        first = max(start, _d(c["signup_date"]))
        last = _d(c["churn_date"]) if c["churn_date"] else TODAY
        if fixed:
            last = dt.date(2026, 8, 1)          # fixture tickets cover Aug-Nov 2026 for named customers
            for t in fixed["tickets"]:
                opened = _d(t["opened"])
                o_min = rng.randint(7 * 60, 17 * 60)
                fr = {"P1": 18, "P2": 75, "P3": 240, "P4": 600}[t["priority"]]
                resolved = t["status"] == "resolved"
                res_h = round(rng.uniform(2, 60), 1) if resolved else None
                rows.append({"ticket_id": t["id"], "customer_id": c["customer_id"], "opened_at": ts(opened, o_min),
                             "resolved_at": ts(opened, o_min + int(res_h * 60)) if resolved else None,
                             "priority": t["priority"], "category": t["category"], "channel": "email",
                             "status": "resolved" if resolved else "open", "first_response_minutes": fr,
                             "resolution_hours": res_h, "sla_breached": fr > SLA[t["priority"]],
                             "csat": t.get("csat"), "assignee": rng.choice(AGENTS)})
        if last <= first:
            continue
        months = max(1, (last - first).days / 30.4)
        expected = (0.2 + c["licensed_technicians"] / 110) * months
        if c["customer_id"] == "C-1001":
            expected *= 1.6
        count = max(0, int(rng.gauss(expected, expected ** 0.5)))
        for _ in range(count):
            n += 1
            opened = first + dt.timedelta(days=rng.randint(0, max(0, (last - first).days - 1)))
            pr = rng.choices(["P1", "P2", "P3", "P4"], [0.03, 0.12, 0.55, 0.30])[0]
            cat = rng.choice(CATS)
            if cat == "Assist" and opened < ASSIST_LAUNCH:
                cat = "Feature request"
            fr = int(rng.lognormvariate({"P1": 2.9, "P2": 4.0, "P3": 5.3, "P4": 6.3}[pr], 0.6))
            o_min = rng.randint(6 * 60, 19 * 60)
            age = (TODAY - opened).days
            status = "resolved" if age > 14 or rng.random() < 0.6 else rng.choice(["open", "pending"])
            res_h = round(rng.lognormvariate({"P1": 1.5, "P2": 2.6, "P3": 3.4, "P4": 4.0}[pr], 0.7), 1) \
                if status == "resolved" else None
            breached = fr > SLA[pr]
            csat = None
            if status == "resolved" and rng.random() < 0.55:
                base = 4.6 - (1.2 if breached else 0) - (0.5 if pr in ("P1", "P2") else 0)
                csat = max(1, min(5, round(rng.gauss(base, 0.8))))
            rows.append({"ticket_id": f"TCK-{60000 + n}", "customer_id": c["customer_id"], "opened_at": ts(opened, o_min),
                         "resolved_at": ts(opened, o_min + int(res_h * 60)) if res_h else None, "priority": pr,
                         "category": cat, "channel": rng.choice(["email", "chat", "phone", "portal"]),
                         "status": status, "first_response_minutes": fr, "resolution_hours": res_h,
                         "sla_breached": breached, "csat": csat, "assignee": rng.choice(AGENTS)})
    return rows


def _invoices(rng: random.Random, customers: list[dict], orders: list[dict]) -> list[dict]:
    act = json.loads((FIX / "smb_account_activity.json").read_text())["accounts"]
    groups: dict[tuple[str, str], float] = {}
    for o in orders:
        groups[(o["customer_id"], o["order_date"])] = groups.get((o["customer_id"], o["order_date"]), 0) + o["amount_usd"]
    rows, n = [], 0
    for (cid, d), amount in sorted(groups.items()):
        inv_d = _d(d)
        if cid in act and inv_d >= dt.date(2026, 1, 1):
            continue                                # fixture invoices cover 2026 for named customers
        n += 1
        due = inv_d + dt.timedelta(days=30)
        if due > TODAY:
            status, paid, dtp = "open", None, None
        elif rng.random() < 0.04:
            status, paid, dtp = "overdue", None, None
        else:
            dtp = max(1, min(95, int(rng.gauss(26, 11))))
            paid_d = inv_d + dt.timedelta(days=dtp)
            if paid_d > TODAY:
                status, paid, dtp = "overdue" if due < TODAY else "open", None, None
            else:
                status, paid = "paid", paid_d.isoformat()
        rows.append({"invoice_id": f"INV-{10000 + n}", "customer_id": cid, "invoice_date": d,
                     "due_date": due.isoformat(), "amount_usd": round(amount, 2), "status": status,
                     "paid_date": paid, "days_to_pay": dtp})
    for cid, a in act.items():
        for inv in a["invoices"]:
            idate, due = _d(inv["date"]), _d(inv["due"])
            status = "paid" if inv["status"] == "paid" else "overdue" if due < TODAY else "open"
            rows.append({"invoice_id": inv["id"], "customer_id": cid, "invoice_date": inv["date"],
                         "due_date": inv["due"], "amount_usd": float(inv["amount_usd"]), "status": status,
                         "paid_date": inv["paid"], "days_to_pay": (_d(inv["paid"]) - idate).days if inv["paid"] else None})
    return rows


def _usage(rng: random.Random, customers: list[dict]) -> list[dict]:
    act = json.loads((FIX / "smb_account_activity.json").read_text())["accounts"]
    months = [dt.date(2025 + (10 + i) // 12, (10 + i) % 12 + 1, 1) for i in range(12)]   # 2025-11 .. 2026-10
    rows = []
    for c in customers:
        if not c["is_active"]:
            continue
        signup = _d(c["signup_date"])
        jobs_day, ftf0, drive0 = SEG_BENCH[c["_segment"]]
        fixed = {u["month"]: u for u in act.get(c["customer_id"], {}).get("usage", [])}
        ratio = min(0.99, max(0.55, rng.gauss(0.9, 0.07)))
        trend = rng.gauss(0, 0.012)
        has_assist = "Assist" in c["addons"]
        for i, m in enumerate(months):
            if m < signup.replace(day=1):
                continue
            tenure = (m - signup).days / 365
            lic = c["licensed_technicians"]
            key = m.strftime("%Y-%m")
            if key in fixed:
                u = fixed[key]
                lic, active, jobs, ftf = u["licensed"], u["active"], u["jobs_completed"], u["first_time_fix_pct"]
            else:
                if c["customer_id"] in act:
                    first_fixed = act[c["customer_id"]]["usage"][0]
                    lic = first_fixed["licensed"]
                    active = min(lic, first_fixed["active"] + rng.randint(0, 2))
                    ftf = first_fixed["first_time_fix_pct"] + rng.uniform(-0.6, 0.4)
                else:
                    r = min(1.0, max(0.4, ratio + trend * (i - 11)))
                    active = max(1, min(lic, round(lic * r)))
                    ftf = min(96.0, ftf0 + min(10.0, tenure * 4) + rng.uniform(-1.5, 1.5))
                seasonal = 1 + 0.12 * (1 if m.month in (6, 7, 8) else -1 if m.month in (12, 1, 2) else 0) * \
                    (1 if c["_segment"] in ("hvac_plumbing", "pest_landscaping") else 0.3)
                jobs = int(active * jobs_day * 21 * seasonal * rng.uniform(0.9, 1.08))
            drive = round(drive0 * (0.85 if "Route Optimizer" in c["addons"] else 1.0) * rng.uniform(0.92, 1.08), 1)
            assist = int(active * rng.uniform(18, 45)) if has_assist and m >= dt.date(2025, 10, 1) else 0
            rows.append({"month": m.isoformat(), "customer_id": c["customer_id"], "licensed_technicians": lic,
                         "active_technicians": active, "jobs_completed": jobs,
                         "work_orders_created": int(jobs * rng.uniform(1.04, 1.12)),
                         "first_time_fix_rate_pct": round(ftf, 1), "avg_drive_minutes_per_job": drive,
                         "assist_queries": assist})
    return rows


def tables() -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    customers = _customers(rng)
    usage = _usage(rng, customers)
    # health for generated customers: driven by last month's active ratio, tickets and churn state
    last = {}
    for u in usage:
        last[u["customer_id"]] = u["active_technicians"] / max(1, u["licensed_technicians"])
    for c in customers:
        if not c["health_score"]:
            base = 35 + 60 * last.get(c["customer_id"], 0.5) + rng.gauss(0, 6)
            c["health_score"] = int(max(5, min(100, round(base if c["is_active"] else base * 0.4))))
    orders = _orders(rng, customers)
    pipeline = _pipeline(rng, customers)
    tickets = _tickets(rng, customers)
    invoices = _invoices(rng, customers, orders)
    for c in customers:
        c.pop("_segment")
    products = [{"product_id": p[0], "product_name": p[1], "category": p[2], "list_price_usd": p[3],
                 "billing_unit": p[4], "launched_date": p[5]} for p in PRODUCTS]
    return {"smb_customers": customers, "smb_products": products, "smb_orders": orders, "smb_pipeline": pipeline,
            "smb_support_tickets": tickets, "smb_invoices": invoices, "smb_product_usage": usage}


if __name__ == "__main__":
    for name, rows in tables().items():
        print(name, len(rows))

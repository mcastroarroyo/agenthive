"""Synthetic BigQuery rows for the enterprise financial + healthcare agents.

Fictional organisations: Quillmark Bank (general ledger, plan, KPIs, channels) and Corvina Health Network (claim
denials). Deterministic: every table uses its own random.Random(seed). Schemas: agenthive/grounding/bq/
enterprise_finhealth.json. Loaded by deploy/seed_bigquery.py.

Stories baked into the data (also described in the enterprise knowledge base):
  * Q3 2026 Technology (CC-900) over budget: data-centre exit slipped from June to October (cloud + DC double
    running) and a one-off software licence true-up in August 2026.
  * Card fraud ring July-August 2026: fraud losses (CP-500), card complaints and contact-centre volumes spike.
  * Mobile-app outage 12-13 May 2026: failed transactions, contact-centre surge, Retail NPS dip, ops-loss refunds.
  * Net interest margin compression from March 2026 after rate cuts; Private Wealth fees ahead of plan.
  * Commercial real-estate downgrade: Commercial Banking provisions and NPL ratio rise in Q3 2026.
  * Silverline Health Plan prior-authorisation rule for advanced imaging (from 2026-07-01) drives CO-197 denials;
    Bluewater's referring-NPI requirement (from 2026-08-15) drives CO-16 denials.
"""
from __future__ import annotations

import datetime as dt
import random

SEED = 20261106

# ------------------------------------------------------------------------------------------------ ledger setup ---
ACCOUNTS = {
    "4100": ("Net interest income", "Net interest income", "revenue"),
    "4200": ("Fees & commissions", "Fee & commission income", "revenue"),
    "4300": ("Advisory & management fees", "Wealth fees", "revenue"),
    "4400": ("Interchange & card fees", "Card & payment fees", "revenue"),
    "6100": ("Salaries & benefits", "Personnel", "expense"),
    "6200": ("Technology & software", "Technology", "expense"),
    "6250": ("Cloud & data centre", "Technology", "expense"),
    "6300": ("Occupancy", "Occupancy", "expense"),
    "6400": ("Marketing", "Marketing", "expense"),
    "6500": ("Professional fees", "Professional fees", "expense"),
    "6600": ("Fraud & operational losses", "Fraud & operational losses", "expense"),
    "6700": ("Credit loss provisions", "Credit loss provisions", "expense"),
}
# cost centre -> (name, business unit, {account: base monthly USD in Jan 2024})
COST_CENTRES = {
    "RB-100": ("Branch Network", "Retail Banking",
               {"4100": 9.2e6, "4200": 1.4e6, "6100": 3.1e6, "6300": 1.05e6, "6400": 0.22e6}),
    "RB-120": ("Consumer Lending", "Retail Banking", {"4100": 6.8e6, "4200": 0.35e6, "6100": 0.9e6, "6700": 0.85e6}),
    "RB-200": ("Digital Banking", "Retail Banking", {"4200": 0.6e6, "6100": 1.2e6, "6200": 0.95e6, "6400": 0.38e6}),
    "CB-300": ("Commercial Lending", "Commercial Banking",
               {"4100": 8.4e6, "4200": 0.9e6, "6100": 1.6e6, "6700": 1.1e6}),
    "CB-310": ("Treasury & Payment Services", "Commercial Banking", {"4200": 2.1e6, "6100": 0.8e6, "6200": 0.42e6}),
    "PW-400": ("Advisory", "Private Wealth", {"4300": 3.6e6, "6100": 1.5e6, "6400": 0.12e6}),
    "PW-410": ("Trust & Estate", "Private Wealth", {"4300": 1.2e6, "6100": 0.55e6, "6500": 0.09e6}),
    "CP-500": ("Card Issuing", "Cards & Payments",
               {"4100": 3.9e6, "4400": 2.6e6, "6100": 0.7e6, "6400": 0.45e6, "6600": 0.38e6, "6700": 1.2e6}),
    "CP-510": ("Merchant Services", "Cards & Payments", {"4400": 1.9e6, "6100": 0.4e6, "6600": 0.12e6}),
    "CC-900": ("Technology", "Corporate Center", {"6100": 2.4e6, "6200": 2.9e6, "6250": 1.3e6, "6500": 0.35e6}),
    "CC-910": ("Operations", "Corporate Center", {"6100": 1.9e6, "6300": 0.6e6, "6600": 0.15e6}),
    "CC-920": ("Risk & Compliance", "Corporate Center", {"6100": 1.1e6, "6200": 0.25e6, "6500": 0.3e6}),
}
START = dt.date(2024, 1, 1)


def _months(first: dt.date, last: dt.date) -> list[dt.date]:
    out, d = [], first
    while d <= last:
        out.append(d)
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def _idx(m: dt.date) -> int:
    return (m.year - START.year) * 12 + m.month - START.month


def _key(m: dt.date) -> str:
    return m.strftime("%Y-%m")


def _trend(acct: str, base: float, m: dt.date) -> float:
    growth = 1.0045 if ACCOUNTS[acct][2] == "revenue" else 1.003
    season = 1.0
    if acct == "4200" and m.month == 12:
        season = 1.05
    if acct == "6400":
        season = {1: 1.15, 3: 1.05, 9: 1.0, 10: 1.1, 12: 0.85}.get(m.month, 1.0)
    return base * growth ** _idx(m) * season


def _nii_compression(m: dt.date) -> float:
    k = (m.year - 2026) * 12 + m.month - 2          # months since Feb 2026
    return 1 - 0.006 * k if k > 0 else 1.0


def _actual(cc: str, acct: str, base: float, m: dt.date, rng: random.Random) -> float:
    v = _trend(acct, base, m) * (1 + rng.gauss(0, 0.015))
    k = _key(m)
    if acct == "4100":
        v *= _nii_compression(m)
    if cc == "CC-900" and acct == "6250" and "2026-07" <= k <= "2026-09":
        v *= 1.08                                       # DC exit slipped: double running
    if cc == "CC-900" and acct == "6200" and k == "2026-08":
        v += 1_100_000                                  # one-off licence true-up
    if cc == "CP-500" and acct == "6600":
        v = {"2026-07": 920_000, "2026-08": 1_350_000, "2026-09": 710_000}.get(k, v)
    if cc == "CP-510" and acct == "6600" and k == "2026-08":
        v *= 1.6
    if cc == "CP-500" and acct == "4400" and "2026-07" <= k <= "2026-09":
        v *= 1.03
    if cc in ("PW-400", "PW-410") and acct == "4300" and k >= "2026-01":
        v *= 1 + (0.015 if cc == "PW-400" else 0.007) * (m.month)
    if cc == "CB-300" and acct == "6100" and k >= "2026-04":
        v *= 0.93                                       # hiring freeze / vacancies
    if cc == "CB-300" and acct == "6700":
        v = {"2026-04": 1.32e6, "2026-05": 1.36e6, "2026-06": 1.38e6, "2026-07": 1.88e6, "2026-08": 1.92e6,
             "2026-09": 1.95e6}.get(k, v)
    if cc == "RB-200" and acct == "6400" and k == "2026-09":
        v = 720_000                                     # app relaunch campaign pulled forward from October
    if cc == "CC-910" and acct == "6600" and k == "2026-05":
        v += 350_000                                    # mobile outage refunds and fee waivers
    if cc == "CC-920" and acct == "6500" and "2026-07" <= k <= "2026-09":
        v += 250_000                                    # KYC remediation contractors
    return round(v, 2)


def _budget(cc: str, acct: str, base: float, m: dt.date) -> float:
    v = _trend(acct, base, m) * 1.01
    k = _key(m)
    if cc == "CC-900" and acct == "6250" and k >= "2026-07":
        v *= 0.55                                       # plan assumed DC exit end of June 2026
    if cc == "RB-200" and acct == "6400" and k == "2026-10":
        v = 700_000
    if cc == "CB-300" and acct == "6700" and k >= "2026-01":
        v = 1.2e6
    return round(v, 2)


def _forecast(cc: str, acct: str, base: float, m: dt.date) -> float:
    """Q3 2026 reforecast prepared 2026-07-20: remaining months only (Jul-Dec)."""
    v = _trend(acct, base, m)
    k = _key(m)
    if acct == "4100":
        v *= 0.965
    if cc == "CC-900" and acct == "6250":
        v *= 1.05 if k <= "2026-10" else 0.6
    if cc == "CP-500" and acct == "6600":
        v = 600_000 if k <= "2026-09" else 500_000
    if cc == "CB-300" and acct == "6700":
        v = 1.6e6
    if cc == "CB-300" and acct == "6100":
        v *= 0.94
    if cc in ("PW-400", "PW-410") and acct == "4300":
        v *= 1.07 if cc == "PW-400" else 1.03
    if cc == "RB-200" and acct == "6400" and k == "2026-10":
        v = 700_000
    if cc == "CC-920" and acct == "6500":
        v += 150_000
    return round(v, 2)


def _gl(rng: random.Random) -> list[dict]:
    rows = []
    for m in _months(START, dt.date(2026, 9, 1)):
        for cc, (cname, bu, accts) in COST_CENTRES.items():
            for acct, base in accts.items():
                name, line, typ = ACCOUNTS[acct]
                rows.append({"month": m.isoformat(), "business_unit": bu, "cost_center": cc,
                             "cost_center_name": cname, "pnl_line": line, "account_code": acct,
                             "account_name": name, "line_type": typ,
                             "amount_usd": _actual(cc, acct, base, m, rng)})
    return rows


def _plan(gl: list[dict]) -> list[dict]:
    actual = {(r["month"], r["cost_center"], r["account_code"]): r["amount_usd"] for r in gl}
    rows = []
    for m in _months(dt.date(2025, 1, 1), dt.date(2026, 12, 1)):
        for cc, (cname, bu, accts) in COST_CENTRES.items():
            for acct, base in accts.items():
                common = {"month": m.isoformat(), "business_unit": bu, "cost_center": cc, "account_code": acct,
                          "pnl_line": ACCOUNTS[acct][1], "line_type": ACCOUNTS[acct][2]}
                rows.append({**common, "scenario": "budget", "version": f"FY{m.year} Budget",
                             "amount_usd": _budget(cc, acct, base, m)})
                if m.year == 2026:
                    act = actual.get((m.isoformat(), cc, acct))
                    is_actual = m.month <= 6 and act is not None
                    rows.append({**common, "scenario": "forecast", "version": "Q3 2026 Reforecast (6+6, 2026-07-20)",
                                 "amount_usd": act if is_actual else _forecast(cc, acct, base, m)})
    return rows


# ---------------------------------------------------------------------------------------------------- KPIs -------
def _kpis(gl: list[dict], rng: random.Random) -> list[dict]:
    agg: dict[tuple[str, str], dict[str, float]] = {}
    for r in gl:
        a = agg.setdefault((r["month"], r["business_unit"]), {"rev": 0.0, "opex": 0.0, "prov": 0.0})
        if r["line_type"] == "revenue":
            a["rev"] += r["amount_usd"]
        elif r["account_code"] == "6700":
            a["prov"] += r["amount_usd"]
        else:
            a["opex"] += r["amount_usd"]
    rows = []
    aum = 18_200.0
    for m in _months(START, dt.date(2026, 9, 1)):
        i, k = _idx(m), _key(m)
        for bu in ("Retail Banking", "Commercial Banking", "Private Wealth", "Cards & Payments"):
            a = agg[(m.isoformat(), bu)]
            row = {"month": m.isoformat(), "business_unit": bu, "revenue_usd_m": round(a["rev"] / 1e6, 3),
                   "operating_expense_usd_m": round(a["opex"] / 1e6, 3),
                   "cost_income_ratio_pct": round(a["opex"] / a["rev"] * 100, 1),
                   "credit_provisions_usd_m": round(a["prov"] / 1e6, 3),
                   "net_interest_margin_pct": None, "loans_usd_m": None, "deposits_usd_m": None, "aum_usd_m": None,
                   "net_new_assets_usd_m": None, "npl_ratio_pct": None}
            noise = rng.gauss(0, 1)
            if bu == "Retail Banking":
                nim = 3.10 + 0.0075 * min(i, 20) - (0.04 * ((m.year - 2026) * 12 + m.month - 2)
                                                    if k >= "2026-03" else 0)
                nps = 38 + i * 0.12 + noise * 1.2
                nps = {"2026-05": 29, "2026-06": 35, "2026-07": 39}.get(k, nps)
                dig = 54 + i * 0.36 + noise * 0.3 - (3 if k == "2026-05" else 0)
                row.update(net_interest_margin_pct=round(nim, 2), loans_usd_m=round(9_800 * 1.004 ** i, 1),
                           deposits_usd_m=round(14_200 * 1.003 ** i + noise * 40, 1),
                           npl_ratio_pct=round(0.92 + noise * 0.02, 2), nps=round(nps),
                           new_customers=int(5_200 * 1.004 ** i + noise * 120), digital_active_pct=round(dig, 1),
                           complaints=int(610 + noise * 30 + (420 if k == "2026-05" else 0)),
                           active_customers=int(1_120_000 * 1.002 ** i))
            elif bu == "Commercial Banking":
                nim = 2.85 - (0.02 * ((m.year - 2026) * 12 + m.month - 2) if k >= "2026-03" else 0)
                npl = 1.05 + i * 0.004 + noise * 0.01
                npl = {"2026-07": 1.38, "2026-08": 1.52, "2026-09": 1.66}.get(k, npl)
                row.update(net_interest_margin_pct=round(nim, 2), loans_usd_m=round(7_400 * 1.003 ** i, 1),
                           deposits_usd_m=round(8_900 * 1.0025 ** i + noise * 30, 1), npl_ratio_pct=round(npl, 2),
                           nps=round(31 + noise * 1.5), new_customers=int(180 + noise * 12),
                           digital_active_pct=round(71 + i * 0.2, 1), complaints=int(48 + noise * 5),
                           active_customers=int(21_500 * 1.001 ** i))
            elif bu == "Private Wealth":
                nna = 60 + 25 * (i / 32) + noise * 15 + (45 if k >= "2026-07" else 0)
                market = 1 + rng.gauss(0.006, 0.02) + (0.012 if "2026-01" <= k <= "2026-09" else 0)
                aum = aum * market + nna
                row.update(aum_usd_m=round(aum, 1), net_new_assets_usd_m=round(nna, 1), nps=round(52 + noise * 1.5),
                           new_customers=int(95 + noise * 8), digital_active_pct=round(46 + i * 0.25, 1),
                           complaints=int(14 + abs(noise) * 3), active_customers=int(8_300 * 1.002 ** i),
                           deposits_usd_m=round(2_100 * 1.002 ** i, 1))
            else:
                npl = 2.1 + i * 0.006 + noise * 0.03
                comp = 420 + noise * 25
                comp = {"2026-07": 760, "2026-08": 1310, "2026-09": 690}.get(k, comp)
                row.update(net_interest_margin_pct=round(9.8 + noise * 0.05, 2),
                           loans_usd_m=round(2_350 * 1.004 ** i, 1), npl_ratio_pct=round(npl, 2),
                           nps=round(33 + noise * 1.2 - (6 if k == "2026-08" else 0)),
                           new_customers=int(7_800 * 1.003 ** i + noise * 200),
                           digital_active_pct=round(61 + i * 0.3, 1), complaints=int(comp),
                           active_customers=int(640_000 * 1.003 ** i))
            rows.append(row)
    return rows


# ------------------------------------------------------------------------------------------------ channels -------
CHANNELS = {  # base daily transactions (Central region), daily trend, avg value, base failed %, customers/txn
    "mobile_app": (52_000, 0.0008, 85.0, 0.7, 0.62),
    "online_banking": (21_000, -0.0002, 310.0, 0.5, 0.66),
    "branch": (6_500, -0.0004, 640.0, 0.1, 0.9),
    "atm": (14_000, 0.0, 120.0, 1.2, 0.8),
    "contact_center": (3_800, 0.0, 0.0, 4.0, 0.95),
}
REGIONS = {"North": 1.0, "Central": 1.3, "Coastal": 0.8}
HOLIDAYS = {"2026-01-01", "2026-05-25", "2026-07-03", "2026-09-07"}


def _channels(rng: random.Random) -> list[dict]:
    rows = []
    d = dt.date(2026, 1, 1)
    while d <= dt.date(2026, 9, 30):
        ds, wd, n = d.isoformat(), d.weekday(), (d - dt.date(2026, 1, 1)).days
        for ch, (base, trend, avg, fail, cust) in CHANNELS.items():
            for region, rm in REGIONS.items():
                vol = base / 1.3 * rm * (1 + trend) ** n * (1 + rng.gauss(0, 0.03))
                f = max(0.02, fail + rng.gauss(0, fail * 0.12))
                if ch == "branch":
                    vol *= 0 if (wd == 6 or ds in HOLIDAYS) else 0.45 if wd == 5 else 1
                elif ch == "online_banking":
                    vol *= 0.7 if wd >= 5 else 1
                elif ch == "mobile_app":
                    vol *= 0.85 if wd >= 5 else 1
                elif ch == "atm":
                    vol *= 1.1 if wd >= 5 else 1
                elif ch == "contact_center":
                    vol *= 0.5 if wd >= 5 else 1
                if d.day in (1, 15) and ch in ("mobile_app", "atm"):
                    vol *= 1.12
                if ds == "2026-05-12":           # mobile-app outage 08:10-14:40
                    vol *= {"mobile_app": 0.62, "online_banking": 1.35, "contact_center": 1.8}.get(ch, 1.05)
                    f = {"mobile_app": 18.5 + rng.gauss(0, 0.6), "contact_center": 21.0}.get(ch, f)
                elif ds == "2026-05-13":
                    vol *= {"mobile_app": 0.85, "online_banking": 1.15, "contact_center": 1.4}.get(ch, 1.0)
                    f = {"mobile_app": 9.2 + rng.gauss(0, 0.4), "contact_center": 12.0}.get(ch, f)
                elif "2026-08-04" <= ds <= "2026-08-08":   # card-fraud ring: card blocks and calls
                    if ch == "contact_center":
                        vol *= 1.6
                        f = 9 + rng.random() * 2
                    elif ch == "mobile_app":
                        f = 1.4 + rng.gauss(0, 0.1)
                tx = int(round(vol))
                rows.append({"date": ds, "channel": ch, "region": region, "transactions": tx,
                             "value_usd": round(tx * avg * (1 + rng.gauss(0, 0.02)), 2),
                             "failed_pct": round(f, 2) if tx else 0.0, "unique_customers": int(tx * cust)})
        d += dt.timedelta(days=1)
    return rows


# ------------------------------------------------------------------------------------------------ denials --------
PAYERS = {"Silverline Health Plan": 0.34, "Pinecrest Mutual": 0.28, "Bluewater Senior Advantage": 0.22,
          "State Medical Assistance Program (synthetic)": 0.16}
CODES = {"CO-197": "authorization", "CO-50": "medical_necessity", "CO-16": "missing_information",
         "CO-29": "timely_filing", "CO-11": "coding", "CO-4": "coding", "CO-97": "bundling", "CO-18": "duplicate"}
CODE_W = {"CO-197": 0.18, "CO-50": 0.22, "CO-16": 0.17, "CO-29": 0.06, "CO-11": 0.12, "CO-4": 0.09, "CO-97": 0.10,
          "CO-18": 0.06}
SERVICES = {  # service line -> (facility, department, billed min, billed max, weight)
    "Advanced imaging": ("Corvina Northside Imaging", "Radiology", 900, 4200, 0.18),
    "Inpatient stay": ("Corvina General Hospital", "Inpatient medicine", 8000, 42000, 0.12),
    "Emergency department": ("Corvina General Hospital", "Emergency department", 600, 5200, 0.16),
    "Laboratory": ("Corvina General Hospital", "Laboratory", 60, 4500, 0.15),
    "Physical therapy": ("Corvina Rehab Center", "Physical therapy", 120, 480, 0.11),
    "Office visit": ("Corvina Northside Clinic", "Primary care", 110, 320, 0.18),
    "Outpatient surgery": ("Corvina Lakeside Medical Center", "Orthopaedics", 2500, 14000, 0.10),
}
APPEAL = {  # category -> (probability worked, success probability, route)
    "authorization": (0.75, 0.55, "appeal"), "medical_necessity": (0.6, 0.35, "appeal"),
    "missing_information": (0.9, 0.9, "corrected"), "timely_filing": (0.4, 0.15, "appeal"),
    "coding": (0.85, 0.75, "corrected"), "bundling": (0.7, 0.55, "corrected"), "duplicate": (0.1, 0.05, "appeal"),
}


def _pick(rng: random.Random, weights: dict) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _denials(rng: random.Random) -> list[dict]:
    rows = []
    as_of = dt.date(2026, 11, 6)

    def add(denial: dt.date, payer: str, code: str, service: str, auth_existed: bool = False):
        fac, dept, lo, hi, _ = SERVICES[service]
        cat = CODES[code]
        billed = round(rng.uniform(lo, hi), 2)
        denied = billed if rng.random() < 0.8 else round(billed * rng.uniform(0.3, 0.9), 2)
        worked_p, win_p, route = APPEAL[cat]
        if auth_existed:
            worked_p, win_p = 0.85, 0.72
        appealed = rng.random() < worked_p
        outcome, recovered, days = "not_appealed", 0.0, None
        if appealed:
            age = (as_of - denial).days
            if age < 30 and rng.random() < 0.7:
                outcome = "pending"
            elif rng.random() < win_p:
                outcome = "corrected_claim_paid" if route == "corrected" else "overturned"
                recovered = round(denied * (0.95 if route == "corrected" else rng.uniform(0.85, 1.0)), 2)
                days = int(rng.uniform(12, 30) if route == "corrected" else rng.uniform(25, 75))
            else:
                outcome = "upheld"
                days = int(rng.uniform(25, 80))
            if days is not None and (denial + dt.timedelta(days=days)) > as_of:
                outcome, recovered, days = "pending", 0.0, None
        service_date = denial - dt.timedelta(days=int(rng.uniform(10, 45)))
        rows.append({"claim_id": f"DN-{denial.strftime('%y')}-{len(rows) + 100001}", "denial_date": denial.isoformat(),
                     "service_date": service_date.isoformat(), "facility": fac, "department": dept,
                     "service_line": service, "payer": payer, "denial_code": code, "denial_category": cat,
                     "billed_amount_usd": billed, "denied_amount_usd": denied, "appealed": appealed,
                     "appeal_outcome": outcome, "recovered_amount_usd": recovered, "days_to_resolution": days})

    for m in _months(dt.date(2025, 10, 1), dt.date(2026, 10, 1)):
        days_in = (dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1) - m).days
        for _ in range(int(138 + rng.gauss(0, 8))):
            add(m + dt.timedelta(days=rng.randrange(days_in)), _pick(rng, PAYERS), _pick(rng, CODE_W),
                _pick(rng, {k: v[4] for k, v in SERVICES.items()}))
        if m >= dt.date(2026, 7, 1):          # Silverline advanced-imaging prior-auth rule (bulletin SL-2026-14)
            for _ in range(int(48 + rng.gauss(0, 4))):
                add(m + dt.timedelta(days=rng.randrange(days_in)), "Silverline Health Plan", "CO-197",
                    "Advanced imaging", auth_existed=rng.random() < 0.6)
        if m >= dt.date(2026, 8, 1):          # Bluewater referring-NPI requirement from 2026-08-15
            start = 14 if m.month == 8 else 0
            for _ in range(int((17 if m.month == 8 else 32) + rng.gauss(0, 3))):
                add(m + dt.timedelta(days=start + rng.randrange(days_in - start)), "Bluewater Senior Advantage",
                    "CO-16", rng.choice(["Advanced imaging", "Laboratory"]))
    rows.sort(key=lambda r: (r["denial_date"], r["claim_id"]))
    return rows


def tables() -> dict[str, list[dict]]:
    gl = _gl(random.Random(SEED))
    return {
        "fin_gl_actuals": gl,
        "fin_budget_forecast": _plan(gl),
        "fin_kpi_monthly": _kpis(gl, random.Random(SEED + 1)),
        "fin_channel_daily": _channels(random.Random(SEED + 2)),
        "hlt_claim_denials": _denials(random.Random(SEED + 3)),
    }


if __name__ == "__main__":
    for name, rows in tables().items():
        print(f"{name}: {len(rows)} rows · columns {list(rows[0])}")

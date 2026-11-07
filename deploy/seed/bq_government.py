"""Synthetic BigQuery rows for the government realm (schema: agenthive/grounding/bq/government.json).

gov_311_requests — a deterministic sample of City of Port Alder 311 requests, 2025-01-01 to 2026-10-31, with the
patterns the Citizen 311 Operations Analyst demo talks about:
  * potholes peak in the rainy months (January-March);
  * District D5 (Eastgate, Juniper Flats) pothole repairs slow down in Q3 2026 when Streets crews were diverted to
    water-main restoration, so SLA compliance drops sharply versus Q2 2026;
  * District D3 streetlight repairs slip from August 2026 (replacement-pole shortage);
  * the messaging channel grows from about 5% to about 30% of intake.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import random
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[2] / "agenthive" / "tools" / "fixtures" / "gov_311.json"
START, END = dt.date(2025, 1, 1), dt.date(2026, 10, 31)
AS_OF = dt.datetime(2026, 10, 31, 23, 59)

CATEGORY_WEIGHTS = {"POTHOLE": 22, "STREETLIGHT_OUT": 12, "MISSED_COLLECTION": 18, "BULKY_ITEM": 10, "ILLEGAL_DUMPING": 9,
                    "GRAFFITI": 7, "TRAFFIC_SIGNAL": 3, "SIGN_DAMAGE": 3, "WATER_LEAK": 5, "TREE_DOWN": 4,
                    "ABANDONED_VEHICLE": 4, "SIDEWALK_DAMAGE": 2, "DEAD_ANIMAL": 1}
P1_SHARE = {"POTHOLE": 0.35, "TRAFFIC_SIGNAL": 0.6, "WATER_LEAK": 0.3, "TREE_DOWN": 0.3, "ILLEGAL_DUMPING": 0.2,
            "GRAFFITI": 0.1, "SIGN_DAMAGE": 0.25}
P3_SHARE = {"BULKY_ITEM": 0.8, "ABANDONED_VEHICLE": 0.7, "SIDEWALK_DAMAGE": 0.7}
DEPT_SPEED = {"SAN": 0.45, "PW-LGT": 0.7, "PW-STR": 0.55, "TRN": 0.5, "WTR": 0.5, "PRK": 0.6, "CDE": 0.6, "ANS": 0.5, "PKE": 0.65}
DISTRICTS = {"D1": (18, ["Old Town", "Harborview"]), "D2": (13, ["Saltmarsh", "Station Quarter"]),
             "D3": (14, ["Kestrel Heights", "Willow Park"]), "D4": (12, ["Millbrook"]),
             "D5": (17, ["Eastgate", "Juniper Flats"]), "D6": (12, ["Fairhaven", "Pelican Point"]),
             "D7": (14, ["Northpoint", "Quarry Hill"])}


def _seasonal(cat: str, month: int) -> float:
    if cat == "POTHOLE":
        return 1.6 if month in (1, 2, 3) else 0.8 if month in (6, 7, 8) else 1.0
    if cat == "STREETLIGHT_OUT":
        return 1.3 if month in (11, 12, 1, 2) else 1.0
    if cat in ("TREE_DOWN", "WATER_LEAK"):
        return 1.5 if month in (1, 2, 12) else 1.0
    return 1.0


def _slowdown(cat: str, district: str, created: dt.datetime) -> float:
    if cat == "POTHOLE" and district == "D5" and dt.datetime(2026, 7, 1) <= created < dt.datetime(2026, 10, 1):
        return 1.9   # Streets crews diverted to water-main restoration
    if cat == "STREETLIGHT_OUT" and district == "D3" and created >= dt.datetime(2026, 8, 1):
        return 1.7   # replacement-pole shortage
    return 1.0


def _channel(rng: random.Random, created: dt.datetime) -> str:
    months = (created.year - 2025) * 12 + created.month - 1          # 0..21
    messaging = 0.05 + 0.25 * months / 21
    weights = {"messaging": messaging, "app": 0.22, "web": 0.18, "walk_in": 0.03}
    weights["phone"] = max(0.05, 1 - sum(weights.values()))
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def _ts(d: dt.datetime | None) -> str | None:
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else None


def tables() -> dict[str, list[dict]]:
    """Return {table_name: rows} for every government BigQuery table (deterministic)."""
    rng = random.Random(311)
    cats = {c["code"]: c for c in json.loads(FIXTURE.read_text())["categories"]}
    rows: list[dict] = []
    day, seq = START, 0
    while day <= END:
        for _ in range(rng.randint(4, 10)):
            seq += 1
            weights = [w * _seasonal(c, day.month) for c, w in CATEGORY_WEIGHTS.items()]
            cat = rng.choices(list(CATEGORY_WEIGHTS), weights=weights)[0]
            district = rng.choices(list(DISTRICTS), weights=[v[0] for v in DISTRICTS.values()])[0]
            hood = rng.choice(DISTRICTS[district][1])
            created = dt.datetime.combine(day, dt.time(rng.randint(6, 21), rng.randint(0, 59), rng.randint(0, 59)))
            r = rng.random()
            prio = "P1" if r < P1_SHARE.get(cat, 0.05) else "P3" if r > 1 - P3_SHARE.get(cat, 0.1) else "P2"
            sla = cats[cat]["sla_hours"][prio]
            dept = cats[cat]["department"]
            median = DEPT_SPEED[dept] * _slowdown(cat, district, created)
            ratio = math.exp(rng.gauss(math.log(median), 0.6))
            closed = created + dt.timedelta(hours=round(sla * ratio, 1))
            is_open = closed > AS_OF
            due = created + dt.timedelta(hours=sla)
            met = None if is_open and due > AS_OF else (False if is_open else closed <= due)
            survey = None
            if not is_open and rng.random() < 0.35:
                survey = rng.choice([5, 5, 4, 4, 3] if met else [1, 2, 2, 3, 4])
            rows.append({
                "request_id": f"SR-H{created:%y}-{seq:05d}",
                "created_at": _ts(created),
                "closed_at": None if is_open else _ts(closed),
                "category": cat,
                "department": dept,
                "district": district,
                "neighborhood": hood,
                "channel": _channel(rng, created),
                "priority": prio,
                "status": "open" if is_open else "closed",
                "sla_hours": sla,
                "hours_to_close": None if is_open else round((closed - created).total_seconds() / 3600, 1),
                "sla_met": met,
                "is_duplicate": rng.random() < (0.18 if cat in ("POTHOLE", "STREETLIGHT_OUT") else 0.06),
                "reopened": (not is_open) and rng.random() < 0.03,
                "satisfaction_score": survey,
            })
        day += dt.timedelta(days=1)
    return {"gov_311_requests": rows}


if __name__ == "__main__":
    t = tables()
    for name, rs in t.items():
        print(name, len(rs), rs[0])

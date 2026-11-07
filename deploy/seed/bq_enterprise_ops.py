"""Synthetic BigQuery rows for the enterprise realm, telco / retail / logistics part
(schema: agenthive/grounding/bq/enterprise_ops.json).

Rows are derived from the same fixtures the function tools read (agenthive/tools/fixtures/tel_*, ret_*, log_*), so
SQL answers and tool answers agree:
  * tel_incidents     — October/November 2026 are exactly the fixture incidents; earlier months follow each
                        service's 90-day incident rate.
  * tel_campaign_results — weekly x segment x arm splits whose totals equal the campaign scorecard; Price-sensitive
                        customers drive most of the (small) uplift of CMP-2610-SAVE02.
  * ret_sales_weekly / ret_inventory_snapshot — the last 28 days of sales equal the fixture's average daily sales,
                        and the 2026-11-06 snapshot equals the fixture positions; Buds 3 sales drop after Buds 4 launched
                        (2026-09-15) and Labor Day / fall-event promotions show their lift.
  * log_shipments / log_lane_performance — 26 weeks of delivered history whose last-30-day on-time rates match the lane
                        scorecard, plus the shipments active on 2026-11-06.
  * log_dc_demand_daily — daily demand around each item's mean (last 14 days at the recent mean).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import random
from pathlib import Path

FIX = Path(__file__).resolve().parents[2] / "agenthive" / "tools" / "fixtures"
TS = "%Y-%m-%d %H:%M:%S"


def _fx(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text())


def _ts(s: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(s) if s else None


def _fmt(d: dt.datetime | None) -> str | None:
    return d.strftime(TS) if d else None


def _split(total: int, weights: list[float]) -> list[int]:
    """Integer split of `total` proportional to weights (largest remainder) — sums exactly to total."""
    s = sum(weights) or 1.0
    raw = [total * w / s for w in weights]
    out = [math.floor(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[: total - sum(out)]:
        out[i] += 1
    return out


# --- telco ------------------------------------------------------------------------------------------------------------


def _tel_contracts() -> list[dict]:
    sla = _fx("tel_sla_contracts")
    rows = []
    for c in sla["customers"]:
        t = sla["tiers"][c["tier"]]
        for s in c["services"]:
            rows.append({"customer_id": c["customer_id"], "customer_name": c["name"], "industry": c["industry"],
                         "tier": c["tier"], "service_id": s["service_id"], "service_type": s["type"],
                         "sites": s["sites"], "mrc_usd": float(s["mrc_usd"]),
                         "availability_target_pct": t["availability_target_pct"],
                         "restore_target_p1_hours": float(t["restore_hours"]["P1"]),
                         "restore_target_p2_hours": float(t["restore_hours"]["P2"]),
                         "credit_cap_pct": float(t["credit_cap_pct"]), "account_manager": c["account_manager"]})
    return rows


_CAUSES = [("fiber_cut", "Fiber cut on access segment"), ("hardware", "Router or CPE hardware failure"),
           ("software", "Software defect after upgrade"), ("config", "Configuration error during change"),
           ("power", "Power interruption at PoP"), ("third_party", "Upstream provider outage"),
           ("planned_maintenance", "Planned maintenance with notice"), ("customer_caused", "Customer premises issue")]


def _tel_incidents() -> list[dict]:
    rng = random.Random(2611)
    sla = _fx("tel_sla_contracts")
    now = _ts(_fx("tel_incidents")["as_of"])
    rows = []
    for c in sla["customers"]:
        tier = sla["tiers"][c["tier"]]
        for s in c["services"]:
            rate = s["history_90d"]["incidents"] / 90
            avg = s["history_90d"]["avg_site_minutes"]
            day = dt.datetime(2025, 11, 1)
            n = 0
            while day < dt.datetime(2026, 10, 1):
                if rng.random() < rate:
                    n += 1
                    cat, cause = rng.choices(_CAUSES, weights=[14, 22, 16, 14, 8, 12, 9, 5])[0]
                    sev = rng.choices(["P1", "P2", "P3"], weights=[2, 5, 3])[0]
                    sites = max(1, min(s["sites"], round(rng.expovariate(1 / max(1.0, s["sites"] * 0.06)))))
                    minutes = max(5, round(rng.expovariate(sites / avg)))
                    opened = day + dt.timedelta(minutes=rng.randint(0, 1439))
                    restored = opened + dt.timedelta(minutes=minutes)
                    hours = minutes / 60
                    rows.append({"incident_id": f"INC-H{opened:%y%m}-{s['service_id'][-4:]}{n:03d}",
                                 "customer_id": c["customer_id"], "service_id": s["service_id"],
                                 "month": opened.strftime("%Y-%m-01"), "severity": sev, "opened_at": _fmt(opened),
                                 "restored_at": _fmt(restored), "outage_minutes": minutes, "sites_affected": sites,
                                 "site_minutes": minutes * sites, "category": cat, "cause": cause,
                                 "excluded": cat in ("planned_maintenance", "customer_caused"),
                                 "restore_hours": round(hours, 2),
                                 "restore_target_met": hours <= tier["restore_hours"][sev],
                                 "customer_notified_after_min": rng.randint(12, 70)})
                day += dt.timedelta(days=1)
    tiers = {c["customer_id"]: sla["tiers"][c["tier"]] for c in sla["customers"]}
    for i in _fx("tel_incidents")["incidents"]:
        opened, restored = _ts(i["opened"]), _ts(i["restored"])
        hours = ((restored or now) - opened).total_seconds() / 3600
        rows.append({"incident_id": i["incident_id"], "customer_id": i["customer_id"], "service_id": i["service_id"],
                     "month": opened.strftime("%Y-%m-01"), "severity": i["severity"], "opened_at": _fmt(opened),
                     "restored_at": _fmt(restored), "outage_minutes": i["outage_minutes"],
                     "sites_affected": i["sites_affected"], "site_minutes": i["outage_minutes"] * i["sites_affected"],
                     "category": i["category"], "cause": i["cause"], "excluded": i["excluded"],
                     "restore_hours": round(hours, 2) if restored else None,
                     "restore_target_met": (hours <= tiers[i["customer_id"]]["restore_hours"][i["severity"]]) if restored else None,
                     "customer_notified_after_min": i["customer_notified_after_min"]})
    return rows


# segment mix of the targeted base and the relative outcome rate per segment (treatment, control)
_SEG_MIX = {"Young digital": 0.22, "Families": 0.24, "Price-sensitive": 0.2, "Small business": 0.1,
            "Rural fiber": 0.12, "Premium": 0.12}
_SEG_EFFECT = {
    "CMP-2610-SAVE02": {"Young digital": (1.0, 1.0), "Families": (0.9, 0.9), "Price-sensitive": (1.3, 1.7),
                        "Small business": (0.8, 0.8), "Rural fiber": (1.0, 0.95), "Premium": (0.7, 0.6)},
    "CMP-2610-SAVE01": {"Young digital": (1.1, 1.2), "Families": (0.8, 1.1), "Price-sensitive": (1.3, 1.2),
                        "Small business": (0.9, 0.9), "Rural fiber": (0.9, 1.1), "Premium": (0.8, 0.8)},
}


def _tel_campaigns() -> list[dict]:
    rng = random.Random(1102)
    data = _fx("tel_campaigns")
    rows = []
    segs = list(_SEG_MIX)
    for c in data["campaigns"]:
        start, end = dt.date.fromisoformat(c["start"]), min(dt.date.fromisoformat(c["end"]), dt.date(2026, 11, 2))
        weeks, w = [], start - dt.timedelta(days=start.weekday())
        while w <= end:
            weeks.append(w)
            w += dt.timedelta(days=7)
        wk_w = [1.0 + 0.3 * rng.random() for _ in weeks]
        cells = [(wk, sg) for wk in weeks for sg in segs]
        base = [wk_w[weeks.index(wk)] * _SEG_MIX[sg] for wk, sg in cells]
        eff = _SEG_EFFECT.get(c["campaign_id"], {})
        cost = c["costs"]
        for arm in ("treatment", "control"):
            a = c[arm]
            targeted = _split(a["targeted"], base)
            reached = _split(a.get("reached", 0), base) if arm == "treatment" else [0] * len(cells)
            responded = _split(a.get("responded", 0), base) if arm == "treatment" else [0] * len(cells)
            k = 0 if arm == "treatment" else 1
            out_w = [b * eff.get(sg, (1, 1))[k] for b, (wk, sg) in zip(base, cells)]
            accepted = _split(a.get("accepted", 0), out_w if arm == "control" else base)
            churned = _split(a.get("churned", 0), out_w)
            for i, (wk, sg) in enumerate(cells):
                rows.append({"campaign_id": c["campaign_id"], "campaign_name": c["name"], "campaign_type": c["type"],
                             "week_start": wk.isoformat(), "segment": sg, "arm": arm, "targeted": targeted[i],
                             "reached": reached[i], "responded": responded[i], "accepted": accepted[i],
                             "churned": churned[i],
                             "offer_cost_usd": round(accepted[i] * cost["offer_cost_per_accept_usd"], 2) if arm == "treatment" else 0.0,
                             "contact_cost_usd": round(reached[i] * cost["contact_cost_per_reach_usd"], 2)})
    return rows


# --- retail -----------------------------------------------------------------------------------------------------------

_WEEKS = [dt.date(2026, 8, 10) + dt.timedelta(days=7 * i) for i in range(12)]          # last week starts 2026-10-26
_PROMOS = {  # (week index, category or sku) -> discount
    (3, "TV & Home Theater"): 15.0,          # Labor Day TV event, week of 2026-08-31
    (0, "Computing"): 10.0, (1, "Computing"): 10.0,     # back to school
    (9, "Audio"): 20.0,                      # fall audio event, week of 2026-10-12
    (6, "AUR-PARTY2"): 30.0,                 # end-of-summer clearance attempt, week of 2026-09-21
}
_ELAST = {"TV & Home Theater": -2.2, "Computing": -1.9, "Audio": -2.8, "Smart Home": -2.4, "Kitchen": -2.5,
          "Gaming": -2.3, "Networking": -2.0, "Wearables": -2.7}


def _season(sku: str, i: int) -> float:
    if sku == "AUR-PARTY2":
        return [3.2, 3.0, 2.6, 2.2, 1.8, 1.4, 1.2, 1.0, 1.0, 1.0, 1.0, 1.0][i]
    if sku == "AUR-BUDS3":
        return 1.0 if i >= 5 else 2.1                        # Buds 4 launched 2026-09-15 (week index 5)
    if sku == "WAV-AX3000":
        return 1.0 + 0.06 * (11 - i)
    if sku == "LUM-55Q8":
        return 1.0 + 0.04 * (11 - i)
    return 1.0 + 0.02 * math.sin(i)


def _ret_tables() -> dict[str, list[dict]]:
    rng = random.Random(4208)
    cat = _fx("ret_catalog")
    inv = _fx("ret_inventory")
    prods = {p["sku"]: p for p in cat["products"]}
    stores = [{"store_id": s["store_id"], "store_name": s["name"], "city": s["city"], "region": s["region"],
               "format": s["format"], "opened_date": s["opened"]} for s in cat["stores"]]
    products = [{"sku": p["sku"], "product_name": p["name"], "brand": p["brand"], "category": p["category"],
                 "unit_cost_usd": float(p["unit_cost_usd"]), "list_price_usd": float(p["list_price_usd"]),
                 "lifecycle": p["lifecycle"], "eol_date": p["eol_date"], "successor": p["successor"],
                 "ship_class": p["ship_class"]} for p in cat["products"]]
    sales, snaps = [], []
    for pos in inv["positions"]:
        p = prods[pos["sku"]]
        ads = pos["ads_28d"]
        disc = [_PROMOS.get((i, p["sku"]), _PROMOS.get((i, p["category"]), 0.0)) for i in range(12)]
        lift = [(1 - d / 100) ** _ELAST[p["category"]] if d else 1.0 for d in disc]
        w = [_season(p["sku"], i) * lift[i] * (0.85 + 0.3 * rng.random()) for i in range(12)]
        last4 = _split(round(ads * 28), w[8:])                # weeks 2026-10-05 .. 2026-10-26 = 28 days
        level = sum(w[j] / lift[j] for j in range(8, 12)) / 4  # promo-free weekly level of the last 4 weeks
        units = [max(0, round(ads * 7 * w[i] / level)) for i in range(8)] + last4
        for i, wk in enumerate(_WEEKS):
            price = p["list_price_usd"] * (1 - disc[i] / 100)
            sales.append({"week_start": wk.isoformat(), "store_id": pos["store_id"], "sku": p["sku"],
                          "units": units[i], "net_sales_usd": round(units[i] * price, 2),
                          "gross_margin_usd": round(units[i] * (price - p["unit_cost_usd"]), 2),
                          "promo_flag": disc[i] > 0, "avg_discount_pct": disc[i]})
        # snapshots: latest equals the fixture; earlier Fridays add back the sales of the following week
        on_hand = pos["on_hand"]
        for back, snap in enumerate([dt.date(2026, 11, 6), dt.date(2026, 10, 30), dt.date(2026, 10, 23),
                                     dt.date(2026, 10, 16)]):
            if back:
                on_hand += units[12 - back]
            a28 = ads if back == 0 else round(sum(units[max(0, 12 - back - 4): 12 - back]) / 28, 2)
            snaps.append({"snapshot_date": snap.isoformat(), "store_id": pos["store_id"], "sku": p["sku"],
                          "on_hand": on_hand, "on_order": pos["on_order"] if back < 3 else 0,
                          "on_order_eta": pos["on_order_eta"] if back < 3 else None, "avg_daily_sales_28d": a28,
                          "days_of_cover": round(on_hand / a28, 1) if a28 > 0 else 999.0})
    return {"ret_stores": stores, "ret_products": products, "ret_sales_weekly": sales, "ret_inventory_snapshot": snaps}


# --- logistics --------------------------------------------------------------------------------------------------------

_LANE_VOLUME = {"L01": 12, "L02": 10, "L03": 14, "L04": 10, "L05": 12, "L06": 12, "L07": 16, "L08": 30, "L09": 15,
                "L10": 4, "L11": 20, "L12": 6, "L13": 12, "L14": 6}
_LANE_SHIPPERS = {"L01": ["C-LRK", "C-SBR", "C-PNC"], "L02": ["C-LRK", "C-LRK", "C-ORL"], "L03": ["C-LRK", "C-GRF"],
                  "L04": ["C-GRF", "C-LRK"], "L05": ["C-GRF", "C-LRK"], "L06": ["C-LRK", "C-ORL"],
                  "L07": ["C-LRK", "C-PNC"], "L08": ["C-LRK", "C-GRF"], "L09": ["C-VAN"], "L10": ["C-VAN"],
                  "L11": ["C-LRK"], "L12": ["C-LRK", "C-VAN", "C-SBR"], "L13": ["C-SBR", "C-LRK"], "L14": ["C-LRK"]}
_KG = {"FTL": (6000, 16000), "LTL": (600, 3500), "parcel": (2000, 6000), "final_mile": (200, 900),
       "drayage": (8000, 20000), "ocean": (4000, 20000)}


def _log_tables() -> dict[str, list[dict]]:
    rng = random.Random(1106)
    net = _fx("log_network")
    lanes = {l["lane_id"]: l for l in net["lanes"]}
    shippers = {s["shipper_id"]: s for s in net["shippers"]}
    sites = net["sites"]
    start = dt.date(2026, 5, 11)
    hist, perf = [], []
    n = 0
    carry = {lid: 0.0 for lid in lanes}
    for week in range(26):
        wk = start + dt.timedelta(days=7 * week)
        recent = wk >= dt.date(2026, 10, 5)
        for lid, l in lanes.items():
            base_ot = l["on_time_30d_pct"] / 100
            p_ot = base_ot if recent or l["mode"] == "ocean" else \
                min(0.985, base_ot + (0.05 if lid in ("L07", "L04", "L11") else 0.02))
            rows = []
            count = max(1, round(_LANE_VOLUME[lid] * (0.85 + 0.3 * rng.random())))
            carry[lid] += count * (1 - p_ot)
            n_late = int(carry[lid])
            carry[lid] -= n_late
            late_idx = set(rng.sample(range(count), min(n_late, count)))
            for k in range(count):
                n += 1
                ship = wk + dt.timedelta(days=rng.randint(0, 6))
                if ship > dt.date(2026, 11, 1):
                    continue
                transit_h = l["transit_days"] * 24
                promised = dt.datetime.combine(ship, dt.time(8)) + dt.timedelta(hours=transit_h + 6)
                late = k in late_idx
                delay = rng.uniform(2, 30 if l["mode"] != "ocean" else 120) if late else -rng.uniform(0, 5)
                delivered = promised + dt.timedelta(hours=delay)
                if delivered > dt.datetime(2026, 11, 5, 23, 0):
                    continue
                kg_lo, kg_hi = _KG.get(l["mode"], (500, 5000))
                kg = round(rng.uniform(kg_lo, kg_hi), 1)
                sh = shippers[rng.choice(_LANE_SHIPPERS[lid])]
                code = None
                if late:
                    code = rng.choices(["WX", "CAP", "DC", "MECH", "PORT", "DOCS"],
                                       weights=[3, 3, 2, 2, 4 if l["mode"] in ("ocean", "drayage") else 0, 1])[0]
                row = {"shipment_id": f"HLV-H{ship:%y%m%d}-{n:05d}", "shipper_id": sh["shipper_id"],
                       "shipper_name": sh["name"], "shipper_tier": sh["tier"], "lane_id": lid,
                       "origin": sites.get(l["origin"], l["origin"]), "destination": sites.get(l["destination"], l["destination"]),
                       "mode": l["mode"], "carrier": l["carrier"], "ship_date": ship.isoformat(),
                       "promised_at": _fmt(promised), "eta_at": _fmt(delivered), "delivered_at": _fmt(delivered),
                       "status": "delivered", "on_time": not late, "delay_hours": round(max(delay, 0.0), 1),
                       "exception_code": code, "value_usd": round(kg * rng.uniform(4, 40), 2), "weight_kg": kg,
                       "temperature_controlled": sh["shipper_id"] == "C-ORL"}
                hist.append(row)
                rows.append((row, transit_h + delay, kg))
            if rows:
                late_rows = [r for r in rows if not r[0]["on_time"]]
                perf.append({"week_start": wk.isoformat(), "lane_id": lid,
                             "origin": sites.get(l["origin"], l["origin"]),
                             "destination": sites.get(l["destination"], l["destination"]), "mode": l["mode"],
                             "carrier": l["carrier"], "shipments": len(rows),
                             "on_time_pct": round(100 * (len(rows) - len(late_rows)) / len(rows), 1),
                             "avg_transit_days": round(sum(r[1] for r in rows) / len(rows) / 24, 2),
                             "avg_delay_hours": round(sum(r[0]["delay_hours"] for r in late_rows) / len(late_rows), 1)
                             if late_rows else 0.0,
                             "cost_per_kg_usd": round(l["cost_per_kg_usd"] * (0.95 + 0.1 * rng.random()), 3),
                             "claims": sum(1 for _ in rows if rng.random() < 0.01)})
    active = []
    for s in _fx("log_shipments")["shipments"]:
        l, sh = lanes[s["lane_id"]], shippers[s["shipper_id"]]
        delay = (_ts(s["eta"]) - _ts(s["promised"])).total_seconds() / 3600
        active.append({"shipment_id": s["shipment_id"], "shipper_id": sh["shipper_id"], "shipper_name": sh["name"],
                       "shipper_tier": sh["tier"], "lane_id": s["lane_id"],
                       "origin": sites.get(l["origin"], l["origin"]), "destination": s["consignee"], "mode": s["mode"],
                       "carrier": s["carrier"], "ship_date": s["ship_date"], "promised_at": _fmt(_ts(s["promised"])),
                       "eta_at": _fmt(_ts(s["eta"])), "delivered_at": None, "status": s["status"], "on_time": None,
                       "delay_hours": round(max(delay, 0.0), 1), "exception_code": s["exception_code"],
                       "value_usd": float(s["value_usd"]), "weight_kg": float(s["weight_kg"]),
                       "temperature_controlled": s["temperature_controlled"]})
    demand = []
    items = _fx("log_items")["items"]
    d0 = dt.date(2026, 8, 14)
    for it in items:
        days = [d0 + dt.timedelta(days=i) for i in range(84)]
        vals = []
        for i, d in enumerate(days):
            mu = it["recent_14d_mean"] if i >= 70 else it["daily_demand_mean"]
            wk_factor = 0.75 if d.weekday() == 6 and it["dc"] != "BRK" else 1.0
            vals.append(max(0, round(rng.gauss(mu * wk_factor, it["daily_demand_sd"]))))
        for i, d in enumerate(days):
            short = it["dc"] == "AVD" and it["sku"] in ("CVX-PRO16", "KAI-NOVA") and i >= 78
            shipped = round(vals[i] * (0.4 if short else 1.0))
            demand.append({"date": d.isoformat(), "dc": it["dc"], "sku": it["sku"], "units_demanded": vals[i],
                           "units_shipped": shipped, "stockout": shipped < vals[i]})
    return {"log_shipments": hist + active, "log_lane_performance": perf, "log_dc_demand_daily": demand}


def tables() -> dict[str, list[dict]]:
    out = {"tel_sla_contracts": _tel_contracts(), "tel_incidents": _tel_incidents(),
           "tel_campaign_results": _tel_campaigns()}
    out.update(_ret_tables())
    out.update(_log_tables())
    return out


if __name__ == "__main__":
    for name, rows in tables().items():
        print(f"{name}: {len(rows)} rows")

"""Enterprise realm tools — telco, retail and logistics/manufacturing (synthetic, deterministic).

Fictional world shared by every fixture in this module:
  * Kestrava Telecom      — telco with enterprise SLAs, consumer marketing and multi-market localisation (tel_*)
  * Larkspur Home & Tech  — 16-store consumer-electronics and home retailer with an online channel (ret_*)
  * Halvard Logistics     — 3PL running Larkspur's DCs and shipping for Vantor Appliances and others (log_*)
  * Vantor Appliances     — small-appliance manufacturer, Brackwater plant (log_spc_check, log_defect_pareto)
The demo clock is fixed at 2026-11-06 so every sample is reproducible.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from statistics import NormalDist, mean, pstdev

from ._base import err, fixture, hive_tool, ok

TODAY = dt.date(2026, 11, 6)
TEL_NOW = dt.datetime(2026, 11, 6, 10, 0)
LOG_NOW = dt.datetime(2026, 11, 6, 7, 0)


def _ts(s: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(s) if s else None


def _d(s: str | None) -> dt.date | None:
    return dt.date.fromisoformat(s[:10]) if s else None


def _csv(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _sid(prefix: str, *parts: object) -> str:
    return prefix + hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:6].upper()


# =====================================================================================================================
# TELCO — Kestrava Telecom: SLA Sentinel, Campaign Analyst, Content Creator, Localization
# =====================================================================================================================


def _tel_customer(query: str) -> dict | None:
    q = (query or "").strip().lower()
    for c in fixture("tel_sla_contracts")["customers"]:
        if q and (q == c["customer_id"].lower() or q in c["name"].lower()
                  or any(q == s["service_id"].lower() for s in c["services"])):
            return c
    return None


def _month(month: str) -> tuple[dt.datetime, dt.datetime, int]:
    y, m = (int(x) for x in month.split("-"))
    start = dt.datetime(y, m, 1)
    end = dt.datetime(y + (m == 12), m % 12 + 1, 1)
    return start, end, int((end - start).total_seconds() // 60)


def _tel_service_month(cust: dict, svc: dict, month: str) -> dict:
    sla = fixture("tel_sla_contracts")
    tier = sla["tiers"][cust["tier"]]
    start, end, minutes = _month(month)
    in_progress = start <= TEL_NOW < end
    target = tier["availability_target_pct"]
    budget = svc["sites"] * minutes * (100 - target) / 100
    incs = [i for i in fixture("tel_incidents")["incidents"]
            if i["service_id"] == svc["service_id"] and start <= _ts(i["opened"]) < end]
    consumed = sum(i["outage_minutes"] * i["sites_affected"] for i in incs if not i["excluded"])
    avail = 100 * (1 - consumed / (svc["sites"] * minutes))
    rows = []
    for i in incs:
        restored = _ts(i["restored"])
        hours = ((restored or TEL_NOW) - _ts(i["opened"])).total_seconds() / 3600
        target_h = tier["restore_hours"][i["severity"]]
        notify_ok = None
        if i["severity"] == "P1" and i["customer_notified_after_min"] is not None:
            notify_ok = i["customer_notified_after_min"] <= tier["notify_minutes_P1"]
        rfo_due = None
        if restored and i["severity"] in ("P1", "P2") and not i["rfo_sent"]:
            d, n = restored.date(), 0
            while n < 5:
                d += dt.timedelta(days=1)
                n += d.weekday() < 5
            rfo_due = d.isoformat()
        rows.append({"incident_id": i["incident_id"], "severity": i["severity"], "opened": i["opened"],
                     "restored": i["restored"], "status": i["status"], "cause": i["cause"],
                     "site_minutes": i["outage_minutes"] * i["sites_affected"], "excluded": i["excluded"],
                     "exclusion_reason": i["exclusion_reason"], "restore_hours": round(hours, 2),
                     "restore_target_hours": target_h,
                     "restore_met": None if not restored else (hours <= target_h or i["excluded"]),
                     "p1_notify_met": notify_ok, "rfo_sent": i["rfo_sent"], "rfo_due": rfo_due})
    return {"service_id": svc["service_id"], "type": svc["type"], "sites": svc["sites"], "mrc_usd": svc["mrc_usd"],
            "availability_target_pct": target, "budget_site_minutes": round(budget, 1),
            "consumed_site_minutes": consumed, "budget_used_pct": round(100 * consumed / budget, 1) if budget else None,
            "availability_pct": round(avail, 4), "month_in_progress": in_progress,
            "status": "breached" if consumed > budget else "within_target", "incidents": rows}


@hive_tool("enterprise")
def tel_sla_status(customer: str, month: str = "2026-11") -> dict:
    """Show an enterprise customer's SLA position for a month: availability vs target, downtime budget and incidents.

    Availability is site-weighted (outage minutes x sites affected) against the contract tier target. Excluded
    incidents (planned maintenance, customer-caused) are listed but do not consume the budget.

    Args:
        customer: Customer id (e.g. 'ENT-1004'), service id (e.g. 'SVC-1004-P5G') or part of the name
            (e.g. 'Tidewater').
        month: Month as YYYY-MM. '2026-11' is in progress (as of 2026-11-06 10:00); '2026-10' is closed.

    Returns:
        Tier targets, per-service budget used, availability, status (breached / within_target) and incidents with
        restore-time and P1-notification compliance and any RFO (reason-for-outage) report due.
    """
    cust = _tel_customer(customer)
    if not cust:
        return err(f"unknown customer {customer!r}",
                   available=[f"{c['customer_id']} {c['name']}" for c in fixture("tel_sla_contracts")["customers"]])
    try:
        services = [_tel_service_month(cust, s, month) for s in cust["services"]]
    except ValueError:
        return err("month must be YYYY-MM, e.g. '2026-10'")
    tier = fixture("tel_sla_contracts")["tiers"][cust["tier"]]
    open_incs = [i for s in services for i in s["incidents"] if i["status"] == "open"]
    return ok(customer_id=cust["customer_id"], customer=cust["name"], tier=cust["tier"],
              account_manager=cust["account_manager"], customer_contact=cust["customer_contact"], month=month,
              as_of=TEL_NOW.isoformat(timespec="minutes"), tier_terms=tier, services=services,
              open_incidents=len(open_incs),
              rfo_reports_due=[{"incident_id": i["incident_id"], "due": i["rfo_due"]}
                               for s in services for i in s["incidents"] if i["rfo_due"]])


def _poisson_tail(lam: float, k: int) -> float:
    if k <= 0:
        return 1.0
    return max(0.0, 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k)))


@hive_tool("enterprise")
def tel_sla_breach_forecast(customer: str = "") -> dict:
    """Forecast which enterprise services will breach their SLA by the end of the current month (November 2026).

    Blends each service's 90-day incident history (60%) with this month's run-rate (40%) and uses a Poisson model
    of further incidents to estimate the probability that the remaining downtime budget is exhausted.

    Args:
        customer: Optional customer id, service id or name. Empty = every service in the portfolio, ranked.

    Returns:
        Per service: budget used, projected month-end consumption, breach probability, status (breached / at_risk /
        watch / healthy) and the action the SLA policy requires.
    """
    sla = fixture("tel_sla_contracts")
    custs = sla["customers"]
    if customer:
        c = _tel_customer(customer)
        if not c:
            return err(f"unknown customer {customer!r}")
        custs = [c]
    month = "2026-11"
    start, end, minutes = _month(month)
    elapsed_days = (TEL_NOW - start).total_seconds() / 86400
    remaining_days = (end - TEL_NOW).total_seconds() / 86400
    th = sla["risk_thresholds"]
    out = []
    for c in custs:
        for s in c["services"]:
            m = _tel_service_month(c, s, month)
            h = s["history_90d"]
            hist_daily = h["incidents"] / 90 * h["avg_site_minutes"]
            run_daily = m["consumed_site_minutes"] / elapsed_days
            blended = 0.6 * hist_daily + 0.4 * run_daily
            remaining_budget = m["budget_site_minutes"] - m["consumed_site_minutes"]
            lam = blended * remaining_days / h["avg_site_minutes"]
            if remaining_budget < 0:
                p, status = 1.0, "breached"
            else:
                p = _poisson_tail(lam, math.ceil(remaining_budget / h["avg_site_minutes"]) or 1)
                status = "at_risk" if p >= th["at_risk_probability"] else "watch" if p >= th["watch_probability"] \
                    else "healthy"
            action = {
                "breached": "Accrue service credit, send RFO for each P1/P2 within 5 business days, account-manager call",
                "at_risk": "Send proactive at-risk notice to the customer and AM; NOC watch list; freeze non-urgent changes",
                "watch": "NOC watch list; review open changes and spares",
                "healthy": "No action",
            }[status]
            out.append({"customer_id": c["customer_id"], "customer": c["name"], "tier": c["tier"],
                        "service_id": s["service_id"], "type": s["type"],
                        "budget_site_minutes": m["budget_site_minutes"],
                        "consumed_site_minutes": m["consumed_site_minutes"], "budget_used_pct": m["budget_used_pct"],
                        "projected_month_end_site_minutes": round(m["consumed_site_minutes"] + blended * remaining_days),
                        "expected_further_incidents": round(lam, 2), "breach_probability": round(p, 2),
                        "status": status, "required_action": action, "mrc_usd": s["mrc_usd"]})
    order = {"breached": 0, "at_risk": 1, "watch": 2, "healthy": 3}
    out.sort(key=lambda r: (order[r["status"]], -r["breach_probability"], -r["mrc_usd"]))
    return ok(month=month, as_of=TEL_NOW.isoformat(timespec="minutes"), elapsed_days=round(elapsed_days, 2),
              remaining_days=round(remaining_days, 2), services=out,
              counts={k: sum(1 for r in out if r["status"] == k) for k in order},
              method="P(breach) = P(N >= ceil(remaining budget / avg incident size)), N ~ Poisson(blended rate x days left)")


@hive_tool("enterprise")
def tel_sla_credit(customer: str, month: str = "2026-10") -> dict:
    """Calculate SLA service credits for an enterprise customer for a month, per the Kestrava credit schedule.

    Credit = availability band credit (5/10/20/30% of the service MRC by shortfall) + 3% per P1 and 1% per P2
    restored late + 1% per P1 notified late (incident credits max 10%), capped by tier (Platinum 40%, Gold 30%,
    Silver 20%).

    Args:
        customer: Customer id, service id or part of the name (e.g. 'Calder').
        month: Month as YYYY-MM. Closed months give final credits; '2026-11' gives a provisional accrual.

    Returns:
        Per-service credit breakdown (band, incident credits, cap), credit in USD, total, and how it is applied
        (automatic for Platinum, claim within 30 days for Gold/Silver).
    """
    cust = _tel_customer(customer)
    if not cust:
        return err(f"unknown customer {customer!r}")
    sla = fixture("tel_sla_contracts")
    tier = sla["tiers"][cust["tier"]]
    try:
        _, end, _ = _month(month)
    except ValueError:
        return err("month must be YYYY-MM")
    lines = []
    for s in cust["services"]:
        m = _tel_service_month(cust, s, month)
        shortfall = max(0.0, m["availability_target_pct"] - m["availability_pct"])
        band = 0
        if shortfall > 0:
            band = next(b["credit_pct"] for b in sla["availability_credit_bands"] if shortfall <= b["shortfall_pp_up_to"])
        restore_misses = [i for i in m["incidents"] if i["restore_met"] is False]
        notify_misses = [i for i in m["incidents"] if i["p1_notify_met"] is False]
        inc_pct = sum(sla["restore_miss_credit_pct"][i["severity"]] for i in restore_misses) \
            + sla["notify_miss_credit_pct"] * len(notify_misses)
        inc_pct = min(inc_pct, sla["incident_credit_max_pct"])
        total_pct = min(band + inc_pct, tier["credit_cap_pct"])
        lines.append({"service_id": s["service_id"], "type": s["type"], "mrc_usd": s["mrc_usd"],
                      "availability_pct": m["availability_pct"], "target_pct": m["availability_target_pct"],
                      "shortfall_pp": round(shortfall, 4), "band_credit_pct": band,
                      "late_restores": [i["incident_id"] for i in restore_misses],
                      "late_p1_notifications": [i["incident_id"] for i in notify_misses],
                      "incident_credit_pct": inc_pct, "cap_pct": tier["credit_cap_pct"], "credit_pct": total_pct,
                      "credit_usd": round(s["mrc_usd"] * total_pct / 100, 2)})
    total = round(sum(l["credit_usd"] for l in lines), 2)
    provisional = end > TEL_NOW
    return ok(customer_id=cust["customer_id"], customer=cust["name"], tier=cust["tier"], month=month,
              provisional=provisional, services=lines, total_credit_usd=total,
              application=("Applied automatically on the next invoice (Platinum proactive credit)"
                           if tier["proactive_credit"] else
                           f"Customer must claim by {(end + dt.timedelta(days=30)).date().isoformat()} (30 days after month end)"))


def _two_prop_p(x1: int, n1: int, x2: int, n2: int) -> float:
    if min(n1, n2) == 0:
        return 1.0
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) or 1e-9
    z = abs(x1 / n1 - x2 / n2) / se
    return round(2 * (1 - NormalDist().cdf(z)), 4)


def _campaign_eval(c: dict, arpu: dict) -> dict:
    t, ctl, cost = c["treatment"], c["control"], c["costs"]
    total_cost = cost["offer_cost_per_accept_usd"] * t["accepted"] + cost["contact_cost_per_reach_usd"] * t["reached"] \
        + cost["fixed_usd"]
    if c["type"] == "churn_save":
        rt, rc = t["churned"] / t["targeted"], ctl["churned"] / ctl["targeted"]
        uplift = rc - rt
        incremental = uplift * t["targeted"]
        p = _two_prop_p(t["churned"], t["targeted"], ctl["churned"], ctl["targeted"])
        outcome = {"treatment_churn_pct": round(100 * rt, 2), "control_churn_pct": round(100 * rc, 2),
                   "uplift_pp": round(100 * uplift, 2), "incremental_saves": round(incremental)}
    else:
        rt, rc = t["accepted"] / t["targeted"], ctl["accepted"] / ctl["targeted"]
        uplift = rt - rc
        incremental = uplift * t["targeted"]
        p = _two_prop_p(t["accepted"], t["targeted"], ctl["accepted"], ctl["targeted"])
        outcome = {"treatment_conversion_pct": round(100 * rt, 2), "control_conversion_pct": round(100 * rc, 2),
                   "uplift_pp": round(100 * uplift, 2), "incremental_conversions": round(incremental)}
    value = max(incremental, 0) * arpu[c["product"]] * c["value_months"] * c["survival_factor"]
    roi = (value - total_cost) / total_cost * 100
    return {
        "campaign_id": c["campaign_id"], "name": c["name"], "type": c["type"], "offer": c["offer"],
        "channels": c["channels"], "window": f"{c['start']} to {c['end']}", "read": c["read"],
        "funnel": {"targeted": t["targeted"], "reached": t["reached"], "reach_pct": round(100 * t["reached"] / t["targeted"], 1),
                   "responded": t["responded"], "response_pct": round(100 * t["responded"] / t["reached"], 1),
                   "accepted": t["accepted"], "accept_pct_of_reached": round(100 * t["accepted"] / t["reached"], 1)},
        **outcome, "p_value": p, "significant_95": p < 0.05,
        "total_cost_usd": round(total_cost), "value_12m_usd": round(value), "roi_pct": round(roi, 1),
        "cost_per_incremental_usd": round(total_cost / incremental) if incremental > 0 else None,
        "accepted_per_incremental": round(t["accepted"] / incremental, 1) if incremental > 0 else None,
    }


@hive_tool("enterprise")
def tel_campaign_performance(campaign_id: str = "") -> dict:
    """Measure Kestrava marketing campaigns against their holdout control: reach, response, uplift, ROI.

    Args:
        campaign_id: Campaign id (e.g. 'CMP-2610-SAVE02'). Empty = portfolio summary of all campaigns ranked by ROI.

    Returns:
        Funnel (reach, response, acceptance), treatment vs control outcome, uplift in percentage points,
        incremental saves or conversions, p-value, cost, 12-month value, ROI and 'accepted_per_incremental' (how many
        offers were given away per truly incremental outcome — high values mean the offer subsidises customers who
        would have stayed or bought anyway).
    """
    data = fixture("tel_campaigns")
    rows = [_campaign_eval(c, data["arpu_usd"]) for c in data["campaigns"]]
    if campaign_id:
        hit = next((r for r in rows if r["campaign_id"].lower() == campaign_id.strip().lower()), None)
        if not hit:
            return err(f"unknown campaign {campaign_id!r}", available=[r["campaign_id"] for r in rows])
        flags = []
        if not hit["significant_95"]:
            flags.append("Uplift not statistically significant at 95% - extend the read or enlarge the holdout")
        if (hit["accepted_per_incremental"] or 0) > 5:
            flags.append("Offer mostly subsidises customers who would have stayed: target by uplift model, not churn score")
        if hit["roi_pct"] < 0:
            flags.append("Negative ROI on 12-month value")
        if "early" in hit["read"]:
            flags.append("Early read: results will move; do not scale yet")
        return ok(campaign=hit, flags=flags, measurement="Holdout control; two-proportion z-test")
    rows.sort(key=lambda r: -r["roi_pct"])
    return ok(campaigns=[{k: r[k] for k in ("campaign_id", "name", "type", "uplift_pp", "significant_95", "roi_pct",
                                            "cost_per_incremental_usd", "accepted_per_incremental")} for r in rows])


def _nbo_eligible(o: dict, s: dict, g: dict) -> tuple[bool, str]:
    oid = o["offer_id"]
    mobile = bool(s["mobile_plan"])
    if o["kind"].startswith("retention") and s["last_retention_offer_days_ago"] is not None \
            and s["last_retention_offer_days_ago"] < g["retention_offer_cooldown_days"]:
        return False, f"Retention offer cooldown: last offer {s['last_retention_offer_days_ago']} days ago (< {g['retention_offer_cooldown_days']})"
    if oid in ("OFF-MOB15", "OFF-DEVICE200", "OFF-ONE-BUNDLE") and s["arrears_days"] > g["no_discounts_if_arrears_days_over"]:
        return False, f"No discount offers while {s['arrears_days']} days in arrears (> {g['no_discounts_if_arrears_days_over']})"
    rules = {
        "OFF-SPEED2G": (s["fiber_plan"] == "1 Gig" and s["tenure_months"] >= 12 and s["arrears_usd"] == 0,
                        "Needs Fiber 1 Gig, tenure >= 12 months and no arrears"),
        "OFF-MOB15": (mobile and 0 < s["contract_end_days"] <= 60, "Needs mobile postpaid with contract ending within 60 days"),
        "OFF-DATA50": (mobile and (s["data_usage_pct_of_cap"] or 0) >= 80, "Needs a capped mobile plan used >= 80%"),
        "OFF-ONE-BUNDLE": (mobile and s["in_5g_home_coverage"] and not s["fiber_plan"] and not s["five_g_home"],
                           "Needs mobile, 5G Home coverage and no Kestrava home broadband"),
        "OFF-DEVICE200": (mobile and (s["device_age_months"] or 0) >= 24 and s["tenure_months"] >= 24
                          and s["churn_score"] >= 0.5, "Needs mobile, device >= 24 months, tenure >= 24, churn >= 0.5"),
        "OFF-STREAM6": (bool(s["fiber_plan"]) or s["five_g_home"], "Needs fiber or 5G Home"),
        "OFF-PAYPLAN": (s["arrears_usd"] > 0 and s["churn_score"] >= 0.5, "Needs arrears and churn score >= 0.5"),
    }
    good, why = rules[oid]
    return good, ("eligible" if good else why)


@hive_tool("enterprise")
def tel_next_best_offer(subscriber_id: str) -> dict:
    """Rank the next-best offer for a Kestrava subscriber by expected value, applying eligibility and guardrails.

    Expected value = P(accept) x (retained value + new revenue - offer cost), where retained value is
    churn score x 60% save rate x 12 months of ARPU. Guardrails: 180-day retention-offer cooldown, no discounts
    above 60 days of arrears, offer cost <= 30% of annual ARPU.

    Args:
        subscriber_id: Subscriber id, e.g. 'SUB-40211'.

    Returns:
        Subscriber profile, ranked eligible offers with expected value and reasons, ineligible offers with the rule
        that blocked them, and the recommendation (or 'no offer' when nothing has positive value).
    """
    data = fixture("tel_offers")
    s = next((x for x in data["subscribers"] if x["subscriber_id"].lower() == subscriber_id.strip().lower()), None)
    if not s:
        return err(f"unknown subscriber {subscriber_id!r}", available=[x["subscriber_id"] for x in data["subscribers"]])
    g = data["guardrails"]
    annual = s["arpu_usd"] * 12
    eligible, blocked = [], []
    for o in data["offers"]:
        good, why = _nbo_eligible(o, s, g)
        cost = o.get("cost_usd")
        if cost is None:
            cost = o["cost_pct_of_mobile_arpu_12m"] / 100 * 58 * max(1, s["mobile_lines"]) * 12
        if good and cost > g["max_offer_cost_pct_of_annual_arpu"] / 100 * annual:
            good, why = False, f"Offer cost ${cost:.0f} exceeds 30% of annual ARPU (${annual * 0.3:.0f})"
        if not good:
            blocked.append({"offer_id": o["offer_id"], "name": o["name"], "reason": why})
            continue
        p = o["base_accept"] * (1 + 0.5 * (s["churn_score"] - 0.5))
        if o["kind"] == "cross_sell":
            p = o["base_accept"] * (0.8 + 0.04 * (s["nps"] or 5))
        retained = s["churn_score"] * g["save_rate_if_accepted"] * annual if o["kind"] != "cross_sell" else 0
        value = retained + o["new_monthly_usd"] * 12 * 0.8
        ev = p * (value - cost)
        eligible.append({"offer_id": o["offer_id"], "name": o["name"], "kind": o["kind"],
                         "p_accept": round(p, 3), "offer_cost_usd": round(cost, 2), "value_if_accepted_usd": round(value),
                         "expected_value_usd": round(ev, 2)})
    eligible.sort(key=lambda r: -r["expected_value_usd"])
    best = eligible[0] if eligible and eligible[0]["expected_value_usd"] > 0 else None
    rec = best["offer_id"] if best else "NO_OFFER"
    note = ("Low churn risk: send a loyalty thank-you, no incentive" if s["churn_score"] < 0.3 and not best
            else "Nothing eligible with positive value: route to care / payment support" if not best else
            f"Lead with {best['name']}; keep #2 as fallback if declined")
    return ok(subscriber=s, recommendation=rec, note=note, eligible=eligible, ineligible=blocked)


_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆↔-↪]")


def _labelled(text: str) -> dict:
    parts, cur = {}, "body"
    for line in text.splitlines():
        m = re.match(r"\s*(subject|preheader|title|body|cta|headline)\s*:\s*(.*)", line, re.I)
        if m:
            cur = m.group(1).lower()
            parts[cur] = m.group(2)
        else:
            parts[cur] = (parts.get(cur, "") + "\n" + line).strip()
    return parts


@hive_tool("enterprise")
def tel_check_copy_compliance(text: str, channel: str = "email") -> dict:
    """Check Kestrava marketing copy against the brand voice and legal rules for a channel (the brand critic).

    Checks length limits, emoji and exclamation limits, banned words, product-name spelling, unsubstantiated
    claims (fastest, #1...), required lines (fair use for 'unlimited', T&Cs/taxes with prices, SMS opt-out),
    call-to-action, ALL-CAPS shouting, sentence length and 'you' vs 'we' focus.

    Args:
        text: The copy. For email use labelled lines 'Subject:', 'Preheader:', 'Body:', 'CTA:'; for push an optional
            'Title:' line followed by the body.
        channel: One of 'email', 'push', 'sms', 'social'.

    Returns:
        pass (no blocker/major issues), score 0-100, issues (severity, rule, detail, fix) and the channel rules.
        Copy written in Spanish is checked with the Spanish equivalents of the legal lines, CTA verbs and banned
        terms (tel_brand.json "spanish").
    """
    brand = fixture("tel_brand")
    es = brand.get("spanish", {})
    ch = channel.strip().lower()
    rules = brand["channels"].get(ch)
    if not rules:
        return err(f"unknown channel {channel!r}", channels=sorted(brand["channels"]))
    if len(text.strip()) < 5:
        return err("text is empty")
    parts = _labelled(text)
    issues = []

    def add(sev, rule, detail, fix):
        issues.append({"severity": sev, "rule": rule, "detail": detail, "fix": fix})

    low = text.lower()
    if ch == "email":
        subj, pre = parts.get("subject", ""), parts.get("preheader", "")
        if not subj:
            add("major", "structure", "No 'Subject:' line", "Add a subject line (<= 50 characters)")
        elif len(subj) > rules["subject_max_chars"]:
            add("major", "length", f"Subject is {len(subj)} chars (max {rules['subject_max_chars']})", "Shorten the subject")
        if pre and len(pre) > rules["preheader_max_chars"]:
            add("minor", "length", f"Preheader is {len(pre)} chars (max {rules['preheader_max_chars']})", "Shorten the preheader")
        words = len(re.findall(r"\w+", parts.get("body", text)))
        if words > rules["body_max_words"]:
            add("major", "length", f"Body is {words} words (max {rules['body_max_words']})", "Cut to the key benefit and one proof point")
    else:
        body = parts.get("body", text) if ch == "push" else text
        if ch == "push" and len(parts.get("title", "")) > rules["title_max_chars"]:
            add("major", "length", f"Push title is {len(parts['title'])} chars (max {rules['title_max_chars']})", "Shorten the title")
        if len(body) > rules["max_chars"]:
            add("blocker" if ch == "sms" else "major", "length", f"{len(body)} chars (max {rules['max_chars']})",
                "Shorten; move detail to the landing page")
    emojis = len(_EMOJI.findall(text))
    if emojis > rules["max_emojis"]:
        add("major", "emoji", f"{emojis} emoji (max {rules['max_emojis']} on {ch})", "Remove extra emoji")
    if text.count("!") > rules["max_exclamations"]:
        add("minor", "tone", f"{text.count('!')} exclamation marks (max {rules['max_exclamations']})", "Keep one at most")
    spanish = bool(es) and len(re.findall(r"\b(el|la|los|las|tu|tus|con|para|por|sin|de|del|y|en|al|más|mes|que|hoy)\b",
                                          low)) >= 3
    es_lines = es.get("conditional_lines", {})
    for term in brand["banned_terms"] + es.get("banned_terms", []):
        if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", low):
            add("blocker", "banned_term", f"Banned term '{term}'", "Replace with a concrete, provable benefit")
    for wrong, right in brand["misspellings"].items():
        if re.search(r"(?<!\w)" + re.escape(wrong) + r"(?!\w)", text):
            add("major", "product_name", f"'{wrong}' should be '{right}'", f"Use '{right}'")
    for claim in brand["claims_needing_source"] + es.get("claims_needing_source", []):
        if claim in low and not ("*" in text and ("source:" in low or "fuente:" in low)):
            add("blocker", "substantiation", f"Claim '{claim}' without a footnote and 'Source:' line",
                "Add '*' and a 'Source:' line, or remove the claim")
    fair_es = es_lines.get("unlimited", "").lower().rstrip(".")
    if re.search(r"\bunlimited\b", low) and "fair use policy applies" not in low:
        add("blocker", "legal_line", "'Unlimited' without 'Fair use policy applies.'", "Add the fair-use line")
    if fair_es and re.search(r"\bilimitad[oa]s?\b", low) and fair_es not in low and "fair use policy applies" not in low:
        add("blocker", "legal_line", f"'Ilimitado' without '{es_lines['unlimited']}'", "Add the fair-use line")
    if re.search(r"\$\s?\d", text):
        key = "price_email" if ch == "email" else "price_short"
        need, need_es = brand["conditional_lines"][key], es_lines.get(key, "")
        if need.split(".")[0].lower() not in low and not (need_es and need_es.split(".")[0].lower() in low):
            line = need_es if spanish and need_es else need
            add("major", "legal_line", f"Price shown without '{line}'", f"Add '{line}'")
    opt_es = es.get("sms_opt_out", "")
    if ch == "sms" and rules.get("required_text", "").lower() not in low and not (opt_es and opt_es.lower() in low):
        line = opt_es if spanish and opt_es else "Reply STOP to opt out"
        add("blocker", "opt_out", f"SMS without '{line}'", f"Append '{line}'")
    verbs = brand["cta_verbs"] + es.get("cta_verbs", [])
    if rules.get("needs_cta") and not any(re.search(rf"(?<!\w){v}(?!\w)", text, re.I) for v in verbs):
        shown = es.get("cta_verbs", [])[:6] if spanish else brand["cta_verbs"][:6]
        add("major", "cta", "No call to action", f"Start the CTA with one of: {', '.join(shown)}")
    shouts = [w for w in re.findall(r"\b[A-Z]{4,}\b", text) if w not in brand["allowed_caps"]]
    if shouts:
        add("minor", "tone", f"ALL-CAPS words: {', '.join(sorted(set(shouts))[:5])}", "Use sentence case")
    if ch == "social":
        tags = re.findall(r"#\w+", text)
        if len(tags) > rules["max_hashtags"]:
            add("minor", "hashtags", f"{len(tags)} hashtags (max {rules['max_hashtags']})", "Keep the 1-3 most relevant")
    sentences = [s for s in re.split(r"[.!?]+", parts.get("body", text)) if s.strip()]
    if sentences and mean(len(s.split()) for s in sentences) > 20:
        add("minor", "readability", "Average sentence longer than 20 words", "Split long sentences")
    you = len(re.findall(r"\byou(r|rs)?\b", low))
    we = len(re.findall(r"\b(we|our|us)\b(?!\$)", low))   # 'US$65' is a price, not 'us'
    if spanish:
        you += len(re.findall(r"\b(tú|tu|tus|te|ti)\b", low))
        we += len(re.findall(r"\b(nosotros|nuestro|nuestra|nuestros|nuestras)\b", low))
    if we > you:
        add("minor", "voice", f"'we/our' ({we}) outnumbers 'you/your' ({you})", "Rewrite from the customer's side")
    sev = {"blocker": 25, "major": 10, "minor": 3}
    score = max(0, 100 - sum(sev[i["severity"]] for i in issues))
    passed = not any(i["severity"] in ("blocker", "major") for i in issues)
    return ok(channel=ch, passed=passed, score=score, issues=issues, rules=rules,
              voice=brand["voice"], product_names=brand["product_names"])


@hive_tool("enterprise")
def tel_localization_glossary(locale: str, terms: str = "") -> dict:
    """Get the Kestrava localisation profile for a target locale: glossary, do-not-translate list, tone and legal lines.

    Args:
        locale: Target locale: 'es-419', 'es-ES', 'pt-BR', 'fr-CA' or 'fr-FR'.
        terms: Optional comma-separated English terms to look up (e.g. 'unlimited, router'). Empty = full glossary.

    Returns:
        Formality rule, price format example, legal lines (taxes, terms, fair use, SMS opt-out), anglicisms to avoid,
        cultural notes, do-not-translate terms and approved translations.
    """
    data = fixture("tel_localization")
    loc = data["locales"].get(locale.strip())
    if not loc:
        return err(f"unsupported locale {locale!r}", supported=sorted(data["locales"]))
    wanted = {t.lower() for t in _csv(terms)}
    gloss = [{"en": g["en"], "approved": g[locale.strip()]} for g in data["glossary"]
             if not wanted or g["en"].lower() in wanted]
    return ok(locale=locale.strip(), profile=loc, do_not_translate=data["do_not_translate"], glossary=gloss,
              channel_limits=data["channel_limits"],
              rules=["Never convert prices: use the local price sheet for the market",
                     "Keep product names exactly as in do_not_translate",
                     "Translate meaning and tone, not word by word; keep the CTA as an imperative"])


@hive_tool("enterprise")
def tel_check_localized_copy(text: str, locale: str, channel: str = "", source_text: str = "") -> dict:
    """Check localised Kestrava copy for glossary, tone, legal, format and cultural issues (the localisation reviewer).

    Args:
        text: The translated copy.
        locale: Target locale ('es-419', 'es-ES', 'pt-BR', 'fr-CA', 'fr-FR').
        channel: Optional channel for length limits ('push', 'sms', 'social', 'email_subject').
        source_text: Optional English source, used to check do-not-translate terms and length expansion.

    Returns:
        pass flag, score, issues (severity, rule, detail, fix) and cultural flags for the market.
    """
    data = fixture("tel_localization")
    loc_id = locale.strip()
    loc = data["locales"].get(loc_id)
    if not loc:
        return err(f"unsupported locale {locale!r}", supported=sorted(data["locales"]))
    if len(text.strip()) < 3:
        return err("text is empty")
    issues, low, padded = [], text.lower(), f" {text.lower()} "

    def add(sev, rule, detail, fix):
        issues.append({"severity": sev, "rule": rule, "detail": detail, "fix": fix})

    if source_text:
        for term in sorted(data["do_not_translate"], key=len, reverse=True):
            if term in source_text and term not in text:
                add("blocker", "do_not_translate", f"'{term}' missing or translated", f"Keep '{term}' verbatim")
                break
    for m in loc["avoid_markers"]:
        if m.lower() in padded:
            add("major", "formality", f"Found '{m.strip()}' - {loc['formality_note']}", "Rewrite in the required form of address")
    for en, repl in loc["anglicisms"].items():
        if re.search(r"(?<!\w)" + re.escape(en.lower()) + r"(?!\w)", low):
            add("major", "anglicism", f"Anglicism '{en}' in {loc_id}", f"Use '{repl}'")
    cultural = []
    for term, why in loc["flag_terms"].items():
        if term.lower() in low:
            cultural.append({"term": term, "why": why})
            add("major", "cultural", f"'{term}': {why}", "Replace with market-appropriate wording or imagery")
    has_price = bool(re.search(r"\d", text) and re.search(r"[$€]|R\$|US\$", text))
    if has_price:
        if loc_id in ("es-ES", "fr-FR") and "$" in text:
            add("blocker", "price", "Dollar price in a euro market", "Use the local price sheet (e.g. " + loc["price_example"] + ")")
        if loc_id == "pt-BR" and re.search(r"(?<!R)\$", text):
            add("blocker", "price", "Price not in reais", "Use the local price sheet (e.g. " + loc["price_example"] + ")")
        if loc_id == "fr-CA" and re.search(r"\$\s?\d", text):
            add("minor", "price_format", "fr-CA writes the amount before the symbol", "Write e.g. " + loc["price_example"])
        if loc_id == "es-419" and re.search(r"(?<!US)\$\s?\d", text):
            add("minor", "price_format", "Use 'US$' to avoid confusion with local pesos", "Write e.g. " + loc["price_example"])
        key = loc["taxes_line"].split()[0].lower().strip(".")
        if key not in low:
            add("major", "legal_line", f"Price without the tax line '{loc['taxes_line']}'", f"Add '{loc['taxes_line']}'")
        if loc_id in ("es-ES", "pt-BR", "fr-FR") and re.search(r"no incluid|não inclus|nao inclus|hors taxes|\bht\b", low):
            add("blocker", "legal_line", "Prices in this market must be shown tax-inclusive", f"Use '{loc['taxes_line']}'")
    if loc["decimal"] == "," and re.search(r"\d+\.\d{2}\b", text):
        add("minor", "number_format", "Decimal point used; this locale uses a decimal comma", "Write e.g. 49,90")
    for a, b in re.findall(r"\b(\d{1,2})/(\d{1,2})\b", text):
        if int(a) <= 12 < int(b):
            add("major", "date_format", f"US-style date {a}/{b}", "Use DD/MM or write the month name")
    if re.search(r"ilimitad|illimit", low) and loc["fair_use_line"].split()[0].lower() not in low:
        add("major", "legal_line", "Unlimited without the fair-use line", f"Add '{loc['fair_use_line']}'")
    if channel.strip().lower() == "sms" and loc["sms_opt_out"].split()[1].lower() not in low:
        add("blocker", "opt_out", "SMS without the local opt-out", f"Append '{loc['sms_opt_out']}'")
    limit = data["channel_limits"].get(channel.strip().lower())
    if limit and len(text) > limit:
        add("major", "length", f"{len(text)} chars (limit {limit} for {channel})", "Shorten; keep the CTA")
    if source_text and len(text) > len(source_text) * (loc["expansion"] + 0.15):
        add("minor", "expansion", f"{len(text) / len(source_text):.2f}x the source length (expected ~{loc['expansion']}x)",
            "Tighten the translation")
    english = len(re.findall(r"\b(the|and|your|with|now|get|for|you|today|offer)\b", low))
    if english >= 3:
        add("major", "untranslated", f"{english} English words left in the text", "Translate remaining fragments")
    sev = {"blocker": 25, "major": 10, "minor": 3}
    score = max(0, 100 - sum(sev[i["severity"]] for i in issues))
    return ok(locale=loc_id, passed=not any(i["severity"] in ("blocker", "major") for i in issues), score=score,
              issues=issues, cultural_flags=cultural, season_note=loc["season_note"])


# =====================================================================================================================
# RETAIL — Larkspur Home & Tech: Inventory Risk, Fulfillment, Promotions, Inventory Campaign, Support, CES Concierge
# =====================================================================================================================


def _cat() -> dict:
    return fixture("ret_catalog")


def _prod(sku: str) -> dict | None:
    s = (sku or "").strip().upper()
    return next((p for p in _cat()["products"] if p["sku"] == s), None)


def _stores() -> dict:
    return {s["store_id"]: s for s in _cat()["stores"]}


def _cover(p: dict) -> float:
    return round(p["on_hand"] / p["ads_28d"], 1) if p["ads_28d"] > 0 else 999.0


def _risk(pos: dict, prod: dict, th: dict) -> str:
    cov = _cover(pos)
    inbound_soon = pos["on_order"] and pos["on_order_eta"] and _d(pos["on_order_eta"]) <= TODAY + dt.timedelta(days=int(cov))
    if cov < th["stockout_critical_days"]:
        return "stockout_critical" if not inbound_soon else "stockout_covered_by_inbound"
    if cov < th["stockout_days"]:
        return "stockout" if not inbound_soon else "stockout_covered_by_inbound"
    if prod["eol_date"]:
        days_left = (_d(prod["eol_date"]) - TODAY).days
        if cov > max(th["eol_overstock_days"], days_left):
            return "overstock_eol"
    if cov > th["overstock_critical_days"]:
        return "overstock_critical"
    if cov > th["overstock_days"]:
        return "overstock"
    return "healthy"


@hive_tool("enterprise")
def ret_stock_risk_scan(sku: str = "", store_id: str = "", region: str = "", category: str = "", risk: str = "all",
                        limit: int = 25) -> dict:
    """Scan Larkspur store inventory for stock-out and overstock risk using days of cover (on hand / 28-day sales).

    Thresholds: stock-out < 7 days (critical < 3), overstock > 60 days (critical > 90); end-of-life SKUs are
    overstocked when cover exceeds the days left before end of life.

    Args:
        sku: Optional SKU filter (e.g. 'LUM-55Q8').
        store_id: Optional store filter (e.g. 'S05').
        region: Optional region: 'North', 'Coast', 'Central' or 'South'.
        category: Optional category (e.g. 'Audio', 'TV & Home Theater').
        risk: 'stockout', 'overstock' or 'all'.
        limit: Maximum store-SKU rows to return (1-100).

    Returns:
        Store-SKU positions with cover and risk, a per-SKU network summary (cover, excess units and value at cost,
        lost-margin-per-day at risk) and totals.
    """
    inv = fixture("ret_inventory")
    th = inv["thresholds"]
    stores = _stores()
    scoped = []
    for pos in inv["positions"]:
        prod = _prod(pos["sku"])
        st = stores[pos["store_id"]]
        if sku and pos["sku"] != sku.strip().upper():
            continue
        if store_id and pos["store_id"] != store_id.strip().upper():
            continue
        if region and st["region"].lower() != region.strip().lower():
            continue
        if category and prod["category"].lower() != category.strip().lower():
            continue
        scoped.append({"store_id": pos["store_id"], "store": st["name"], "region": st["region"], "sku": pos["sku"],
                       "product": prod["name"], "on_hand": pos["on_hand"], "on_order": pos["on_order"],
                       "on_order_eta": pos["on_order_eta"], "ads_28d": pos["ads_28d"], "days_of_cover": _cover(pos),
                       "risk": _risk(pos, prod, th)})
    rows = [x for x in scoped if risk not in ("stockout", "overstock") or x["risk"].startswith(risk)]
    if not rows:
        return err("no positions match the filters")
    sev = {"stockout_critical": 0, "stockout": 1, "overstock_eol": 2, "overstock_critical": 3, "overstock": 4,
           "stockout_covered_by_inbound": 5, "healthy": 6}
    rows.sort(key=lambda x: (sev[x["risk"]], x["days_of_cover"] if x["risk"].startswith("stockout") else -x["days_of_cover"]))
    matched = {x["sku"] for x in rows}
    summary = {}
    for x in scoped:
        if x["sku"] not in matched:
            continue
        p = _prod(x["sku"])
        s = summary.setdefault(x["sku"], {"sku": x["sku"], "product": p["name"], "category": p["category"],
                                          "lifecycle": p["lifecycle"], "eol_date": p["eol_date"],
                                          "on_hand": 0, "ads": 0.0, "stockout_stores": 0, "overstock_stores": 0,
                                          "excess_units": 0, "lost_margin_per_day_usd": 0.0})
        margin = p["list_price_usd"] - p["unit_cost_usd"]
        s["on_hand"] += x["on_hand"]
        s["ads"] += x["ads_28d"]
        if x["risk"] in ("stockout", "stockout_critical"):
            s["stockout_stores"] += 1
            s["lost_margin_per_day_usd"] += round(x["ads_28d"] * margin, 2)
        s["overstock_stores"] += x["risk"].startswith("overstock")
        s["excess_units"] += max(0, round(x["on_hand"] - th["overstock_days"] * x["ads_28d"]))
    for s in summary.values():
        p = _prod(s["sku"])
        s["ads"] = round(s["ads"], 2)
        s["network_cover_days"] = round(s["on_hand"] / s["ads"], 1) if s["ads"] else None
        s["excess_value_at_cost_usd"] = round(s["excess_units"] * p["unit_cost_usd"])
        s["unit_margin_usd"] = p["list_price_usd"] - p["unit_cost_usd"]
        s["lost_margin_per_day_usd"] = round(s["lost_margin_per_day_usd"], 2)
    key = (lambda s: -s["lost_margin_per_day_usd"]) if risk == "stockout" else (lambda s: -s["excess_value_at_cost_usd"])
    top = sorted(summary.values(), key=key)
    limit = max(1, min(int(limit), 100))
    return ok(snapshot_date=inv["snapshot_date"], thresholds=th, positions=rows[:limit], total_matches=len(rows),
              sku_summary=top[:15],
              totals={"stockout_positions": sum(1 for r in rows if r["risk"] in ("stockout", "stockout_critical")),
                      "overstock_positions": sum(1 for r in rows if r["risk"].startswith("overstock")),
                      "excess_value_at_cost_usd": sum(s["excess_value_at_cost_usd"] for s in summary.values()),
                      "lost_margin_per_day_usd": round(sum(s["lost_margin_per_day_usd"] for s in summary.values()), 2)})


@hive_tool("enterprise")
def ret_recommend_transfers(sku: str, region: str = "", max_transfers: int = 8) -> dict:
    """Recommend store-to-store transfers for one SKU: move stock from overstocked donors to stores at stock-out risk.

    Receivers (< 10 days cover) are filled to 21 days; donors (> 40 days cover) keep at least 30 days. Same-region
    donors are used first (2-day transfer), then cross-region (4 days, higher cost per unit).

    Args:
        sku: SKU to rebalance, e.g. 'AUR-NC90'.
        region: Optional region to restrict receivers to.
        max_transfers: Maximum transfer lines to return.

    Returns:
        Transfer lines (from, to, units, cost, lead days, margin protected), unfilled demand and totals.
    """
    prod = _prod(sku)
    if not prod:
        return err(f"unknown sku {sku!r}")
    inv = fixture("ret_inventory")
    th = inv["thresholds"]
    stores = _stores()
    cat = _cat()
    pos = [p for p in inv["positions"] if p["sku"] == prod["sku"]]
    receivers, donors = [], []
    for p in pos:
        cov = _cover(p)
        inbound = p["on_order"] if p["on_order_eta"] and _d(p["on_order_eta"]) <= TODAY + dt.timedelta(days=7) else 0
        if cov < 10 and (not region or stores[p["store_id"]]["region"].lower() == region.lower()):
            need = round(th["transfer_target_cover_days"] * p["ads_28d"] - p["on_hand"] - inbound)
            if need >= th["min_transfer_units"]:
                receivers.append({**p, "need": need, "cover": cov})
        elif cov > 40:
            spare = p["on_hand"] - math.ceil(th["donor_floor_days"] * p["ads_28d"])
            if spare >= th["min_transfer_units"]:
                donors.append({**p, "spare": spare, "cover": cov})
    receivers.sort(key=lambda r: r["cover"])
    lines = []
    margin = prod["list_price_usd"] - prod["unit_cost_usd"]
    costs = cat["transfer_cost_per_unit_usd"][prod["ship_class"]]
    for r in receivers:
        rreg = stores[r["store_id"]]["region"]
        for same in (True, False):
            cands = sorted([d for d in donors if (stores[d["store_id"]]["region"] == rreg) == same and d["spare"] > 0],
                           key=lambda d: -d["cover"])
            for d in cands:
                if r["need"] <= 0:
                    break
                qty = min(r["need"], d["spare"])
                if qty < th["min_transfer_units"]:
                    continue
                unit_cost = costs["same_region" if same else "cross_region"]
                lines.append({"from_store": d["store_id"], "from_cover_days": d["cover"], "to_store": r["store_id"],
                              "to_cover_days": r["cover"], "units": qty, "same_region": same,
                              "lead_days": cat["transfer_lead_days"]["same_region" if same else "cross_region"],
                              "transfer_cost_usd": round(qty * unit_cost, 2),
                              "margin_protected_usd": round(qty * margin, 2)})
                d["spare"] -= qty
                r["need"] -= qty
    lines = lines[:max(1, int(max_transfers))]
    unfilled = [{"store_id": r["store_id"], "units_short": r["need"]} for r in receivers if r["need"] > 0]
    return ok(sku=prod["sku"], product=prod["name"], transfers=lines, unfilled=unfilled,
              totals={"units": sum(l["units"] for l in lines),
                      "transfer_cost_usd": round(sum(l["transfer_cost_usd"] for l in lines), 2),
                      "margin_protected_usd": round(sum(l["margin_protected_usd"] for l in lines), 2)},
              note="Transfers are proposals; store managers confirm pick lists in the store system (simulated).")


def _order(order_id: str = "", email: str = "") -> dict | None:
    for o in fixture("ret_orders")["orders"]:
        if order_id and o["order_id"].lower() == order_id.strip().lower():
            return o
        if email and o["email"].lower() == email.strip().lower():
            return o
    return None


def _dc_stock(sku: str) -> dict:
    out = {}
    for it in fixture("log_items")["items"]:
        if it["sku"] == sku and it["dc"] in ("AVD", "RMD"):
            out[f"DC-{it['dc']}"] = max(0, it["on_hand"] - it["backorders"])
    return out


@hive_tool("enterprise")
def ret_order_lookup(order_id: str = "", email: str = "") -> dict:
    """Look up a Larkspur online order by order id or customer email: lines, shipments, status and exceptions.

    Args:
        order_id: Order id, e.g. 'ORD-L-480117'.
        email: Customer email (used when the order id is unknown).

    Returns:
        Customer, loyalty tier, lines with product names, CarePlus plans, shipments (node, carrier, tracking,
        promised and delivered dates, exception with new ETA and days late) and the order total.
    """
    o = _order(order_id, email)
    if not o:
        return err("order not found", hint="try an id like ORD-L-480117")
    lines = [{**l, "product": (_prod(l["sku"]) or {}).get("name", l["sku"]),
              "category": (_prod(l["sku"]) or {}).get("category")} for l in o["lines"]]
    ships = []
    for s in o["shipments"]:
        x = dict(s)
        ex = s.get("exception")
        if ex:
            eta = _d(ex.get("new_eta"))
            x["days_late"] = (eta - _d(s["promised"])).days if eta else max(0, (TODAY - _d(s["promised"])).days)
        ships.append(x)
    return ok(order={**{k: v for k, v in o.items() if k not in ("lines", "shipments")}, "lines": lines,
                     "shipments": ships, "total_usd": round(sum(l["price"] * l["qty"] for l in o["lines"]), 2)},
              as_of=fixture("ret_orders")["as_of"])


_EXC_ACTION = {
    "backorder": "Offer ship-from-store (see stock_elsewhere) or the new date; let the customer choose; apply delay credit",
    "split_shipment": "Escalate the store pick; if not picked by 14:00 reallocate to another store with stock",
    "carrier_delay": "Proactive delay notice with the new ETA; no reship while in transit; apply delay credit",
    "address_issue": "Contact the customer to confirm the address; express clock pauses until confirmed",
    "damaged_in_transit": "Ship a replacement now (reported within 48 h); open a carrier damage claim",
    "failed_delivery": "Offer a new delivery slot or pickup at the nearest store; hold at depot up to 5 days",
    "dc_backlog": "Check carrier options for an upgrade so the express promise holds; notify if it cannot",
}


@hive_tool("enterprise")
def ret_fulfillment_exceptions(exception_type: str = "", region: str = "") -> dict:
    """List open Larkspur order-fulfilment exceptions with lateness, notification deadline and next best action.

    Args:
        exception_type: Optional filter: backorder, split_shipment, carrier_delay, address_issue, damaged_in_transit,
            failed_delivery, dc_backlog.
        region: Optional ship-to region filter.

    Returns:
        Exceptions ranked by days late and customer tier, each with notify-by time (2 h after detection),
        recommended action, policy compensation and stock available elsewhere for backorders/splits.
    """
    data = fixture("ret_orders")
    pol = data["policy"]
    inv = fixture("ret_inventory")["positions"]
    out = []
    for o in data["orders"]:
        if region and o["region"].lower() != region.strip().lower():
            continue
        for s in o["shipments"]:
            ex = s.get("exception")
            if not ex or (exception_type and ex["type"] != exception_type.strip().lower()):
                continue
            eta = _d(ex.get("new_eta"))
            late = (eta - _d(s["promised"])).days if eta else max(0, (TODAY - _d(s["promised"])).days)
            comp = None
            for c in pol["compensation"]:
                if late >= c["min_days_late"] or (s["service"] == "express" and late >= 1 and c["min_days_late"] == 5):
                    comp = c
            row = {"order_id": o["order_id"], "customer": o["customer"], "loyalty": o["loyalty"], "region": o["region"],
                   "shipment": s["shipment"], "type": ex["type"], "detail": ex["detail"], "service": s["service"],
                   "promised": s["promised"], "new_eta": ex.get("new_eta"), "days_late": late,
                   "detected": ex["detected"],
                   "notify_by": (_ts(ex["detected"]) + dt.timedelta(hours=pol["notify_within_hours"])).isoformat(timespec="minutes"),
                   "order_value_usd": round(sum(l["price"] * l["qty"] for l in o["lines"]), 2),
                   "recommended_action": _EXC_ACTION.get(ex["type"], "Review"),
                   "compensation": comp}
            if ex["type"] in ("backorder", "split_shipment"):
                skus = s.get("skus") or [l["sku"] for l in o["lines"]]
                stores = _stores()
                cands = [{"node": p["store_id"], "region": stores[p["store_id"]]["region"], "sku": p["sku"],
                          "on_hand": p["on_hand"]} for p in inv if p["sku"] in skus and p["on_hand"] >= 2
                         and p["store_id"] != s["node"]]
                cands.sort(key=lambda c: (c["region"] != o["region"], -c["on_hand"]))
                row["stock_elsewhere"] = cands[:4]
            out.append(row)
    tier = {"Rewards Gold": 0, "Rewards": 1, "None": 2}
    out.sort(key=lambda r: (-r["days_late"], tier.get(r["loyalty"], 3)))
    return ok(as_of=data["as_of"], exceptions=out, count=len(out),
              by_type={t: sum(1 for r in out if r["type"] == t) for t in sorted({r["type"] for r in out})})


@hive_tool("enterprise")
def ret_carrier_options(order_id: str, ship_from: str = "") -> dict:
    """Quote carrier options for the open shipment of an order: cost, delivery date, promise check and recommendation.

    Policy: choose the cheapest option that meets the promise with >= 92% on-time; if none meets it, the fastest
    reliable option. Storm advisories add days on affected regions.

    Args:
        order_id: Order id, e.g. 'ORD-L-480532'.
        ship_from: Optional node to ship from instead of the planned one: 'DC-AVD', 'DC-RMD' or a store id ('S09').

    Returns:
        Shipment weight, origin/destination regions, carrier quotes (service, cost, est. delivery, meets promise,
        on-time %), and the recommended option with the reason.
    """
    o = _order(order_id)
    if not o:
        return err(f"order {order_id!r} not found")
    data = fixture("ret_orders")
    ship = next((s for s in o["shipments"] if s["status"] not in ("delivered", "ready_for_pickup")), None)
    if not ship:
        return err("order has no open shipment to quote")
    skus = ship.get("skus") or [l["sku"] for l in o["lines"]]
    weight = sum((_prod(l["sku"]) or {}).get("weight_lb", 2) * l["qty"] for l in o["lines"] if l["sku"] in skus)
    node = (ship_from or ship["node"]).strip().upper()
    stores = _stores()
    origin_region = data["nodes"][node]["region"] if node in data["nodes"] else stores.get(node, {}).get("region")
    if not origin_region:
        return err(f"unknown ship_from node {ship_from!r}")
    promised = _d(ship["promised"])
    quotes = []
    for c in data["carriers"]:
        if weight > c["max_lb"] or o["region"] not in c["regions"] or origin_region not in c["regions"]:
            continue
        for svc, s in c["services"].items():
            days = s["days"] + (1 if origin_region != o["region"] and svc == "same_day" else 0)
            if svc == "same_day" and origin_region != o["region"]:
                continue
            adv = c.get("advisory")
            if adv and o["region"] in adv["regions"]:
                days += adv["extra_days"]
            eta = TODAY + dt.timedelta(days=max(days, 0))
            if eta.weekday() == 6:
                eta += dt.timedelta(days=1)
            quotes.append({"carrier": c["carrier"], "service": svc, "cost_usd": round(s["base"] + s["per_lb"] * weight, 2),
                           "est_delivery": eta.isoformat(), "meets_promise": eta <= promised,
                           "on_time_30d_pct": c["on_time_30d_pct"],
                           "advisory": adv["detail"] if adv and o["region"] in adv["regions"] else None})
    if not quotes:
        return err("no carrier can serve this shipment", weight_lb=weight)
    reliable = [q for q in quotes if q["on_time_30d_pct"] >= data["policy"]["min_on_time_pct"]]
    meeting = [q for q in reliable if q["meets_promise"]]
    if meeting:
        best, why = min(meeting, key=lambda q: q["cost_usd"]), "Cheapest reliable option that meets the promise"
    elif reliable:
        best, why = min(reliable, key=lambda q: (q["est_delivery"], q["cost_usd"])), \
            "Promise cannot be met; fastest reliable option (notify the customer)"
    else:
        best, why = min(quotes, key=lambda q: q["est_delivery"]), "No reliable carrier; fastest available"
    quotes.sort(key=lambda q: (q["est_delivery"], q["cost_usd"]))
    return ok(order_id=o["order_id"], shipment=ship["shipment"], ship_from=node, origin_region=origin_region,
              destination_region=o["region"], weight_lb=round(weight, 1), promised=ship["promised"],
              quotes=quotes, recommended=best, reason=why)


@hive_tool("enterprise", kind="action")
def ret_notify_customer(order_id: str, message: str, channel: str = "email", credit_usd: float = 0.0) -> dict:
    """Send a customer notification about an order, optionally with a goodwill credit. Simulated — nothing is sent.

    Credits up to $25 are auto-approved; larger credits are queued for supervisor approval and the message is held.

    Args:
        order_id: Order id the message is about.
        message: Full customer-facing message text.
        channel: 'email' or 'sms'.
        credit_usd: Goodwill credit to apply (0 for none).

    Returns:
        Message id, delivery_status (sent / pending_approval), recipient, credit decision and checks on the message.
    """
    o = _order(order_id)
    if not o:
        return err(f"order {order_id!r} not found")
    if channel not in ("email", "sms"):
        return err("channel must be 'email' or 'sms'")
    if len(message.strip()) < 20:
        return err("message too short")
    checks = []
    if o["order_id"] not in message:
        checks.append("Message does not mention the order id")
    if channel == "sms" and len(message) > 320:
        checks.append("SMS longer than 2 segments (320 chars)")
    limit = fixture("ret_orders")["policy"]["auto_credit_limit_usd"]
    pending = credit_usd > limit
    return ok(message_id=_sid("MSG-L-", o["order_id"], message[:40]), delivery_status="pending_approval" if pending else "sent",
              recipient=o["email"] if channel == "email" else "mobile on file", channel=channel,
              credit={"usd": credit_usd, "approved": not pending and credit_usd > 0,
                      "needs_approval": pending, "auto_limit_usd": limit}, checks=checks, simulated=True)


def _careplus(price: float) -> dict:
    cp = _cat()["careplus"]
    band = next(b for b in cp["bands"] if price <= b["max_price"])
    return {"2_year_usd": band["y2"], "3_year_usd": band["y3"]}


@hive_tool("enterprise")
def ret_return_eligibility(order_id: str, sku: str, reason: str = "changed_mind", opened: bool = True) -> dict:
    """Decide whether an item can be returned or exchanged under the Larkspur returns policy, with fees and next steps.

    Rules: 30-day window (15 days for opened TVs 55 in and larger, opened computers and opened consoles), +15 days
    for Rewards Gold, holiday purchases (Nov 1-Dec 24) returnable until Jan 31; 14-day dead-on-arrival rule;
    transit damage reported within 48 h; restocking fee on some opened items unless defective/damaged or Gold;
    goodwill up to 7 days past the window needs Returns Desk L2.

    Args:
        order_id: Order id, e.g. 'ORD-L-480117'.
        sku: The SKU being returned, e.g. 'LUM-65Q8'.
        reason: changed_mind, defective, damaged_in_transit, wrong_item or not_as_described.
        opened: Whether the box was opened.

    Returns:
        Decision (refund / exchange / warranty / not_eligible / escalate), window end, days left, restocking fee,
        refund amount, return method, product advisories, replacement stock and escalation queue when needed.
    """
    o = _order(order_id)
    if not o:
        return err(f"order {order_id!r} not found")
    line = next((l for l in o["lines"] if l["sku"] == sku.strip().upper()), None)
    if not line:
        return err(f"{sku} is not on order {o['order_id']}", skus=[l["sku"] for l in o["lines"]])
    reason = reason.strip().lower()
    if reason not in ("changed_mind", "defective", "damaged_in_transit", "wrong_item", "not_as_described"):
        return err("reason must be changed_mind, defective, damaged_in_transit, wrong_item or not_as_described")
    pol = fixture("ret_policies")
    prod = _prod(line["sku"])
    ship = next((s for s in o["shipments"] if line["sku"] in (s.get("skus") or [l["sku"] for l in o["lines"]])), None)
    delivered = _d(ship.get("delivered")) if ship else None
    if not delivered:
        return err("item not delivered yet - use fulfilment options instead", shipment_status=ship["status"] if ship else None)
    key = None
    if opened:
        if prod["category"] == "TV & Home Theater" and prod["specs"].get("screen_in", 0) >= 55:
            key = "TV & Home Theater_55in_plus_opened"
        elif prod["category"] == "Computing" and prod["sku"].startswith("CVX-") and "laptop" in prod["name"].lower():
            key = "Computing_opened"
        elif prod["sku"] == "KAI-NOVA":
            key = "Gaming_console_opened"
    window = pol["return_window_days"].get(key, pol["return_window_days"]["default"]) if key else \
        pol["return_window_days"]["default"]
    window += pol["loyalty_extra_days"].get(o["loyalty"], 0)
    window_end = delivered + dt.timedelta(days=window)
    hol = pol["holiday_extension"]
    if _d(hol["purchased_from"]) <= _d(o["placed"]) <= _d(hol["purchased_to"]):
        window_end = max(window_end, _d(hol["return_by"]))
    days_since = (TODAY - delivered).days
    days_left = (window_end - TODAY).days
    fee_pct = pol["restocking_fee_pct"].get(key, 0) if key else 0
    if reason in pol["fee_waived_reasons"] or o["loyalty"] in pol["fee_waived_loyalty"]:
        fee_pct = 0
    price = line["price"] * line["qty"]
    decision, notes, escalation = None, [], None
    if reason == "damaged_in_transit":
        ex = ship.get("exception") or {}
        reported = _ts(ex.get("detected")) or dt.datetime.combine(TODAY, dt.time(9))
        hours = (reported - dt.datetime.combine(delivered, dt.time(18))).total_seconds() / 3600
        if hours <= pol["transit_damage_report_hours"]:
            decision = "replacement_or_refund"
            notes.append(f"Reported {max(hours, 0):.0f} h after delivery (limit 48 h): ship replacement, open carrier claim")
        else:
            decision = "escalate"
            escalation = pol["escalation"]
            notes.append("Damage reported after 48 h: Returns Desk L2 decides")
    elif reason == "defective" and days_since <= pol["doa_days"]:
        decision = "exchange_or_refund"
        notes.append(f"Dead on arrival (day {days_since} of {pol['doa_days']}): no fee, exchange or refund")
    elif days_left >= 0:
        decision = "exchange_or_refund" if reason != "changed_mind" else "refund"
        if reason == "defective":
            notes.append("Defective within the return window: exchange preferred, no restocking fee")
    elif reason == "defective":
        months = _cat()["careplus"]["manufacturer_warranty_months"].get(prod["brand"],
                                                                         _cat()["careplus"]["manufacturer_warranty_months"]["default"])
        decision = "warranty_claim"
        notes.append(f"Outside the return window: {prod['brand']} warranty {months} months"
                     + ("; CarePlus on this order covers repair/replacement" if o["careplus"] else ""))
    elif -days_left <= pol["goodwill_days_past_window"] and o["loyalty"] == "Rewards Gold":
        decision = "escalate"
        escalation = pol["escalation"]
        notes.append(f"{-days_left} days past the window: goodwill possible for Gold with L2 approval")
    else:
        decision = "not_eligible"
        notes.append(f"Return window ended {window_end.isoformat()} ({-days_left} days ago); suggest trade-in or CarePlus")
    if prod["sku"] in pol["product_advisories"]:
        notes.append(pol["product_advisories"][prod["sku"]])
    fee = round(price * fee_pct / 100, 2) if decision in ("refund", "exchange_or_refund") and reason == "changed_mind" else 0.0
    method = ("Halvard Final Mile pickup (white-glove item)" if prod["ship_class"] == "white_glove"
              else "Any Larkspur store, or prepaid return label" + (" (order over $50)" if price > 50 else ""))
    stock = {**_dc_stock(prod["sku"]),
             **{p["store_id"]: p["on_hand"] for p in fixture("ret_inventory")["positions"]
                if p["sku"] == prod["sku"] and _stores()[p["store_id"]]["region"] == o["region"] and p["on_hand"] > 0}}
    return ok(order_id=o["order_id"], sku=prod["sku"], product=prod["name"], loyalty=o["loyalty"], reason=reason,
              delivered=delivered.isoformat(), days_since_delivery=days_since, window_days=window,
              window_end=window_end.isoformat(), days_left=days_left, decision=decision, restocking_fee_pct=fee_pct
              if reason == "changed_mind" else 0, restocking_fee_usd=fee, refund_usd=round(price - fee, 2)
              if decision in ("refund", "exchange_or_refund", "replacement_or_refund") else 0.0,
              return_method=method, notes=notes, escalation=escalation,
              replacement_stock=stock if decision in ("exchange_or_refund", "replacement_or_refund") else None,
              refund_timing="Original payment 3-5 business days; store credit instant")


_SPEC_KEYS = ["screen_in", "panel", "refresh_hz", "hdmi21_ports", "earc", "vrr", "hdr", "channels", "atmos", "ram_gb",
              "storage_gb", "weight_kg", "battery_h", "usb4", "wifi", "anc", "matter", "coverage_sqft", "output"]


@hive_tool("enterprise")
def ret_product_compare(skus: str = "", category: str = "", max_price: float = 0.0, must_have: str = "") -> dict:
    """Compare consumer-electronics products from the Larkspur catalog side by side (specs, price, stock, CarePlus).

    Args:
        skus: Comma-separated SKUs to compare (e.g. 'LUM-55Q8,LUM-55U6,LUM-65Q8'). Leave empty to search.
        category: Category to search when no SKUs are given (e.g. 'TV & Home Theater', 'Computing', 'Audio').
        max_price: Optional maximum list price in USD (0 = no limit).
        must_have: Optional comma-separated features that must appear in the specs (e.g. 'earc, dolby vision').

    Returns:
        Up to 6 products with key specs, price, network stock, CarePlus 2/3-year prices, lifecycle notes
        (end of life / successor) and the matched features.
    """
    prods = _cat()["products"]
    note = None
    if skus:
        known = [p["sku"] for p in prods]
        wanted, fixed = [], {}
        for s in (x.upper() for x in _csv(skus)):
            if s not in known:   # tolerate a mistyped brand prefix only (e.g. 'CRV-AIR14' -> 'CVX-AIR14')
                same = [k for k in known if k.split("-", 1)[-1] == s.split("-", 1)[-1]]
                if len(same) == 1:
                    fixed[s] = same[0]
                    s = same[0]
            wanted.append(s)
        missing = [s for s in wanted if s not in known]
        if missing:
            return err(f"unknown SKUs {missing}", hint="Search by category to get the SKUs.",
                       categories=sorted({p["category"] for p in prods}))
        sel = [p for p in prods if p["sku"] in wanted]
        if fixed:
            note = f"SKUs resolved to the closest catalog SKU: {fixed}"
    else:
        if not category:
            return err("pass skus or a category", categories=sorted({p["category"] for p in prods}))
        sel = [p for p in prods if p["category"].lower() == category.strip().lower()]
    if max_price:
        sel = [p for p in sel if p["list_price_usd"] <= max_price]
    feats = [f.lower() for f in _csv(must_have)]

    def norm(x: str) -> str:
        return re.sub(r"[\s._\-]", "", x.lower())

    def has(p, f):
        parts = [k if v is True else f"{k} {v}" for k, v in p["specs"].items() if v not in (False, 0, None)]
        return norm(f) in norm(" ".join([p["name"], p["brand"], *parts]))

    if feats and not skus:   # named SKUs are always compared; features then show as matched / missing per product
        pool = sel
        sel = [p for p in sel if all(has(p, f) for f in feats)]
        if not sel and pool:  # nothing has every feature: show the closest matches and what each one lacks
            best = max(sum(has(p, f) for f in feats) for p in pool)
            sel = [p for p in pool if sum(has(p, f) for f in feats) == best]
            note = ("No product has every must_have feature; showing the closest matches with missing_features. "
                    "Spec words that match: earc, hdmi21, vrr, usb4, dolby atmos, wifi 7, matter.")
    if not sel:
        return err("no products match")
    inv = fixture("ret_inventory")["positions"]
    rows = []
    for p in sel[:6]:
        units = sum(x["on_hand"] for x in inv if x["sku"] == p["sku"])
        stores_with = sum(1 for x in inv if x["sku"] == p["sku"] and x["on_hand"] > 0)
        life = None
        if p["lifecycle"] == "end_of_life":
            life = f"End of life {p['eol_date']}; successor {p['successor']}"
        elif p["lifecycle"] == "seasonal":
            life = f"Seasonal item ({p['specs'].get('season', 'seasonal')})"
        rows.append({"sku": p["sku"], "name": p["name"], "brand": p["brand"], "price_usd": p["list_price_usd"],
                     "key_specs": {k: p["specs"][k] for k in _SPEC_KEYS if k in p["specs"]},
                     "other_specs": {k: v for k, v in p["specs"].items() if k not in _SPEC_KEYS},
                     "stock": {"units": units, "stores_with_stock": stores_with}, "careplus": _careplus(p["list_price_usd"]),
                     "lifecycle_note": life,
                     **({"missing_features": [f for f in feats if not has(p, f)]} if feats and (skus or note) else {})})
    return ok(products=rows, matched_features=feats, count=len(sel), **({"note": note} if note else {}))


def _compat(a: dict, b: dict) -> tuple[str, str]:
    sa, sb = a["specs"], b["specs"]
    pair = {a["sku"], b["sku"]}
    tv = a if "screen_in" in sa and a["category"] == "TV & Home Theater" else b if "screen_in" in sb and \
        b["category"] == "TV & Home Theater" else None
    other = b if tv is a else a
    if "AUR-SUB300" in pair:
        mate = b if a["sku"] == "AUR-SUB300" else a
        return ("compatible", "Pairs wirelessly with the SB700") if mate["sku"] == "AUR-SB700" else \
            ("not_compatible", "The SUB300 only pairs with the Aurion SB700 soundbar")
    if tv and other["sku"] == "AUR-SB700":
        if tv["specs"].get("earc"):
            return "compatible", "Full Dolby Atmos and lossless audio over HDMI eARC"
        return "partial", "TV has ARC only: works, but Dolby Digital 5.1 only (no Atmos/lossless)"
    if tv and other["sku"] == "KAI-NOVA":
        if tv["specs"].get("hdmi21_ports", 0) >= 1 and tv["specs"].get("refresh_hz", 60) >= 120:
            return "compatible", "4K120 with VRR on an HDMI 2.1 port; use an Ultra High Speed cable (LUM-HDMI21)"
        return "partial", "Works at 4K60 only: TV has no HDMI 2.1 / 120 Hz input"
    if tv and other["sku"] == "LUM-HDMI21":
        return "compatible", "Needed for 4K120/VRR and eARC at full bandwidth"
    if "CVX-DOCK4" in pair:
        lap = b if a["sku"] == "CVX-DOCK4" else a
        if lap["category"] != "Computing" or "laptop" not in lap["name"].lower():
            return "not_applicable", "Dock is for laptops"
        return ("compatible", "Dual 4K60 displays over USB4") if lap["specs"].get("usb4") else \
            ("partial", "Single 4K60 display (USB-C 3.2 host, no USB4)")
    if "WAV-MESH7" in pair:
        cl = b if a["sku"] == "WAV-MESH7" else a
        wifi = str(cl["specs"].get("wifi", ""))
        if not wifi:
            return "not_applicable", "No Wi-Fi radio"
        return ("compatible", "Wi-Fi 7 client: gets multi-link (MLO) speed and latency") if "7" in wifi else \
            ("compatible", f"Backward compatible ({wifi}); Wi-Fi 7 gains need a Wi-Fi 7 client")
    if "HRT-HUB" in pair:
        dev = b if a["sku"] == "HRT-HUB" else a
        if dev["brand"] == "Hearthly" or dev["specs"].get("matter"):
            note = "Matter device controlled by the hub"
            if dev["specs"].get("connectivity") == "Thread":
                note += "; hub is the Thread border router"
            if dev["specs"].get("c_wire"):
                note += f"; C-wire: {dev['specs']['c_wire']}"
            return "compatible", note
    if {"KAI-CTRL", "KAI-HS7"} & pair and "KAI-NOVA" in pair:
        return "compatible", "Native Kairo accessory"
    return "no_dependency", "No known dependency between these products"


@hive_tool("enterprise")
def ret_check_compatibility(sku: str, with_skus: str = "") -> dict:
    """Check compatibility between a product and other products, and list bundles, CarePlus and warranty for it.

    Args:
        sku: The main product SKU (e.g. 'LUM-55U6').
        with_skus: Comma-separated SKUs to check against (e.g. 'AUR-SB700,KAI-NOVA'). Empty = check against the
            usual attach products for this SKU.

    Returns:
        Per pair: verdict (compatible / partial / not_compatible / no_dependency) with the reason; bundles that
        include the SKU; CarePlus prices and manufacturer warranty.
    """
    p = _prod(sku)
    if not p:
        return err(f"unknown sku {sku!r}")
    cat = _cat()
    others = [s.upper() for s in _csv(with_skus)] or [a["sku"] for a in cat["attach"].get(p["sku"], [])]
    checks = []
    for o in others:
        q = _prod(o)
        if not q:
            checks.append({"with": o, "verdict": "unknown_sku"})
            continue
        v, why = _compat(p, q)
        checks.append({"with": q["sku"], "product": q["name"], "price_usd": q["list_price_usd"], "verdict": v, "why": why})
    months = cat["careplus"]["manufacturer_warranty_months"].get(p["brand"], cat["careplus"]["manufacturer_warranty_months"]["default"])
    addon = cat["careplus"]["accidental_damage_addon_usd"].get(p["category"])
    return ok(sku=p["sku"], product=p["name"], price_usd=p["list_price_usd"], checks=checks,
              bundles=[b for b in cat["bundles"] if p["sku"] in b["skus"]],
              careplus={**_careplus(p["list_price_usd"]), "accidental_damage_addon_usd": addon},
              manufacturer_warranty_months=months)


def _seg(seg_id: str) -> dict | None:
    return next((s for s in fixture("ret_segments")["segments"] if s["segment_id"] == seg_id.strip().upper()), None)


def _band_factor(price: float) -> float:
    return next(b["factor"] for b in fixture("ret_segments")["price_band_factor"] if price >= b["min_price"])


def _campaign_buyers(seg: dict, category: str, promo_price: float, discount_pct: float, channel: str) -> tuple[int, float]:
    """(sends, expected buyers) for one segment — the response model documented in ret_segments.json."""
    segd = fixture("ret_segments")
    sends = round(seg["size"] * (seg["push_opt_in"] if channel == "push" else seg["email_opt_in"]))
    reach = sends * seg["affinity"][category] * segd["engaged_share"]
    boost = 1 + 3 * discount_pct / 100 * seg["discount_sensitivity"] / 0.6
    return sends, reach * seg["base_response"] * _band_factor(promo_price) * boost


def _overlaps(a1: dt.date, a2: dt.date, b1: dt.date, b2: dt.date) -> bool:
    return a1 <= b2 and b1 <= a2


@hive_tool("enterprise")
def ret_simulate_promotion(sku: str, discount_pct: float, weeks: int = 2, segment_id: str = "", channel: str = "email",
                           start_date: str = "2026-11-09", targeted_only: bool = False, bundle_sku: str = "",
                           bundle_discount_pct: float = 0.0) -> dict:
    """Simulate a Larkspur promotion for one SKU: lift, margin, cannibalisation, halo, and margin vs doing nothing.

    Public promotions cut the shelf price for everyone (lift from the category price elasticity). A target segment
    adds campaign buyers (opted-in, engaged audience x category affinity x response x price-band factor x discount
    boost). With targeted_only=True the discount is a personal offer code for the segment only, so baseline sales
    stay at full price. 'Do nothing' runs to the SKU's end of life (or 90 days for core and seasonal items): demand
    after the window fades to 60% for end-of-life and 50% for off-season items, leftover end-of-life stock is cleared
    at the category clearance discount, and holding cost is charged.

    Args:
        sku: SKU to promote, e.g. 'LUM-55Q8'.
        discount_pct: Discount off list price in percent (e.g. 15).
        weeks: Promotion length in weeks (1-6).
        segment_id: Optional target segment (e.g. 'SEG-HCU'); required when targeted_only is True.
        channel: 'email', 'push' or 'sms' for the targeted part.
        start_date: Promotion start (YYYY-MM-DD).
        targeted_only: True = personal offer code for the segment only (no public price cut).
        bundle_sku: Optional attach SKU offered as a bundle (e.g. 'AUR-SB700').
        bundle_discount_pct: Discount on the bundle SKU in percent.

    Returns:
        Units (baseline, store, campaign, total, incremental), revenue, margin, cannibalisation, halo, campaign cost,
        scenario comparison (promotion vs do nothing to the horizon), cover after the promotion and guardrail checks
        (max discount, 18% margin floor, calendar conflicts, segment contact cap).
    """
    p = _prod(sku)
    if not p:
        return err(f"unknown sku {sku!r}")
    if not 0 < discount_pct < 90 or not 1 <= weeks <= 6:
        return err("discount_pct must be above 0 and below 90 and weeks between 1 and 6",
                   hint="For a bundle-led offer keep a small discount on the main SKU (e.g. 5) and put the rest in "
                        "bundle_discount_pct.")
    if targeted_only and not segment_id:
        return err("targeted_only needs a segment_id")
    try:
        start = dt.date.fromisoformat(str(start_date).strip()[:10])
    except ValueError:
        return err("start_date must be YYYY-MM-DD")
    cat, segd = _cat(), fixture("ret_segments")
    cp = cat["category_params"][p["category"]]
    pos = [x for x in fixture("ret_inventory")["positions"] if x["sku"] == p["sku"]]
    on_hand, ads = sum(x["on_hand"] for x in pos), sum(x["ads_28d"] for x in pos)
    d = discount_pct / 100
    days = weeks * 7
    end = start + dt.timedelta(days=days - 1)
    price, cost = p["list_price_usd"], p["unit_cost_usd"]
    promo_price = round(price * (1 - d), 2)
    baseline = ads * days
    lift = 1.0 if targeted_only else (1 - d) ** cp["elasticity"]
    store_units = baseline * lift
    campaign_units, sends, seg = 0.0, 0, None
    warnings = []
    if segment_id:
        seg = _seg(segment_id)
        if not seg:
            return err(f"unknown segment {segment_id!r}")
        sends, buyers = _campaign_buyers(seg, p["category"], promo_price, discount_pct, channel)
        campaign_units = buyers * segd["units_per_responder"]
        if seg["margin_protect"] and discount_pct > 10:
            warnings.append(f"{seg['name']} is margin-protected: use bonus points or a bundle, not > 10% off")
    demand = store_units + campaign_units
    total_units = min(round(demand), on_hand)
    if demand > on_hand:
        warnings.append("Demand exceeds stock: the promotion would sell out")
    scale = total_units / demand if demand else 0
    full_units = round(store_units * scale) if targeted_only else 0
    promo_units = total_units - full_units
    incr = max(0.0, total_units - baseline)
    unit_margin = promo_price - cost
    gm = promo_units * unit_margin + full_units * (price - cost)
    cannib = []
    for r in cat["related"].get(p["sku"], []):
        q = _prod(r["sku"])
        u = round(incr * r["cannibalisation_pct"] / 100)
        cannib.append({"sku": q["sku"], "units": u, "margin_lost_usd": round(u * (q["list_price_usd"] - q["unit_cost_usd"]))})
    halo = []
    b_sku = bundle_sku.strip().upper()
    for a in cat["attach"].get(p["sku"], []):
        q = _prod(a["sku"])
        rate = a["attach_rate"] * (2.5 if q["sku"] == b_sku else 1)
        disc = bundle_discount_pct / 100 if q["sku"] == b_sku else 0
        u = round(incr * rate)
        halo.append({"sku": q["sku"], "units": u, "attach_rate": round(rate, 3),
                     "margin_usd": round(u * (q["list_price_usd"] * (1 - disc) - q["unit_cost_usd"]))})
    if b_sku and b_sku not in {h["sku"] for h in halo}:
        warnings.append(f"{bundle_sku} is not a known attach item for {p['sku']}; bundle effect not modelled")
    camp_cost = (segd["fixed_campaign_cost_usd"] + sends * segd["send_cost_usd"].get(channel, 0.004)) if seg else 0.0
    net = gm - sum(c["margin_lost_usd"] for c in cannib) + sum(h["margin_usd"] for h in halo) - camp_cost

    eol = p["lifecycle"] == "end_of_life" and p["eol_date"]
    horizon_end = _d(p["eol_date"]) if eol else start + dt.timedelta(days=90)
    horizon = max(days, (horizon_end - start).days)
    fade = 0.6 if eol else 0.5 if p["lifecycle"] == "seasonal" else 1.0
    clear_price = price * (1 - cp["clearance_discount_pct"] / 100)
    hold_rate = cat["holding_cost_pct_per_year"] / 100

    def scenario(units_window: float, window_margin: float) -> dict:
        left = on_hand - units_window
        post = min(left, ads * fade * (horizon - days))
        leftover = left - post
        clear = leftover * (clear_price - cost) if eol else 0.0
        holding = (on_hand + leftover) / 2 * cost * hold_rate * horizon / 365
        if not eol:
            holding += leftover * cost * hold_rate * 0.25
        return {"units_sold_full_price_after": round(post), "leftover_units": round(leftover),
                "clearance_margin_usd": round(clear), "holding_cost_usd": round(holding),
                "total_margin_usd": round(window_margin + post * (price - cost) + clear - holding)}

    base_units = min(baseline, on_hand)
    nothing = scenario(base_units, base_units * (price - cost))
    promo = scenario(total_units, net)
    checks = []
    max_disc = p["max_discount_pct_override"] or cp["max_discount_pct"]
    checks.append({"check": "max_discount", "ok": discount_pct <= max_disc,
                   "detail": f"<= {max_disc}%" if discount_pct <= max_disc else
                   f"{discount_pct}% > {max_disc}% category max; merchandising director approval"})
    margin_pct = unit_margin / promo_price * 100
    floor = fixture("ret_promotions")["margin_floor_pct"]
    eol_ok = bool(eol) and margin_pct >= 0
    checks.append({"check": "margin_floor", "ok": margin_pct >= floor or eol_ok,
                   "detail": f"Promo margin {margin_pct:.1f}% vs floor {floor}%"
                   + (" (end-of-life clearance exception: floor 0%, director sign-off)" if eol_ok and margin_pct < floor else "")})
    promos = fixture("ret_promotions")
    conflicts = [f"{c['promo_id']} {c['name']} ({c['start']} to {c['end']})" for c in promos["calendar"]
                 if _overlaps(start, end, _d(c["start"]), _d(c["end"]))
                 and (p["category"] in c["categories"] or p["sku"] in c["skus"])]
    conflicts += [f"Blackout: {b['name']} ({b['start']} to {b['end']})" for b in promos["blackouts"]
                  if _overlaps(start, end, _d(b["start"]), _d(b["end"])) and p["category"] in b["categories"]]
    checks.append({"check": "calendar", "ok": not conflicts, "detail": conflicts or "No overlap in this category"})
    if seg:
        cap = segd["contact_cap_per_week"]["email"]
        full = [w for w, n in zip(segd["weeks"], segd["scheduled_promo_emails"][seg["segment_id"]])
                if n >= cap and _overlaps(start, end, _d(w), _d(w) + dt.timedelta(days=6))]
        checks.append({"check": "contact_cap", "ok": not full or channel == "push",
                       "detail": f"{seg['segment_id']} already at {cap} promo emails in week(s) {', '.join(full)}"
                       + (" (push is not capped by email)" if full and channel == "push" else "") if full
                       else "Capacity available"})
    after = on_hand - total_units
    return ok(sku=p["sku"], product=p["name"], category=p["category"], lifecycle=p["lifecycle"], eol_date=p["eol_date"],
              mechanic="targeted offer code" if targeted_only else "public price promotion",
              window={"start": start.isoformat(), "end": end.isoformat(), "weeks": weeks},
              pricing={"list_usd": price, "promo_usd": promo_price, "unit_cost_usd": cost,
                       "promo_margin_pct": round(margin_pct, 1)},
              stock={"on_hand": on_hand, "ads": round(ads, 2), "cover_days_now": round(on_hand / ads, 1),
                     "cover_days_after": round(after / ads, 1)},
              units={"baseline": round(baseline), "price_lift_x": round(lift, 2), "store_units": round(store_units),
                     "campaign_units": round(campaign_units), "total": total_units, "at_promo_price": promo_units,
                     "at_full_price": full_units, "incremental": round(incr)},
              targeting={"segment": seg["segment_id"] if seg else None, "channel": channel if seg else None,
                         "sends": sends},
              financials={"revenue_usd": round(promo_units * promo_price + full_units * price),
                          "gross_margin_usd": round(gm), "cannibalisation": cannib, "halo": halo,
                          "campaign_cost_usd": round(camp_cost), "net_margin_window_usd": round(net)},
              scenarios={"horizon_end": horizon_end.isoformat(), "demand_fade_after_window": fade,
                         "do_nothing": nothing, "promotion": promo,
                         "margin_vs_do_nothing_usd": promo["total_margin_usd"] - nothing["total_margin_usd"]},
              checks=checks, warnings=warnings)


@hive_tool("enterprise")
def ret_promo_calendar(start_date: str = "2026-11-09", end_date: str = "2026-12-06", category: str = "",
                       segment_id: str = "") -> dict:
    """Show the Larkspur promotion calendar for a window: planned promotions, blackout periods and segment contact load.

    Args:
        start_date: Window start (YYYY-MM-DD).
        end_date: Window end (YYYY-MM-DD).
        category: Optional category filter (e.g. 'Kitchen').
        segment_id: Optional segment to show weekly promo-email load against the 2-per-week cap.

    Returns:
        Promotions and blackouts overlapping the window, and per-week contact load with remaining capacity.
    """
    try:
        a, b = dt.date.fromisoformat(start_date), dt.date.fromisoformat(end_date)
    except ValueError:
        return err("dates must be YYYY-MM-DD")
    pr, segd = fixture("ret_promotions"), fixture("ret_segments")
    cal = [c for c in pr["calendar"] if _overlaps(a, b, _d(c["start"]), _d(c["end"]))
           and (not category or category in c["categories"])]
    bl = [x for x in pr["blackouts"] if _overlaps(a, b, _d(x["start"]), _d(x["end"]))
          and (not category or category in x["categories"])]
    segs = [segment_id.strip().upper()] if segment_id else sorted(segd["scheduled_promo_emails"])
    cap = segd["contact_cap_per_week"]["email"]
    load = {}
    for s in segs:
        if s not in segd["scheduled_promo_emails"]:
            return err(f"unknown segment {segment_id!r}")
        load[s] = [{"week_of": w, "scheduled": n, "remaining": max(0, cap - n)}
                   for w, n in zip(segd["weeks"], segd["scheduled_promo_emails"][s])
                   if _overlaps(a, b, _d(w), _d(w) + dt.timedelta(days=6))]
    return ok(window={"start": a.isoformat(), "end": b.isoformat()}, promotions=cal, blackouts=bl,
              contact_cap_per_week=segd["contact_cap_per_week"], segment_load=load,
              margin_floor_pct=pr["margin_floor_pct"])


@hive_tool("enterprise")
def ret_match_segments(skus: str, channel: str = "email", discount_pct: float = 15.0, max_segments: int = 3,
                       start_date: str = "2026-11-09") -> dict:
    """Pick the best customer segments to target for each SKU (e.g. overstocked items), with expected buyers.

    Expected buyers = opted-in audience x category affinity x engaged share x base response x price-band factor x
    discount boost (scaled by the segment's discount sensitivity).
    Segments at their weekly promo-email cap in the start week are flagged; margin-protected segments (Rewards
    Gold) are flagged for discounts above 10%.

    Args:
        skus: Comma-separated SKUs, e.g. 'LUM-55Q8,AUR-BUDS3,VAN-AF55'.
        channel: 'email' or 'push'.
        discount_pct: Discount assumed for the response estimate.
        max_segments: Segments to return per SKU (1-5).
        start_date: Campaign start, used for the contact-cap check (YYYY-MM-DD).

    Returns:
        Per SKU: ranked segments with reachable audience, expected buyers and revenue, contact capacity and rationale.
    """
    segd = fixture("ret_segments")
    try:
        start = dt.date.fromisoformat(start_date)
    except ValueError:
        return err("start_date must be YYYY-MM-DD")
    week_idx = next((i for i, w in enumerate(segd["weeks"]) if _d(w) <= start < _d(w) + dt.timedelta(days=7)), 0)
    cap = segd["contact_cap_per_week"]["email" if channel != "push" else "push"]
    out = {}
    for s in _csv(skus):
        p = _prod(s)
        if not p:
            out[s] = {"error": "unknown sku"}
            continue
        promo_price = p["list_price_usd"] * (1 - discount_pct / 100)
        ranked = []
        for seg in segd["segments"]:
            sends, buyers = _campaign_buyers(seg, p["category"], promo_price, discount_pct, channel)
            reach = sends * seg["affinity"][p["category"]] * segd["engaged_share"]
            sched = segd["scheduled_promo_emails"][seg["segment_id"]][week_idx]
            flags = []
            if channel != "push" and sched >= cap:
                flags.append(f"At email cap ({sched}/{cap}) week of {segd['weeks'][week_idx]}; start a week later or use push")
            if seg["margin_protect"] and discount_pct > 10:
                flags.append("Margin-protected: offer points or a bundle instead of > 10% off")
            ranked.append({"segment_id": seg["segment_id"], "name": seg["name"], "affinity": seg["affinity"][p["category"]],
                           "sends": sends, "engaged_reach": round(reach), "expected_buyers": round(buyers, 1),
                           "expected_revenue_usd": round(buyers * promo_price), "flags": flags, "notes": seg["notes"]})
        ranked.sort(key=lambda r: (bool(r["flags"]), -r["expected_buyers"]))
        out[p["sku"]] = {"product": p["name"], "category": p["category"],
                         "segments": ranked[:max(1, min(int(max_segments), 5))]}
    return ok(channel=channel, discount_pct=discount_pct, week_of=segd["weeks"][week_idx], by_sku=out)


_RET_BANNED = ["cheapest", "lowest price ever", "guaranteed", "best price anywhere", "!!!", "act now"]


@hive_tool("enterprise", kind="action")
def ret_create_campaign(name: str, skus: str, segment_ids: str, discount_pct: float, start_date: str, end_date: str,
                        copy_blocks: list[dict], objective: str = "clear_overstock",
                        bundle_discount_pct: float = 0.0) -> dict:
    """Create a draft campaign in the Larkspur marketing platform after validating offer and copy. Simulated.

    Validation: discount within category max, dates outside blackouts, segments known, and copy rules per channel
    (email subject <= 60 chars, push <= 110, SMS <= 160 with 'Reply STOP', 'While stocks last' for overstock
    campaigns, offer end date stated, no banned superlatives, discount in copy matches the offer).

    Args:
        name: Campaign name.
        skus: Comma-separated SKUs in the offer.
        segment_ids: Comma-separated target segments (e.g. 'SEG-HCU,SEG-NWH').
        discount_pct: Headline discount in percent.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        copy_blocks: List of {"channel": "email"|"push"|"sms"|"social", "subject": str (email only), "body": str}.
        objective: 'clear_overstock', 'acquisition' or 'loyalty'.
        bundle_discount_pct: Discount on a bundled attach item, if the offer has one (e.g. 20 for the soundbar).

    Returns:
        Campaign id, campaign_status (draft_created / draft_with_issues), audience estimate, approvals needed, issues.
    """
    sku_list, seg_list = [s.upper() for s in _csv(skus)], [s.upper() for s in _csv(segment_ids)]
    prods = [_prod(s) for s in sku_list]
    if not sku_list or None in prods:
        return err("unknown or missing SKUs", skus=sku_list)
    segs = [_seg(s) for s in seg_list]
    if not seg_list or None in segs:
        return err("unknown or missing segments", segments=seg_list)
    try:
        a, b = dt.date.fromisoformat(start_date), dt.date.fromisoformat(end_date)
    except ValueError:
        return err("dates must be YYYY-MM-DD")
    if not copy_blocks:
        return err("copy_blocks must not be empty")
    issues, approvals = [], []
    cat = _cat()
    for p in prods:
        mx = p["max_discount_pct_override"] or cat["category_params"][p["category"]]["max_discount_pct"]
        if discount_pct > mx:
            approvals.append(f"Merchandising director: {p['sku']} discount {discount_pct}% > {mx}%")
        for bl in fixture("ret_promotions")["blackouts"]:
            if _overlaps(a, b, _d(bl["start"]), _d(bl["end"])) and p["category"] in bl["categories"]:
                issues.append(f"{p['sku']}: dates overlap blackout '{bl['name']}' ({bl['start']} to {bl['end']})")
    for blk in copy_blocks:
        ch = str(blk.get("channel", "")).lower()
        body = str(blk.get("body", ""))
        subj = str(blk.get("subject", ""))
        txt = f"{subj} {body}"
        low = txt.lower()
        if ch == "email":
            if not subj:
                issues.append("email: missing subject")
            elif len(subj) > 60:
                issues.append(f"email: subject {len(subj)} chars (max 60)")
            if not re.search(r"\b(ends|until|valid|through)\b", low):
                issues.append("email: state when the offer ends (e.g. 'Ends Nov 22')")
        elif ch == "push" and len(body) > 110:
            issues.append(f"push: {len(body)} chars (max 110)")
        elif ch == "sms":
            if len(body) > 160:
                issues.append(f"sms: {len(body)} chars (max 160)")
            if "reply stop" not in low:
                issues.append("sms: add 'Reply STOP to opt out'")
        elif ch == "social" and len(body) > 280:
            issues.append(f"social: {len(body)} chars (max 280)")
        elif ch not in ("email", "push", "sms", "social"):
            issues.append(f"unknown channel {ch!r}")
        if objective == "clear_overstock" and ch in ("email", "social") and "while stocks last" not in low:
            issues.append(f"{ch}: overstock offers must say 'While stocks last'")
        for t in _RET_BANNED:
            if t in low:
                issues.append(f"{ch}: banned phrase '{t}'")
        for pct in re.findall(r"(\d{1,2})\s?%", txt):
            if float(pct) > discount_pct and abs(float(pct) - bundle_discount_pct) > 0.01:
                issues.append(f"{ch}: copy says {pct}% but the offer is {discount_pct}%")
        if re.search(r"\bLark[sS]pur'?s?\b", txt) and re.search(r"\bLarkSpur\b|\bLARKSPUR\b", txt):
            issues.append(f"{ch}: brand is written 'Larkspur'")
    audience = round(sum(s["size"] * s["email_opt_in"] for s in segs))
    cid = _sid("LKC-2611-", name, sku_list, seg_list, start_date)
    return ok(campaign_id=cid, campaign_status="draft_with_issues" if issues else "draft_created", name=name, skus=sku_list,
              segments=seg_list, window=f"{a.isoformat()} to {b.isoformat()}", discount_pct=discount_pct,
              audience_estimate=audience, approvals_required=approvals, issues=issues,
              next_step="Fix the issues and resubmit" if issues else "Send to marketing ops for scheduling",
              simulated=True)


# =====================================================================================================================
# LOGISTICS — Halvard Logistics: Control Tower, Shipment Brief, Logistics Orch., Replenishment; Vantor: Mfg Quality
# =====================================================================================================================


def _net() -> dict:
    return fixture("log_network")


def _shipper(q: str) -> dict | None:
    q = (q or "").strip().lower()
    return next((s for s in _net()["shippers"] if q and (q == s["shipper_id"].lower() or q in s["name"].lower())), None)


def _lane(lane_id: str) -> dict:
    return next(l for l in _net()["lanes"] if l["lane_id"] == lane_id)


def _disr(did: str | None) -> dict | None:
    return next((x for x in fixture("log_disruptions")["disruptions"] if x["disruption_id"] == did), None) if did else None


def _ship(shipment_id: str) -> dict | None:
    return next((s for s in fixture("log_shipments")["shipments"]
                 if s["shipment_id"].lower() == (shipment_id or "").strip().lower()), None)


def _delay_h(s: dict) -> float:
    return round((_ts(s["eta"]) - _ts(s["promised"])).total_seconds() / 3600, 1)


def _severity(s: dict) -> tuple[float, str]:
    tier = _shipper(s["shipper_id"])["tier"]
    score = {1: 3, 2: 2, 3: 1}[tier] * (1 + max(_delay_h(s), 0) / 24)
    score *= 2.2 if s["temperature_controlled"] else 1
    score *= 1.3 if s["promo_critical"] else 1
    score *= 2 if s["line_stoppage_risk"] else 1
    score += math.log10(max(s["value_usd"], 10)) / 2
    label = "critical" if score >= 15 else "high" if score >= 8 else "medium" if score >= 4 else "low"
    return round(score, 1), label


@hive_tool("enterprise")
def log_shipment_exceptions(shipper: str = "", min_severity: str = "low", include_on_time: bool = False) -> dict:
    """List Halvard shipment exceptions as of 2026-11-06 07:00, ranked by severity, with cause and notify deadline.

    Severity = shipper tier x (1 + days late) x temperature-control (x2.2) x promo-critical (x1.3) x line-stoppage
    risk (x2) + value factor; critical >= 15, high >= 8, medium >= 4.

    Args:
        shipper: Optional shipper id or name (e.g. 'C-LRK' or 'Larkspur').
        min_severity: Minimum severity to include: 'low', 'medium', 'high' or 'critical'.
        include_on_time: Also list shipments that are on schedule.

    Returns:
        Exceptions with lane, carrier, promised vs current ETA, hours late, disruption, downstream impact, severity,
        detection time, the shipper notification deadline, when (and what) the shipper was last told, and an
        overdue flag for exceptions nobody has notified yet; plus counts by severity and cause.
    """
    order = ["low", "medium", "high", "critical"]
    if min_severity not in order:
        return err(f"min_severity must be one of {order}")
    sh = _shipper(shipper) if shipper else None
    if shipper and not sh:
        return err(f"unknown shipper {shipper!r}", shippers=[s["name"] for s in _net()["shippers"]])
    rows = []
    for s in fixture("log_shipments")["shipments"]:
        if sh and s["shipper_id"] != sh["shipper_id"]:
            continue
        late = _delay_h(s)
        is_exc = late > 0 or s["exception_code"]
        if not is_exc and not include_on_time:
            continue
        score, label = _severity(s) if is_exc else (0.0, "on_time")
        if is_exc and order.index(label) < order.index(min_severity):
            continue
        shp = _shipper(s["shipper_id"])
        d = _disr(s["disruption_id"])
        notify_by = (_ts(s["detected_at"]) + dt.timedelta(hours=shp["notify_within_hours"])) if s["detected_at"] else None
        rows.append({"shipment_id": s["shipment_id"], "shipper": shp["name"], "tier": shp["tier"],
                     "consignee": s["consignee"], "lane_id": s["lane_id"], "mode": s["mode"], "carrier": s["carrier"],
                     "promised": s["promised"], "eta": s["eta"], "hours_late": late, "status": s["status"],
                     "last_event": s["last_event"], "cause_code": s["exception_code"],
                     "disruption": d["title"] if d else None, "value_usd": s["value_usd"], "contents": s["contents"],
                     "downstream": s["downstream"], "severity": label, "severity_score": score,
                     "detected_at": s["detected_at"],
                     "notify_by": notify_by.isoformat(timespec="minutes") if notify_by else None,
                     "shipper_notified_at": s.get("shipper_notified_at"),
                     "last_update_note": s.get("last_update_note"),
                     "notification_overdue": bool(notify_by and notify_by < LOG_NOW and not s.get("shipper_notified_at"))})
    rows.sort(key=lambda r: -r["severity_score"])
    exc = [r for r in rows if r["severity"] != "on_time"]
    return ok(as_of=LOG_NOW.isoformat(timespec="minutes"), shipments=rows,
              counts={k: sum(1 for r in exc if r["severity"] == k) for k in reversed(order)},
              by_cause={c: sum(1 for r in exc if r["cause_code"] == c) for c in sorted({r["cause_code"] for r in exc if r["cause_code"]})},
              value_at_risk_usd=sum(r["value_usd"] for r in exc),
              cause_codes={"WX": "weather", "PORT": "port congestion", "CAP": "carrier capacity", "DC": "DC backlog",
                           "MECH": "equipment breakdown", "DOCS": "documentation/customs"})


@hive_tool("enterprise")
def log_eta_risk(shipment_id: str) -> dict:
    """Estimate ETA risk for one shipment: probability of (further) delay, P50/P90 arrival and the drivers.

    Args:
        shipment_id: Shipment id, e.g. 'HLV-SH-260552'.

    Returns:
        Promised vs carrier ETA, P50/P90 ETA, probability of missing the promise and of further slip, lane on-time
        rate, disruption confidence, and for plant inbound the expected line-stoppage hours at P50/P90.
    """
    s = _ship(shipment_id)
    if not s:
        return err(f"unknown shipment {shipment_id!r}")
    lane = _lane(s["lane_id"])
    d = _disr(s["disruption_id"])
    base = 1 - lane["on_time_30d_pct"] / 100
    eta, promised = _ts(s["eta"]), _ts(s["promised"])
    if d:
        slip = {"high": 0.25, "medium": 0.45, "low": 0.6}[d["confidence"]]
        p90 = eta + dt.timedelta(hours=d["uncertainty_hours"])
    else:
        slip = base
        p90 = eta + dt.timedelta(hours=6 if s["mode"] != "ocean" else 48)
    margin = (promised - eta).total_seconds() / 3600
    p_miss = 1.0 if margin < 0 else round(min(0.95, slip if d else base), 2)
    drivers = [f"Lane {lane['lane_id']} {lane['carrier']} on-time {lane['on_time_30d_pct']}% (30 days)"]
    if d:
        drivers.append(f"{d['title']} - expected clear {d['expected_clear']} (confidence {d['confidence']})")
    if s["exception_code"]:
        drivers.append(f"Current status: {s['last_event']}")
    out = {"shipment_id": s["shipment_id"], "promised": s["promised"], "eta_p50": s["eta"],
           "eta_p90": p90.isoformat(timespec="minutes"), "hours_late_p50": round(-margin, 1) if margin < 0 else 0,
           "p_miss_promise": p_miss, "p_further_slip": round(slip, 2), "drivers": drivers,
           "downstream": s["downstream"]}
    if s["line_stoppage_risk"]:
        buf = _ts(s["line_stoppage_risk"]["buffer_until"])
        out["line_stoppage"] = {"line": s["line_stoppage_risk"]["line"], "buffer_until": s["line_stoppage_risk"]["buffer_until"],
                                "stoppage_hours_p50": max(0.0, round((eta - buf).total_seconds() / 3600, 1)),
                                "stoppage_hours_p90": max(0.0, round((p90 - buf).total_seconds() / 3600, 1))}
    return ok(**out)


@hive_tool("enterprise")
def log_customer_impact(shipper: str = "", shipment_ids: str = "") -> dict:
    """Quantify customer impact of late shipments per shipper: SLA penalty exposure, downstream effects, comms duty.

    Penalties follow each shipper's contract (e.g. Larkspur USD 250 per store delivery > 24 h late, x2 if
    promo-critical; Vantor USD 4,000 per hour of line stoppage, cap USD 40,000; Orla USD 1,500 per late
    temperature-controlled delivery).

    Args:
        shipper: Optional shipper id or name.
        shipment_ids: Optional comma-separated shipment ids to limit the analysis.

    Returns:
        Per shipper: tier, contact and channel, affected shipments, value at risk, penalty exposure with the
        calculation, downstream impacts and the notification deadline; plus the total exposure.
    """
    ids = {x.upper() for x in _csv(shipment_ids)}
    sh = _shipper(shipper) if shipper else None
    if shipper and not sh:
        return err(f"unknown shipper {shipper!r}")
    groups: dict[str, dict] = {}
    for s in fixture("log_shipments")["shipments"]:
        late = _delay_h(s)
        if (ids and s["shipment_id"] not in ids) or (not ids and late <= 0) or (sh and s["shipper_id"] != sh["shipper_id"]):
            continue
        shp = _shipper(s["shipper_id"])
        g = groups.setdefault(shp["shipper_id"], {"shipper": shp["name"], "tier": shp["tier"], "contact": shp["contact"],
                                                  "email": shp["email"], "channel": shp["channel"],
                                                  "contract_penalty": shp["penalty"], "shipments": [],
                                                  "value_at_risk_usd": 0, "penalty_exposure_usd": 0,
                                                  "notify_by": None})
        pen, calc = 0.0, "no penalty"
        if shp["shipper_id"] == "C-VAN" and s["line_stoppage_risk"]:
            hrs = max(0.0, (_ts(s["eta"]) - _ts(s["line_stoppage_risk"]["buffer_until"])).total_seconds() / 3600)
            pen = min(hrs * shp["line_stoppage_per_hour_usd"], shp["line_stoppage_cap_usd"])
            calc = f"{hrs:.0f} h stoppage x USD {shp['line_stoppage_per_hour_usd']:,} (cap {shp['line_stoppage_cap_usd']:,})"
        elif shp["shipper_id"] == "C-LRK":
            if late > 24 and s["consignee"].startswith("Larkspur S"):
                pen = shp["penalty_per_late_delivery_usd"] * (shp["promo_multiplier"] if s["promo_critical"] else 1)
                calc = "store delivery > 24 h late" + (" (promo-critical x2)" if s["promo_critical"] else "")
            elif s["consignee"].startswith("Larkspur S"):
                calc = "store delivery <= 24 h late: no penalty"
            elif late > 0:
                calc = "no contract penalty (DC/parcel flow) - downstream risk only"
        elif shp["shipper_id"] == "C-ORL" and s["temperature_controlled"] and late > 0:
            pen, calc = shp["penalty_per_late_delivery_usd"], "late temperature-controlled delivery"
        elif shp["shipper_id"] == "C-PNC" and late > 48:
            pen = round(s["weight_kg"] * _lane(s["lane_id"])["cost_per_kg_usd"], 2)
            calc = "freight charge credited (> 48 h)"
        elif shp["penalty_per_late_delivery_usd"] and late > 0:
            pen, calc = shp["penalty_per_late_delivery_usd"], "late delivery"
        g["shipments"].append({"shipment_id": s["shipment_id"], "consignee": s["consignee"], "hours_late": late,
                               "value_usd": s["value_usd"], "penalty_usd": pen, "penalty_basis": calc,
                               "downstream": s["downstream"]})
        g["value_at_risk_usd"] += s["value_usd"]
        g["penalty_exposure_usd"] += pen
        if s["detected_at"]:
            nb = (_ts(s["detected_at"]) + dt.timedelta(hours=shp["notify_within_hours"])).isoformat(timespec="minutes")
            g["notify_by"] = min(g["notify_by"] or nb, nb)
    if not groups:
        return err("no late shipments match")
    rows = sorted(groups.values(), key=lambda g: (g["tier"], -g["penalty_exposure_usd"]))
    return ok(as_of=LOG_NOW.isoformat(timespec="minutes"), shippers=rows,
              total_penalty_exposure_usd=round(sum(g["penalty_exposure_usd"] for g in rows), 2),
              total_value_at_risk_usd=sum(g["value_at_risk_usd"] for g in rows))


@hive_tool("enterprise")
def log_disruption_feed(region: str = "") -> dict:
    """Return active supply-chain disruptions (weather, port, carrier capacity, DC, customs) with affected lanes.

    Args:
        region: Optional region filter: 'North', 'Coast', 'Central' or 'South'.

    Returns:
        Disruptions with type, start, expected clear time, confidence, affected lanes, impact, source, and the count
        and value of active Halvard shipments they touch.
    """
    ships = fixture("log_shipments")["shipments"]
    rows = []
    for d in fixture("log_disruptions")["disruptions"]:
        if region and d["region"].lower() != region.strip().lower():
            continue
        hit = [s for s in ships if s["disruption_id"] == d["disruption_id"]]
        rows.append({**d, "shipments_affected": [s["shipment_id"] for s in hit],
                     "value_affected_usd": sum(s["value_usd"] for s in hit),
                     "lanes": [f"{l['lane_id']} {_net()['sites'].get(l['origin'], l['origin'])} -> "
                               f"{_net()['sites'].get(l['destination'], l['destination'])} ({l['mode']}, {l['carrier']})"
                               for l in _net()["lanes"] if l["lane_id"] in d["affected_lanes"]]})
    return ok(as_of=LOG_NOW.isoformat(timespec="minutes"), disruptions=rows, count=len(rows))


@hive_tool("enterprise")
def log_recovery_options(shipment_id: str) -> dict:
    """Evaluate recovery options for a late shipment: cost, new ETA, hours saved, promise/deadline check, approval.

    Recommendation rule: cheapest option that meets the promise (or prevents line stoppage); otherwise the option
    with the best hours saved per dollar within the director's approval limit. Approval: <= USD 5,000 ops manager,
    <= USD 25,000 director, above that VP.

    Args:
        shipment_id: Shipment id, e.g. 'HLV-SH-260620'.

    Returns:
        Options with cost, new ETA, hours saved, meets_promise, line-stoppage hours and penalty avoided (plant
        inbound), approval level and the recommended option with the reason.
    """
    s = _ship(shipment_id)
    if not s:
        return err(f"unknown shipment {shipment_id!r}")
    if not s["recovery_options"]:
        return err("shipment is on schedule - no recovery needed", eta=s["eta"], promised=s["promised"])
    lim = _net()["approval_limits_usd"]
    eta, promised = _ts(s["eta"]), _ts(s["promised"])
    shp = _shipper(s["shipper_id"])
    opts = []
    for o in s["recovery_options"]:
        new = _ts(o["new_eta"])
        row = {**o, "hours_saved": round((eta - new).total_seconds() / 3600, 1), "meets_promise": new <= promised,
               "approval": "ops_manager" if o["cost_usd"] <= lim["ops_manager"] else "director"
               if o["cost_usd"] <= lim["director"] else "vp"}
        if s["line_stoppage_risk"]:
            buf = _ts(s["line_stoppage_risk"]["buffer_until"])
            hrs = max(0.0, (new - buf).total_seconds() / 3600)
            row["line_stoppage_hours"] = round(hrs, 1)
            row["penalty_usd"] = min(hrs * shp["line_stoppage_per_hour_usd"], shp["line_stoppage_cap_usd"])
        opts.append(row)
    if s["line_stoppage_risk"]:
        base_pen = max(o["penalty_usd"] for o in opts)
        for o in opts:
            o["penalty_avoided_usd"] = base_pen - o["penalty_usd"]
            o["net_benefit_usd"] = o["penalty_avoided_usd"] - o["cost_usd"]
        best = max(opts, key=lambda o: (o["net_benefit_usd"], -o["cost_usd"]))
        why = "Highest net benefit (penalty and stoppage avoided minus cost)"
    else:
        meeting = [o for o in opts if o["meets_promise"]]
        if meeting:
            best, why = min(meeting, key=lambda o: o["cost_usd"]), "Cheapest option that meets the promise"
        else:
            within = [o for o in opts if o["hours_saved"] > 0 and o["approval"] != "vp"]
            if within:
                best = min(within, key=lambda o: o["cost_usd"] / o["hours_saved"])
                why = "Promise cannot be met; best hours saved per dollar within director limit"
            else:
                best, why = min(opts, key=lambda o: o["cost_usd"]), "No option improves the ETA; hold and communicate"
    return ok(shipment_id=s["shipment_id"], shipper=shp["name"], promised=s["promised"], current_eta=s["eta"],
              downstream=s["downstream"], options=opts, recommended=best["option"], reason=why,
              approval_limits_usd=lim)


@hive_tool("enterprise", kind="action")
def log_send_customer_update(shipper: str, subject: str, message: str, shipment_ids: str, channel: str = "email") -> dict:
    """Send a shipment status update to a shipper's logistics contact. Simulated — nothing is sent.

    The message must mention every shipment id, give a date for the new ETA and avoid internal codes
    (disruption ids, lane ids, cause codes).

    Args:
        shipper: Shipper id or name (e.g. 'Vantor').
        subject: Subject line.
        message: Full message text.
        shipment_ids: Comma-separated shipment ids covered by the update.
        channel: 'email' or 'portal'.

    Returns:
        Message id, recipient, delivery_status, and any quality checks that failed.
    """
    shp = _shipper(shipper)
    if not shp:
        return err(f"unknown shipper {shipper!r}")
    ids = [x.upper() for x in _csv(shipment_ids)]
    if not ids:
        return err("shipment_ids must not be empty")
    checks = [f"{i} not mentioned in the message" for i in ids if i not in message.upper()]
    if not re.search(r"\b20\d\d-\d\d-\d\d\b|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}\b|"
                     r"\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", message):
        checks.append("No date for the new ETA")
    if re.search(r"\bDSR-|\bL\d\d\b|\b(WX|PORT|CAP|MECH|DOCS)\b", message):
        checks.append("Internal codes in a customer message")
    if len(subject) > 90:
        checks.append("Subject longer than 90 characters")
    return ok(message_id=_sid("HLV-MSG-", shp["shipper_id"], subject), recipient=f"{shp['contact']} <{shp['email']}>",
              channel=channel, shipments=ids, delivery_status="sent" if not checks else "sent_with_warnings", checks=checks,
              simulated=True)


@hive_tool("enterprise")
def log_replenishment_plan(dc: str = "", sku: str = "", service_level: float = 0.0,
                           lead_time_buffer_days: float = 0.0) -> dict:
    """Compute demand-driven replenishment: safety stock, reorder point, stock-out gap and purchase-order suggestions.

    Safety stock = z x sqrt(LT x sd^2 + mean^2 x sd_LT^2); ROP = mean x LT + SS; order when inventory position
    (on hand + on order - backorders) <= ROP, up to ROP + mean x review period (at least EOQ, MOQ and case pack).
    Recent 14-day demand replaces the mean when it is > 30% higher (spike). Flags expedite gaps when on-hand runs
    out before the next inbound, and excess when days of supply > 60.

    Args:
        dc: Optional site filter: 'AVD' (Ashford Vale DC), 'RMD' (Redmarsh DC) or 'BRK' (Vantor plant).
        sku: Optional SKU filter (e.g. 'RES-ABS-PC', 'LUM-65Q8').
        service_level: Override cycle service level (e.g. 0.98); 0 = by ABC class (A 98%, B 95%, C 90%).
        lead_time_buffer_days: Extra lead-time days for a disruption (e.g. 4 for port congestion).

    Returns:
        Per item: demand used, SS, ROP, inventory position, days of supply, status (order_now / expedite / excess /
        ok), suggested quantity and expedite proposal; PO lines grouped by supplier with value.
    """
    data = fixture("log_items")
    if service_level and not 0.5 <= service_level < 1:
        return err("service_level must be between 0.5 and 0.999")
    rows, pos = [], {}
    for it in data["items"]:
        if dc and it["dc"] != dc.strip().upper():
            continue
        if sku and it["sku"] != sku.strip().upper():
            continue
        sl = service_level or data["service_level_by_abc"][it["abc"]]
        z = NormalDist().inv_cdf(sl)
        spike = it["recent_14d_mean"] > 1.3 * it["daily_demand_mean"]
        mu = it["recent_14d_mean"] if spike else it["daily_demand_mean"]
        sd = it["daily_demand_sd"] * (mu / it["daily_demand_mean"])
        lt = it["lead_time_days"] + lead_time_buffer_days
        ss = z * math.sqrt(lt * sd ** 2 + mu ** 2 * it["lead_time_sd_days"] ** 2)
        rop = mu * lt + ss
        on_order = sum(o["qty"] for o in it["on_order"])
        ip = it["on_hand"] + on_order - it["backorders"]
        net = it["on_hand"] - it["backorders"]
        dos = round(net / mu, 1)
        eoq = math.sqrt(2 * mu * 365 * it["order_cost_usd"] / (it["unit_cost_usd"] * data["holding_rate_per_year"]))
        qty = 0
        status = "ok"
        if ip <= rop:
            raw = max(eoq, rop + mu * it["review_period_days"] - ip, it["moq"])
            qty = int(math.ceil(raw / it["case_pack"]) * it["case_pack"])
            status = "order_now"
        next_in = min((_d(o["eta"]) for o in it["on_order"]), default=None)
        gap = None
        if next_in and dos < (next_in - TODAY).days:
            gap = round((next_in - TODAY).days - max(dos, 0), 1)
        elif not next_in and dos < lt:
            gap = round(lt - max(dos, 0), 1)
        expedite = None
        if gap:
            status = "expedite" if status == "ok" else status + "+expedite"
            alt = next((a for a in data["alternate_suppliers"] if a["sku"] == it["sku"] and a.get("dc", it["dc"]) == it["dc"]), None)
            need = (gap + 0.5) * mu
            if alt:
                need = max(alt["moq"], math.ceil(need / alt["case_pack"]) * alt["case_pack"])
                if alt.get("max_qty") and need > alt["max_qty"]:
                    gap_note = f"capped at {alt['max_qty']} available; {need - alt['max_qty']} units still short"
                    need = alt["max_qty"]
                else:
                    gap_note = None
                expedite = {"source": alt["supplier"], "qty": need, "lead_time_days": alt["lead_time_days"],
                            "unit_cost_usd": alt["unit_cost_usd"],
                            "premium_usd": round(need * (alt["unit_cost_usd"] - it["unit_cost_usd"]), 2)
                            if alt["unit_cost_usd"] > it["unit_cost_usd"] else round(need * alt["unit_cost_usd"], 2),
                            "note": alt["note"] + (f" ({gap_note})" if gap_note else "")}
            else:
                expedite = {"source": f"{it['supplier']} (ask for air/expedite)", "qty": round(need), "note":
                            "No approved alternate source"}
        if dos > 60 and status == "ok":
            status = "excess"
        row = {"dc": it["dc"], "sku": it["sku"], "description": it["description"], "supplier": it["supplier"],
               "abc": it["abc"], "service_level": sl, "demand_used_per_day": round(mu, 1),
               "demand_spike": spike, "lead_time_days": lt, "safety_stock": round(ss), "reorder_point": round(rop),
               "on_hand": it["on_hand"], "backorders": it["backorders"], "on_order": it["on_order"],
               "inventory_position": ip, "days_of_supply": dos, "eoq": round(eoq), "status": status,
               "suggested_order_qty": qty, "order_value_usd": round(qty * it["unit_cost_usd"], 2),
               "stockout_gap_days": gap, "expedite": expedite}
        if spike:
            row["note"] = (f"Demand spike: last 14 days {it['recent_14d_mean']}/day vs {it['daily_demand_mean']}/day"
                           + (" - linked to quality advisory QA-26-031 (cracked CM12 housings)" if it["sku"] == "VAN-P-HSG12" else ""))
        rows.append(row)
        if qty:
            po = pos.setdefault(it["supplier"], {"supplier": it["supplier"], "lines": [], "value_usd": 0.0})
            po["lines"].append({"dc": it["dc"], "sku": it["sku"], "qty": qty})
            po["value_usd"] = round(po["value_usd"] + qty * it["unit_cost_usd"], 2)
    if not rows:
        return err("no items match", sites=sorted({i["dc"] for i in data["items"]}))
    rank = {"order_now+expedite": 0, "expedite": 1, "order_now": 2, "excess": 3, "ok": 4}
    rows.sort(key=lambda r: (rank.get(r["status"], 5), r["days_of_supply"]))
    return ok(as_of=data["as_of"], items=rows, purchase_orders=list(pos.values()),
              summary={k: sum(1 for r in rows if r["status"] == k) for k in rank})


def _subgroup_stats(sg: list[dict]) -> list[dict]:
    return [{"subgroup": g["subgroup"], "timestamp": g["timestamp"], "shift": g["shift"],
             "xbar": round(mean(g["values"]), 4), "range": round(max(g["values"]) - min(g["values"]), 4),
             "values": g["values"]} for g in sg]


@hive_tool("enterprise")
def log_spc_check(line_id: str = "BW-2", characteristic: str = "", last_n: int = 30) -> dict:
    """Run SPC on a Vantor production characteristic: X-bar/R chart against Phase I limits, Western Electric rules, Cpk.

    Rules: R1 point beyond 3 sigma; R2 2 of 3 beyond 2 sigma (same side); R3 4 of 5 beyond 1 sigma (same side);
    R4 8 in a row on one side of the centre; TREND 6 in a row increasing or decreasing; RCHART range above UCL.

    Args:
        line_id: Production line, e.g. 'BW-2' (CM12 housing molding) or 'BW-1' (AF55 basket assembly).
        characteristic: Characteristic key (default: the line's first one, e.g. 'boss_wall_mm').
        last_n: Number of most recent subgroups (n=5) to analyse (10-30).

    Returns:
        Control limits, per-subgroup X-bar and range with zone, rule violations (first occurrence and all points),
        Phase I vs recent Cpk, out-of-spec readings and process events that precede the first violation.
    """
    q = fixture("log_quality")
    line = q["lines"].get(line_id.strip().upper())
    if not line:
        return err(f"unknown line {line_id!r}", lines=sorted(q["lines"]))
    key = characteristic or next(iter(line["characteristics"]))
    ch = line["characteristics"].get(key)
    if not ch:
        return err(f"unknown characteristic {key!r}", characteristics=sorted(line["characteristics"]))
    c = q["spc_constants_n5"]
    ph = ch["phase1_limits"]
    center, rbar = ph["center"], ph["rbar"]
    ucl, lcl = center + c["A2"] * rbar, center - c["A2"] * rbar
    sig = (ucl - center) / 3
    r_ucl = c["D4"] * rbar
    pts = _subgroup_stats(ch["subgroups"][-max(10, min(int(last_n), 30)):])
    for p in pts:
        z = (p["xbar"] - center) / sig
        p["zone_sigma"] = round(z, 2)
    viol: dict[str, list[int]] = {k: [] for k in ("R1", "R2", "R3", "R4", "TREND", "RCHART")}
    zs = [p["zone_sigma"] for p in pts]
    for i, p in enumerate(pts):
        n = p["subgroup"]
        if abs(zs[i]) > 3:
            viol["R1"].append(n)
        if p["range"] > r_ucl:
            viol["RCHART"].append(n)
        for side in (1, -1):
            w3 = zs[max(0, i - 2): i + 1]
            if len(w3) == 3 and sum(1 for z in w3 if z * side > 2) >= 2 and zs[i] * side > 2:
                viol["R2"].append(n)
            w5 = zs[max(0, i - 4): i + 1]
            if len(w5) == 5 and sum(1 for z in w5 if z * side > 1) >= 4 and zs[i] * side > 1:
                viol["R3"].append(n)
            w8 = zs[max(0, i - 7): i + 1]
            if len(w8) == 8 and all(z * side > 0 for z in w8):
                viol["R4"].append(n)
        w6 = [x["xbar"] for x in pts[max(0, i - 5): i + 1]]
        if len(w6) == 6 and (all(a < b for a, b in zip(w6, w6[1:])) or all(a > b for a, b in zip(w6, w6[1:]))):
            viol["TREND"].append(n)
    viol = {k: sorted(set(v)) for k, v in viol.items()}
    names = {"R1": "Point beyond 3 sigma", "R2": "2 of 3 beyond 2 sigma", "R3": "4 of 5 beyond 1 sigma",
             "R4": "8 in a row on one side", "TREND": "6 in a row trending", "RCHART": "Range above UCL"}
    ts = {p["subgroup"]: p["timestamp"] for p in pts}
    summary = [{"rule": k, "description": names[k], "first_subgroup": v[0], "first_at": ts[v[0]], "points": v}
               for k, v in viol.items() if v]
    first = min((s["first_at"] for s in summary), default=None)
    recent = pts[-10:]
    allv = [v for p in recent for v in p["values"]]
    sigma_w = mean(p["range"] for p in recent) / c["d2"]
    xbb = mean(p["xbar"] for p in recent)
    cpk = min(ch["usl"] - xbb, xbb - ch["lsl"]) / (3 * sigma_w)
    ppk = min(ch["usl"] - mean(allv), mean(allv) - ch["lsl"]) / (3 * pstdev(allv))
    dist = NormalDist(mean(allv), pstdev(allv))
    ppm_oos = (dist.cdf(ch["lsl"]) + 1 - dist.cdf(ch["usl"])) * 1e6
    oos = [{"subgroup": p["subgroup"], "value": v} for p in pts for v in p["values"] if v < ch["lsl"] or v > ch["usl"]]
    events = []
    if first:
        fdt = _ts(first)
        for e in q["events"]:
            edt = _ts(e["timestamp"])
            if e["line"] == line_id.strip().upper() and edt <= fdt + dt.timedelta(days=3) and edt >= _ts(pts[0]["timestamp"]) - dt.timedelta(days=10):
                h = round((fdt - edt).total_seconds() / 3600, 1)
                events.append({**e, "relation": "before first violation" if h >= 0 else "after first violation",
                               "hours_apart": abs(h)})
    return ok(line=line_id.upper(), line_name=line["name"], characteristic=key, description=ch["description"],
              unit=ch["unit"], spec={"nominal": ch["nominal"], "lsl": ch["lsl"], "usl": ch["usl"]},
              limits={"xbar_center": center, "xbar_ucl": round(ucl, 4), "xbar_lcl": round(lcl, 4),
                      "sigma_xbar": round(sig, 4), "r_center": rbar, "r_ucl": round(r_ucl, 4),
                      "basis": f"Phase I study {ph['established']}"},
              subgroups=[{k: p[k] for k in ("subgroup", "timestamp", "shift", "xbar", "range", "zone_sigma")} for p in pts],
              violations=summary, in_control=not summary,
              capability={"phase1_cpk": ph["cpk"], "recent_cpk": round(cpk, 2), "recent_ppk": round(ppk, 2),
                          "recent_mean": round(xbb, 4), "recent_sigma_within": round(sigma_w, 4),
                          "target_cpk": 1.33, "expected_ppm_out_of_spec": round(ppm_oos)},
              out_of_spec_readings=oos, events=events)


@hive_tool("enterprise")
def log_defect_pareto(line_id: str = "BW-2", weeks: int = 8, recent_weeks: int = 2) -> dict:
    """Build a defect Pareto for a Vantor production line and compare recent weeks against the baseline.

    Args:
        line_id: Production line, e.g. 'BW-2'.
        weeks: Number of weeks in the analysis window (2-8).
        recent_weeks: How many of the latest weeks count as 'recent' (1-3); the rest is the baseline.

    Returns:
        Pareto rows (count, share, cumulative share, ppm), recent vs baseline rate per defect with the change
        ratio and a 'significant increase' flag (>= 2x), process events in the recent weeks and linked customer
        complaints.
    """
    q = fixture("log_quality")
    line = q["lines"].get(line_id.strip().upper())
    if not line:
        return err(f"unknown line {line_id!r}", lines=sorted(q["lines"]))
    w = line["weekly"]
    n = max(2, min(int(weeks), len(w["weeks"])))
    r = max(1, min(int(recent_weeks), 3, n - 1))
    sl = slice(len(w["weeks"]) - n, None)
    weeks_l, prod = w["weeks"][sl], w["produced"][sl]
    total_prod = sum(prod)
    defects = {k: v[sl] for k, v in w["defects"].items()}
    tot = {k: sum(v) for k, v in defects.items()}
    all_def = sum(tot.values())
    rows, cum = [], 0
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
        cum += v
        base_p, rec_p = sum(prod[:-r]), sum(prod[-r:])
        base_rate = sum(defects[k][:-r]) / base_p * 1e6
        rec_rate = sum(defects[k][-r:]) / rec_p * 1e6
        ratio = rec_rate / base_rate if base_rate else None
        rows.append({"defect": k, "count": v, "share_pct": round(100 * v / all_def, 1),
                     "cumulative_pct": round(100 * cum / all_def, 1), "ppm": round(v / total_prod * 1e6),
                     "baseline_ppm": round(base_rate), "recent_ppm": round(rec_rate),
                     "change_x": round(ratio, 2) if ratio else None,
                     "significant_increase": bool(ratio and ratio >= 2), "weekly": defects[k]})
    recent_start = weeks_l[-r]
    yr, wk = int(recent_start[:4]), int(recent_start.split("W")[1])
    rs = dt.date.fromisocalendar(yr, wk, 1) - dt.timedelta(days=7)
    events = [e for e in q["events"] if e["line"] == line_id.strip().upper() and _d(e["timestamp"]) >= rs]
    sku = {"BW-2": "VAN-CM12", "BW-1": "VAN-AF55"}.get(line_id.strip().upper())
    complaints = [cc for cc in q["complaints"] if cc["sku"] == sku]
    rising = [x["defect"] for x in rows if x["significant_increase"]]
    return ok(line=line_id.upper(), line_name=line["name"], weeks=weeks_l, recent_weeks=weeks_l[-r:],
              produced=prod, total_defect_rate_ppm=round(all_def / total_prod * 1e6), pareto=rows,
              rising_defects=rising, events_in_window=events, complaints=complaints, note=w.get("note"))

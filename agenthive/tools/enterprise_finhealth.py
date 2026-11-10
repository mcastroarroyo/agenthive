"""Enterprise realm · financial services + healthcare tools (synthetic data, simulated actions).

Fictional organisations used consistently across fixtures, docs and the knowledge base:
  * Quillmark Bank — retail/commercial bank with the Quillmark Private Wealth division (Wealth Sentinel, Compliance,
    Fin. Insights, Exec Data Intel);
  * Corvina Health Network — hospitals, clinics and a clinical research office (After-Care, Trial Screener,
    Claim Denial, Clinical Docs).
Every client, patient, claim and transaction is synthetic (no PHI, no real customers). The tools are deterministic
decision support: they are not investment, legal, coding or medical advice, and a qualified human reviews every output.
"""
from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import re
import statistics

from ._base import err, fixture, hive_tool, ok

AS_OF = dt.date(2026, 11, 6)
_FIN_DISCLAIMER = ("Synthetic demo data. Decision support only — not investment advice; a licensed advisor and "
                   "supervisor must review before anything is presented to a client or traded.")
_HLT_DISCLAIMER = ("Synthetic patients only (no PHI). Decision support — not medical advice; a licensed clinician "
                   "must review and decide.")


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def _ref(prefix: str, *parts: object) -> str:
    return prefix + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:6].upper()


# =================================================================================================================
# Wealth Sentinel — Quillmark Private Wealth (portfolio exposure, mandate drift, rebalance, suitability)
# =================================================================================================================


def _wb() -> dict:
    return fixture("fin_wealth_book")


def _client(client: str) -> dict | None:
    q = (client or "").strip().lower()
    if not q:
        return None
    for c in _wb()["clients"]:
        if q == c["client_id"].lower() or q in c["household"].lower() or q in c["primary_contact"].lower():
            return c
    return None


def _no_client(client: str) -> dict:
    return err(f"no client matching {client!r}",
               clients=[f"{c['client_id']} · {c['household']}" for c in _wb()["clients"]])


def _mv(c: dict) -> dict[str, float]:
    secs = _wb()["securities"]
    return {h["symbol"]: sum(l["units"] for l in h["lots"]) * secs[h["symbol"]]["price"] for h in c["holdings"]}


def _pct(part: float, total: float) -> float:
    return round(part / total * 100, 2) if total else 0.0


def _class_weights(mv: dict[str, float]) -> dict[str, float]:
    secs, total = _wb()["securities"], sum(mv.values())
    out = {"equity": 0.0, "fixed_income": 0.0, "alternatives": 0.0, "cash": 0.0}
    for sym, v in mv.items():
        out[secs[sym]["asset_class"]] += v
    return {k: _pct(v, total) for k, v in out.items()}


def _targets(c: dict, total: float) -> dict[str, float]:
    """Model targets with the liquidity override (cash covers the 12-month liquidity need)."""
    model = _wb()["models"][c["model"]]["targets"]
    cash = max(model["cash"], round(c["liquidity_need_12m_usd"] / total * 100, 2) if total else 0)
    scale = (100 - cash) / (100 - model["cash"])
    return {k: (cash if k == "cash" else round(v * scale, 2)) for k, v in model.items()}


def _complex_ok(c: dict) -> bool:
    return bool(c["complex_products_ok"]) and c["risk_score"] >= _wb()["policy"]["complex_min_risk_score"]


def _restricted(c: dict, s: dict, sym: str) -> bool:
    r = c["restrictions"]
    return sym in r["exclude_symbols"] or any(t in r["exclude_sectors"] for t in s["esg_tags"])


def _profile_status(c: dict) -> dict:
    age = (AS_OF - _d(c["last_suitability_review"])).days
    kyc_overdue = _d(c["kyc_refresh_due"]) < AS_OF
    stale = age > _wb()["policy"]["profile_max_age_days"] or kyc_overdue
    return {"days_since_suitability_review": age, "kyc_refresh_due": c["kyc_refresh_due"],
            "kyc_overdue": kyc_overdue, "profile_current": not stale}


def _findings(c: dict, mv: dict[str, float]) -> list[dict]:
    """Every QPW-POL-07 rule evaluated on a (possibly pro-forma) portfolio."""
    wb = _wb()
    pol, secs, model = wb["policy"], wb["securities"], wb["models"][c["model"]]
    total = sum(mv.values())
    out: list[dict] = []

    def add(rule, severity, message, **kw):
        out.append({"rule": rule, "severity": severity, "message": message, **kw})

    ps = _profile_status(c)
    if not ps["profile_current"]:
        add("WS-1", "high", f"Suitability profile not current (review {ps['days_since_suitability_review']} days ago, "
            f"KYC due {c['kyc_refresh_due']}). No new recommendation until the profile is refreshed.")
    w = {s: _pct(v, total) for s, v in mv.items() if v > 0.5}
    complex_total = digital = illiquid = hy = 0.0
    for sym, wt in w.items():
        s = secs[sym]
        if _restricted(c, s, sym):
            add("WS-2", "high", f"{sym} breaches a client restriction ({', '.join(s['esg_tags']) or 'symbol'}).",
                symbol=sym, weight_pct=wt)
        if s["complex"]:
            complex_total += wt
            if not _complex_ok(c):
                add("WS-3", "high", f"{sym} is a complex product; client is not eligible (risk score "
                    f"{c['risk_score']}, complex_products_ok={c['complex_products_ok']}).", symbol=sym, weight_pct=wt)
        if s["leveraged"] and wt > pol["leveraged_max_pct"]:
            add("WS-3", "medium", f"Leveraged product {sym} at {wt}% exceeds {pol['leveraged_max_pct']}%.",
                symbol=sym, weight_pct=wt, limit_pct=pol["leveraged_max_pct"])
        if s["digital_asset"]:
            digital += wt
        if s["illiquid"]:
            illiquid += wt
        if s["sub_class"] == "high_yield":
            hy += wt
        if s["single_issuer"] and wt > pol["single_issuer_max_pct"]:
            add("WS-5", "high", f"Single-issuer concentration: {sym} is {wt}% (limit {pol['single_issuer_max_pct']}%).",
                symbol=sym, weight_pct=wt, limit_pct=pol["single_issuer_max_pct"])
        if s["sector_fund"] and wt > pol["sector_fund_max_pct"]:
            add("WS-6", "medium", f"Sector fund {sym} is {wt}% (limit {pol['sector_fund_max_pct']}%).",
                symbol=sym, weight_pct=wt, limit_pct=pol["sector_fund_max_pct"])
    if complex_total > pol["complex_total_max_pct"]:
        add("WS-3", "medium", f"Complex products total {round(complex_total, 2)}% (limit {pol['complex_total_max_pct']}%).")
    if digital and (c["risk_score"] < pol["digital_assets_min_risk_score"] or digital > pol["digital_assets_max_pct"]):
        add("WS-4", "high", f"Digital assets {round(digital, 2)}% (limit {pol['digital_assets_max_pct']}%, risk score "
            f">= {pol['digital_assets_min_risk_score']} required; client {c['risk_score']}).",
            weight_pct=round(digital, 2), limit_pct=pol["digital_assets_max_pct"])
    if illiquid > pol["illiquid_max_pct"]:
        add("WS-9", "medium", f"Illiquid holdings {round(illiquid, 2)}% (limit {pol['illiquid_max_pct']}%).")
    if hy > model["high_yield_cap_pct"]:
        add("WS-10", "medium", f"High-yield bonds {round(hy, 2)}% exceed the {model['label']} cap of "
            f"{model['high_yield_cap_pct']}%.", weight_pct=round(hy, 2), limit_pct=model["high_yield_cap_pct"])
    sectors: dict[str, float] = {}
    for sym, wt in w.items():
        for sec, f in secs[sym]["look_through"].items():
            sectors[sec] = sectors.get(sec, 0) + wt * f
    for sec, wt in sectors.items():
        if wt > pol["look_through_sector_soft_pct"]:
            add("WS-6", "medium", f"Look-through {sec} exposure {round(wt, 1)}% exceeds the "
                f"{pol['look_through_sector_soft_pct']}% soft limit (advisor review).", sector=sec,
                weight_pct=round(wt, 1))
    cw, tg, bands = _class_weights(mv), _targets(c, total), model["bands"]
    for k in cw:
        drift = round(cw[k] - tg[k], 2)
        if abs(drift) > bands[k]:
            add("WS-7", "high" if abs(drift) > 2 * bands[k] else "medium",
                f"{k} at {cw[k]}% vs target {tg[k]}% (band ±{bands[k]}pp): drift {drift:+}pp.", asset_class=k,
                drift_pp=drift)
    cash_mv = sum(v for s, v in mv.items() if secs[s]["asset_class"] == "cash")
    if cash_mv + 1 < c["liquidity_need_12m_usd"]:
        add("WS-8", "medium", f"Cash & money market USD {cash_mv:,.0f} below the 12-month liquidity need "
            f"USD {c['liquidity_need_12m_usd']:,.0f} ({c['liquidity_note']}).",
            shortfall_usd=round(c["liquidity_need_12m_usd"] - cash_mv))
    if c.get("employer_stock") and mv.get(c["employer_stock"]["symbol"], 0) > 0:
        add("WS-12", "info", c["employer_stock"]["note"], symbol=c["employer_stock"]["symbol"])
    if c["tax_status"] == "tax_deferred" and any(secs[s]["sub_class"] == "municipal" for s in w):
        add("INFO", "info", "Tax-exempt municipal bonds held in a tax-deferred account (asset-location inefficiency).")
    return out


def _priority(fs: list[dict]) -> int:
    return sum({"high": 10, "medium": 4, "low": 1}.get(f["severity"], 0) for f in fs)


@hive_tool("enterprise")
def fin_client_profile(client: str) -> dict:
    """Get a wealth client's suitability profile: risk score, mandate, objectives, liquidity needs and restrictions.

    Args:
        client: Client id (e.g. 'WM-1042') or household/contact name (e.g. 'Hartwell').

    Returns:
        KYC/suitability profile, model portfolio targets and bands, restrictions, recent notes and whether the
        profile is current (annual review and KYC refresh).
    """
    c = _client(client)
    if not c:
        return _no_client(client)
    model = _wb()["models"][c["model"]]
    prof = {k: v for k, v in c.items() if k != "holdings"}
    return ok(**prof, model_label=model["label"], model_targets_pct=model["targets"], bands_pp=model["bands"],
              complex_products_eligible=_complex_ok(c), profile_status=_profile_status(c),
              advisor=_wb()["advisor"], disclaimer=_FIN_DISCLAIMER)


@hive_tool("enterprise")
def fin_portfolio_exposure(client: str) -> dict:
    """Break a client's portfolio down by holding, asset class, look-through sector, region, liquidity and tax lots.

    Args:
        client: Client id (e.g. 'WM-1042') or household name.

    Returns:
        Holdings with market value, weight, unrealised gain and short/long-term lots; exposure by asset class,
        sub-class, look-through sector and region; complex/illiquid share; top holdings; cash vs liquidity need.
    """
    c = _client(client)
    if not c:
        return _no_client(client)
    secs = _wb()["securities"]
    mv = _mv(c)
    total = sum(mv.values())
    rows, sub, region, sector = [], {}, {}, {}
    for h in c["holdings"]:
        s, sym = secs[h["symbol"]], h["symbol"]
        units = sum(l["units"] for l in h["lots"])
        cost = sum(l["units"] * l["cost_per_unit"] for l in h["lots"])
        st = [l for l in h["lots"] if (AS_OF - _d(l["acquired"])).days <= 365]
        rows.append({"symbol": sym, "name": s["name"], "asset_class": s["asset_class"], "sub_class": s["sub_class"],
                     "units": round(units, 2), "price": s["price"], "market_value_usd": round(mv[sym], 2),
                     "weight_pct": _pct(mv[sym], total), "unrealised_gain_usd": round(mv[sym] - cost, 2),
                     "short_term_lots": len(st), "complex": s["complex"], "liquidity": s["redemption"]})
        sub[s["sub_class"]] = sub.get(s["sub_class"], 0) + mv[sym]
        region[s["region"]] = region.get(s["region"], 0) + mv[sym]
        for sec, f in s["look_through"].items():
            sector[sec] = sector.get(sec, 0) + mv[sym] * f
    rows.sort(key=lambda r: -r["market_value_usd"])
    cash = sum(v for s, v in mv.items() if secs[s]["asset_class"] == "cash")
    return ok(client_id=c["client_id"], household=c["household"], as_of=_wb()["as_of"],
              total_value_usd=round(total, 2), holdings=rows, by_asset_class_pct=_class_weights(mv),
              by_sub_class_pct={k: _pct(v, total) for k, v in sorted(sub.items(), key=lambda x: -x[1])},
              look_through_sector_pct={k: _pct(v, total) for k, v in sorted(sector.items(), key=lambda x: -x[1])},
              by_region_pct={k: _pct(v, total) for k, v in sorted(region.items(), key=lambda x: -x[1])},
              complex_products_pct=round(sum(r["weight_pct"] for r in rows if r["complex"]), 2),
              top_holdings=[r["symbol"] for r in rows[:5]],
              cash_and_equivalents_usd=round(cash, 2), liquidity_need_12m_usd=c["liquidity_need_12m_usd"],
              note="Look-through sector exposure is notional for leveraged products (2x).")


@hive_tool("enterprise")
def fin_mandate_check(client: str = "") -> dict:
    """Check a portfolio (or the advisor's whole book) against its mandate and the QPW-POL-07 policy limits.

    Args:
        client: Client id or household name. Leave empty to scan the whole book and rank clients by urgency.

    Returns:
        For one client: asset-class drift vs target and band, every rule finding (WS-1..WS-12) with severity and a
        priority score. For the book: one row per client with breach counts, worst issue and priority, sorted.
    """
    wb = _wb()
    if not client.strip():
        rows = []
        for c in wb["clients"]:
            mv = _mv(c)
            fs = _findings(c, mv)
            worst = sorted(fs, key=lambda f: {"high": 0, "medium": 1, "low": 2, "info": 3}[f["severity"]])
            rows.append({"client_id": c["client_id"], "household": c["household"], "model": c["model"],
                         "total_value_usd": round(sum(mv.values())), "high": sum(f["severity"] == "high" for f in fs),
                         "medium": sum(f["severity"] == "medium" for f in fs), "priority_score": _priority(fs),
                         "top_issue": worst[0]["message"] if worst else "Within mandate"})
        rows.sort(key=lambda r: -r["priority_score"])
        return ok(advisor=wb["advisor"], as_of=wb["as_of"], clients=rows,
                  book_value_usd=sum(r["total_value_usd"] for r in rows),
                  clients_in_breach=sum(1 for r in rows if r["high"] or r["medium"]))
    c = _client(client)
    if not c:
        return _no_client(client)
    mv = _mv(c)
    total = sum(mv.values())
    model = wb["models"][c["model"]]
    cw, tg = _class_weights(mv), _targets(c, total)
    drift = [{"asset_class": k, "current_pct": cw[k], "target_pct": tg[k], "band_pp": model["bands"][k],
              "drift_pp": round(cw[k] - tg[k], 2),
              "status": "breach" if abs(cw[k] - tg[k]) > model["bands"][k] else "within band"} for k in cw]
    fs = _findings(c, mv)
    return ok(client_id=c["client_id"], household=c["household"], model=c["model"], total_value_usd=round(total, 2),
              drift=drift, findings=fs, priority_score=_priority(fs),
              rebalance_required=any(f["rule"] in ("WS-2", "WS-3", "WS-4", "WS-5", "WS-6", "WS-7", "WS-9", "WS-10")
                                     and f["severity"] in ("high", "medium") for f in fs),
              advice_blocked=any(f["rule"] == "WS-1" for f in fs),
              targets_note="Cash target raised to cover the 12-month liquidity need when it exceeds the model cash.")


def _sell_lots(c: dict, sym: str, amount: float, lots_state: dict, avoid_st: bool) -> tuple[float, list[dict]]:
    """Sell up to `amount` USD of `sym`: losses first, then long-term gains (highest cost first), then short-term."""
    price = _wb()["securities"][sym]["price"]
    lots = lots_state[sym]

    def key(l):
        gain = price - l["cost_per_unit"]
        st = (AS_OF - _d(l["acquired"])).days <= 365
        return (0 if gain < 0 else 2 if st else 1, -l["cost_per_unit"])

    sold, detail = 0.0, []
    for l in sorted(lots, key=key):
        if sold >= amount - 0.5 or l["units"] <= 0:
            continue
        st = (AS_OF - _d(l["acquired"])).days <= 365
        if st and price > l["cost_per_unit"] and avoid_st:
            continue
        units = min(l["units"], round((amount - sold) / price, 2))
        if units <= 0:
            continue
        l["units"] = round(l["units"] - units, 4)
        sold += units * price
        detail.append({"acquired": l["acquired"], "units": units, "term": "short" if st else "long",
                       "realised_gain_usd": round(units * (price - l["cost_per_unit"]), 2)})
    return sold, detail


@hive_tool("enterprise")
def fin_propose_rebalance(client: str, avoid_short_term_gains: bool = True, min_trade_usd: float = 2500.0) -> dict:
    """Propose a tax-aware rebalance that cures policy breaches and returns asset classes to the mandate targets.

    Args:
        client: Client id or household name.
        avoid_short_term_gains: Do not sell tax lots held <= 365 days at a gain (default True).
        min_trade_usd: Skip trades smaller than this amount.

    Returns:
        Trade list (sell/buy, amount, units, reason, tax lots), staged sales for concentrated low-basis stock,
        realised gains and illustrative tax/trading-cost estimates, pre/post asset-class weights and any findings
        left after the trades. Pro-forma only — nothing is traded.
    """
    c = _client(client)
    if not c:
        return _no_client(client)
    wb = _wb()
    pol, secs, model = wb["policy"], wb["securities"], wb["models"][c["model"]]
    if not _profile_status(c)["profile_current"]:
        return ok(client_id=c["client_id"], household=c["household"], blocked=True, trades=[],
                  reason="WS-1: suitability profile/KYC not current — refresh the profile with the client before "
                         "proposing trades.", profile_status=_profile_status(c),
                  pre_trade_findings=_findings(c, _mv(c)), disclaimer=_FIN_DISCLAIMER)
    mv = _mv(c)
    total = sum(mv.values())
    lots_state = {h["symbol"]: [dict(l) for l in h["lots"]] for h in c["holdings"]}
    trades: dict[tuple[str, str], dict] = {}
    staged, notes = [], []

    def record(sym, action, amount, reason, lots=None):
        if amount < 1:
            return
        t = trades.setdefault((sym, action), {"symbol": sym, "name": secs[sym]["name"], "action": action,
                                               "amount_usd": 0.0, "reasons": [], "lots": []})
        t["amount_usd"] += amount
        if reason not in t["reasons"]:
            t["reasons"].append(reason)
        t["lots"] += lots or []
        mv[sym] = mv.get(sym, 0) + (amount if action == "buy" else -amount)

    avoid_st = avoid_short_term_gains and c["tax_status"] == "taxable"

    def sell(sym, amount, reason, cure=False):
        # policy cures (restricted / ineligible products) sell short-term lots too; tax-deferred accounts ignore lots
        sold, lots = _sell_lots(c, sym, min(amount, mv[sym]), lots_state, avoid_st and not cure)
        record(sym, "sell", sold, reason, lots)
        if sold + 1 < min(amount, mv[sym] + sold):
            notes.append(f"{sym}: USD {amount - sold:,.0f} not sold to avoid realising short-term gains.")
        if cure and any(l["term"] == "short" and l["realised_gain_usd"] > 0 for l in lots):
            notes.append(f"{sym}: short-term gain realised because the holding breaches policy ({reason[:4]}).")
        return sold

    # 1) policy breaches first (restrictions, ineligible complex products, concentration limits)
    for sym in sorted(mv, key=lambda s: -mv[s]):
        s, wt = secs[sym], _pct(mv[sym], total)
        if _restricted(c, s, sym):
            sell(sym, mv[sym], "WS-2 restricted holding — full exit", cure=True)
        elif s["complex"] and not _complex_ok(c):
            sell(sym, mv[sym], "WS-3 complex product not permitted for this client — full exit", cure=True)
        elif s["digital_asset"] and (wt > pol["digital_assets_max_pct"]
                                     or c["risk_score"] < pol["digital_assets_min_risk_score"]):
            keep = 0 if c["risk_score"] < pol["digital_assets_min_risk_score"] else pol["digital_assets_max_pct"]
            sell(sym, mv[sym] - total * keep / 100, "WS-4 digital assets outside policy", cure=True)
        elif s["leveraged"] and wt > pol["leveraged_max_pct"]:
            sell(sym, mv[sym] - total * pol["leveraged_max_pct"] / 100, "WS-3 leveraged product above 5%")
        elif s["single_issuer"] and wt > pol["single_issuer_max_pct"]:
            excess = mv[sym] - total * (pol["single_issuer_max_pct"] - 1) / 100
            cost = sum(l["units"] * l["cost_per_unit"] for l in lots_state[sym])
            gain_ratio = (mv[sym] - cost) / mv[sym]
            if c["tax_status"] == "taxable" and gain_ratio > pol["staged_sale_gain_ratio"]:
                n = pol["staged_tranches"]
                sell(sym, excess / n, f"WS-5 concentration — tranche 1 of {n} (staged for tax)")
                for i in range(1, n):
                    when = (AS_OF + dt.timedelta(days=91 * i)).isoformat()
                    staged.append({"symbol": sym, "tranche": i + 1, "planned_date": when,
                                   "amount_usd": round(excess / n, -2),
                                   "note": "Re-confirm price, trading window and tax position before each tranche."})
            else:
                sell(sym, excess, "WS-5 single-issuer concentration above 10%")
        elif s["sector_fund"] and wt > pol["sector_fund_max_pct"]:
            sell(sym, mv[sym] - total * (pol["sector_fund_max_pct"] - 1) / 100, "WS-6 sector fund above 20%")
        elif s["sub_class"] == "high_yield":
            cap = model["high_yield_cap_pct"]
            if wt > cap:
                sell(sym, mv[sym] - total * (cap - 1) / 100, f"WS-10 high-yield above the {cap}% cap")
    # proceeds settle to the money-market fund
    freed = sum(t["amount_usd"] for t in trades.values() if t["action"] == "sell")
    mv["QMMF"] = mv.get("QMMF", 0) + freed

    # 2) back to target by asset class (sell satellites before core funds; buy the model's core funds)
    tg = _targets(c, total)
    by_class: dict[str, float] = {}
    for sym, v in mv.items():
        by_class[secs[sym]["asset_class"]] = by_class.get(secs[sym]["asset_class"], 0) + v
    needs_rebalance = any(abs(_pct(by_class.get(k, 0), total) - tg[k]) > model["bands"][k] for k in tg) or trades
    tolerance = max(min_trade_usd, total * 0.005)     # leave in-band classes alone for tiny deltas
    if needs_rebalance:
        deltas = {k: total * tg[k] / 100 - by_class.get(k, 0) for k in ("equity", "fixed_income", "alternatives")}
        deltas = {k: d for k, d in deltas.items() if abs(d) >= tolerance}
        for k, delta in deltas.items():          # pass 1: sells (proceeds settle to the money-market fund)
            if delta >= 0:
                continue
            remaining = -delta
            core = model["core_funds"][k]
            cands = sorted([s for s in mv if secs[s]["asset_class"] == k and mv[s] > 1],
                           key=lambda s: (s in core, secs[s]["illiquid"], -mv[s]))
            for sym in cands:
                if remaining < min_trade_usd:
                    break
                if secs[sym]["illiquid"]:
                    notes.append(f"{sym} is only redeemable at its tender window ({secs[sym]['redemption']}).")
                got = sell(sym, min(remaining, mv[sym]), f"WS-7 reduce {k} toward {tg[k]}% target")
                remaining -= got
                mv["QMMF"] += got
        buys = {k: d for k, d in deltas.items() if d > 0}
        spendable = mv.get("QMMF", 0) - total * tg["cash"] / 100     # never spend the liquidity reserve
        scale = min(1.0, max(0.0, spendable) / sum(buys.values())) if buys else 0
        if buys and scale < 1:
            notes.append(f"Purchases scaled to {scale:.0%} to keep the cash/liquidity reserve intact.")
        for k, delta in buys.items():            # pass 2: buys into the model's core funds
            for sym, share in model["core_funds"][k].items():
                amt = (delta * scale * share) // 100 * 100
                if amt >= min_trade_usd:
                    record(sym, "buy", amt, f"WS-7 raise {k} toward {tg[k]}% target")
                    mv["QMMF"] -= amt
    # 3) assemble
    out, st_gain, lt_gain, cost = [], 0.0, 0.0, 0.0
    rates = c["illustrative_tax_rates"]
    for t in trades.values():
        if t["amount_usd"] < min_trade_usd and not any(r.startswith(("WS-2", "WS-3", "WS-4")) for r in t["reasons"]):
            continue
        price = secs[t["symbol"]]["price"]
        t["amount_usd"] = round(t["amount_usd"], 2)
        t["units"] = round(t["amount_usd"] / price, 2)
        t["reason"] = "; ".join(t.pop("reasons"))
        for l in t["lots"]:
            if l["term"] == "short":
                st_gain += l["realised_gain_usd"]
            else:
                lt_gain += l["realised_gain_usd"]
        bps = pol["single_stock_cost_bps"] if secs[t["symbol"]]["single_issuer"] else pol["trading_cost_bps"]
        cost += t["amount_usd"] * bps / 10000
        if secs[t["symbol"]]["illiquid"] and t["action"] == "sell":
            t["execution"] = "scheduled — " + secs[t["symbol"]]["redemption"]
        elif c.get("employer_stock") and t["symbol"] == c["employer_stock"]["symbol"]:
            t["execution"] = "pre-clearance required — " + c["employer_stock"]["note"]
        else:
            t["execution"] = "next trading day"
        if not t["lots"]:
            t.pop("lots")
        out.append(t)
    out.sort(key=lambda t: (t["action"] != "sell", -t["amount_usd"]))
    tax = max(st_gain, 0) * rates["short_term"] + max(lt_gain, 0) * rates["long_term"]
    sells = sum(t["amount_usd"] for t in out if t["action"] == "sell")
    buys = sum(t["amount_usd"] for t in out if t["action"] == "buy")
    pre = _class_weights(_mv(c))
    post_findings = [f for f in _findings(c, mv) if f["severity"] != "info"]
    return ok(client_id=c["client_id"], household=c["household"], model=c["model"], total_value_usd=round(total, 2),
              targets_pct=tg, trades=out, staged_sales=staged,
              summary={"sells_usd": round(sells, 2), "buys_usd": round(buys, 2),
                       "net_to_money_market_usd": round(sells - buys, 2),
                       "realised_short_term_gain_usd": round(st_gain, 2),
                       "realised_long_term_gain_usd": round(lt_gain, 2),
                       "estimated_tax_usd": round(tax, 2), "estimated_trading_cost_usd": round(cost, 2),
                       "tax_note": f"Illustrative rates ST {rates['short_term']:.0%} / LT {rates['long_term']:.0%} "
                                   f"({c['tax_status']}); confirm with the client's tax adviser."},
              pre_trade_weights_pct=pre, post_trade_weights_pct=_class_weights(mv),
              remaining_findings=post_findings, notes=notes, pro_forma=True, disclaimer=_FIN_DISCLAIMER)


@hive_tool("enterprise")
def fin_suitability_check(client: str, trades: list[dict]) -> dict:
    """Check proposed trades against the client's profile and QPW-POL-07 suitability rules before they are presented.

    Args:
        client: Client id or household name.
        trades: List of {"symbol": str, "action": "buy"|"sell", "amount_usd": number}. Use the exact symbols from
            the portfolio or the rebalance proposal (e.g. 'QBTCX', 'QUSTE').

    Returns:
        Verdict (suitable / suitable_with_conditions / not_suitable / blocked), per-trade rule results with rule ids,
        post-trade findings and the conditions an advisor must satisfy.
    """
    c = _client(client)
    if not c:
        return _no_client(client)
    if not trades:
        return err("trades must not be empty")
    wb = _wb()
    pol, secs = wb["policy"], wb["securities"]
    before = _mv(c)
    mv = dict(before)
    total = sum(mv.values())
    results, conditions = [], []
    for t in trades:
        sym = str(t.get("symbol", "")).upper()
        action = str(t.get("action", "")).lower()
        try:
            amt = float(t.get("amount_usd") or 0)
        except (TypeError, ValueError):
            amt = 0.0
        if sym not in secs or action not in ("buy", "sell") or amt <= 0:
            results.append({"trade": t, "result": "fail", "rules": [{"rule": "INPUT", "detail":
                            "unknown symbol, action or amount", "known_symbols": sorted(secs)}]})
            continue
        s, rules = secs[sym], []
        if action == "sell":
            if amt > mv.get(sym, 0) + 1:
                rules.append({"rule": "WS-11", "status": "fail", "detail": f"Sell USD {amt:,.0f} exceeds holding "
                              f"USD {mv.get(sym, 0):,.0f}."})
            if s["illiquid"]:
                rules.append({"rule": "WS-9", "status": "condition", "detail": s["redemption"]})
            if c.get("employer_stock") and sym == c["employer_stock"]["symbol"]:
                rules.append({"rule": "WS-12", "status": "condition", "detail": c["employer_stock"]["note"]})
            mv[sym] = max(0.0, mv.get(sym, 0) - amt)
            mv["QMMF"] = mv.get("QMMF", 0) + amt
        else:
            if _restricted(c, s, sym):
                rules.append({"rule": "WS-2", "status": "fail", "detail": f"{sym} conflicts with client restrictions."})
            if s["complex"] and not _complex_ok(c):
                rules.append({"rule": "WS-3", "status": "fail", "detail": "Complex product; client not eligible."})
            mv[sym] = mv.get(sym, 0) + amt
            mv["QMMF"] = mv.get("QMMF", 0) - amt
            post = _pct(mv[sym], total)
            if s["digital_asset"]:
                dig = sum(_pct(v, total) for k, v in mv.items() if secs[k]["digital_asset"])
                if c["risk_score"] < pol["digital_assets_min_risk_score"]:
                    rules.append({"rule": "WS-4", "status": "fail", "detail": "Digital assets need risk score >= 7."})
                elif dig > pol["digital_assets_max_pct"]:
                    cap = total * pol["digital_assets_max_pct"] / 100 - (mv[sym] - amt)
                    rules.append({"rule": "WS-4", "status": "fail", "detail": f"Digital assets would be {dig:.1f}% "
                                  f"(limit {pol['digital_assets_max_pct']}%). Maximum additional purchase about "
                                  f"USD {max(cap, 0):,.0f}."})
            if s["single_issuer"] and post > pol["single_issuer_max_pct"]:
                rules.append({"rule": "WS-5", "status": "fail", "detail": f"{sym} would be {post}% (limit 10%)."})
            if s["sector_fund"] and post > pol["sector_fund_max_pct"]:
                rules.append({"rule": "WS-6", "status": "fail", "detail": f"{sym} would be {post}% (limit 20%)."})
            if s["illiquid"] and sum(_pct(v, total) for k, v in mv.items() if secs[k]["illiquid"]) > pol["illiquid_max_pct"]:
                rules.append({"rule": "WS-9", "status": "fail", "detail": "Illiquid holdings would exceed 15%."})
            if mv["QMMF"] < -1:
                rules.append({"rule": "FUNDING", "status": "condition", "detail": "Purchase needs funding from sales "
                              f"(cash short by USD {-mv['QMMF']:,.0f})."})
        status = "fail" if any(r["status"] == "fail" for r in rules) else \
            "condition" if rules else "pass"
        results.append({"trade": {"symbol": sym, "action": action, "amount_usd": amt}, "result": status,
                        "rules": rules or [{"rule": "ALL", "status": "pass", "detail": "No rule triggered."}]})
        conditions += [r["detail"] for r in rules if r["status"] == "condition"]
    post = _findings(c, mv)
    pre_rules = {(f["rule"], f.get("symbol"), f.get("asset_class")) for f in _findings(c, before)}
    new = [f for f in post if (f["rule"], f.get("symbol"), f.get("asset_class")) not in pre_rules
           and f["severity"] in ("high", "medium")]
    remaining = [f for f in post if f["severity"] in ("high", "medium")]
    blocked = any(f["rule"] == "WS-1" for f in post)
    if blocked:
        verdict = "blocked"
    elif any(r["result"] == "fail" for r in results) or any(f["severity"] == "high" for f in new):
        verdict = "not_suitable"
    elif conditions or remaining:
        verdict = "suitable_with_conditions"
    else:
        verdict = "suitable"
    return ok(client_id=c["client_id"], household=c["household"], verdict=verdict, trade_results=results,
              new_findings_after_trades=new, remaining_findings_after_trades=remaining,
              conditions=sorted(set(conditions)), post_trade_weights_pct=_class_weights(mv),
              policy="QPW-POL-07 Investment Policy & Suitability Standard", disclaimer=_FIN_DISCLAIMER)


@hive_tool("enterprise", kind="action")
def fin_log_advice_record(client: str, summary: str, trades: list[dict], suitability_verdict: str) -> dict:
    """File the record of advice for a proposal and queue it for supervisory approval (simulated).

    Args:
        client: Client id or household name.
        summary: One-paragraph rationale presented to the client.
        trades: The trades recommended, as {"symbol", "action", "amount_usd"}.
        suitability_verdict: Verdict returned by fin_suitability_check.

    Returns:
        Record-of-advice id, supervisory queue status and retention period. Refuses proposals that failed
        suitability or are blocked.
    """
    c = _client(client)
    if not c:
        return _no_client(client)
    if suitability_verdict not in ("suitable", "suitable_with_conditions"):
        return err("A record of advice can only be filed for a proposal that passed suitability; fix the trades "
                   "and re-run fin_suitability_check.", verdict=suitability_verdict)
    if not summary.strip() or not trades:
        return err("summary and trades are required")
    rid = _ref("ROA-2026-", c["client_id"], summary[:80], len(trades))
    return ok(record_id=rid, client_id=c["client_id"], record_status="pending supervisory approval (T+1)",
              supervisor=_wb()["advisor"]["supervisor"], trades=len(trades), retention="7 years (QPW-POL-07 §8)",
              client_approval="required before any order is placed", simulated=True)


# =================================================================================================================
# Compliance — Quillmark Bank (transaction monitoring, screening, control mapping, case management)
# =================================================================================================================

_TM_RULES = {
    "TM-01": ("Structuring below the cash reporting threshold", 45),
    "TM-02": ("Rapid movement of funds (pass-through)", 50),
    "TM-03": ("High-risk jurisdiction transfers", 30),
    "TM-04": ("Outflow velocity vs expected profile", 25),
    "TM-05": ("Dormant account reactivation", 30),
    "TM-06": ("Round-amount outgoing wires", 10),
}
_OUT = ("wire_out", "ach_out")
_IN = ("wire_in", "ach_in", "cash_deposit")


def _ts(t: dict) -> dt.datetime:
    return dt.datetime.fromisoformat(t["timestamp"])


def _account_alerts(acc: dict, txns: list[dict], window_days: int, high_risk: list[str]) -> list[dict]:
    alerts = []

    def alert(rule, evidence, detail, weight=None):
        aid = f"AL-{acc['account_id'][-5:]}-{rule.replace('-', '')}"
        n = sum(1 for a in alerts if a["rule"] == rule)
        alerts.append({"alert_id": aid + (f"-{n + 1}" if n else ""), "rule": rule,
                       "rule_name": _TM_RULES[rule][0], "weight": weight or _TM_RULES[rule][1],
                       "evidence_txn_ids": [t["txn_id"] for t in evidence],
                       "evidence_total_usd": round(sum(t["amount_usd"] for t in evidence), 2), "detail": detail})

    cash = sorted([t for t in txns if t["type"] == "cash_deposit" and 8000 <= t["amount_usd"] < 10000], key=_ts)
    best: list[dict] = []
    for i, t in enumerate(cash):
        grp = [u for u in cash[i:] if (_ts(u) - _ts(t)).days < 7]
        if len(grp) > len(best):
            best = grp
    if len(best) >= 3 and sum(t["amount_usd"] for t in best) >= 25000:
        alert("TM-01", best, f"{len(best)} cash deposits of USD 8,000-9,999 within 7 days "
              f"({len({t['channel'] for t in best})} branches), total USD {sum(t['amount_usd'] for t in best):,.0f}.")
    for t in [t for t in txns if t["type"] == "wire_in" and t["amount_usd"] >= 50000]:
        outs = [u for u in txns if u["type"] == "wire_out" and dt.timedelta(0) < _ts(u) - _ts(t) <= dt.timedelta(hours=72)]
        moved = sum(u["amount_usd"] for u in outs)
        if moved >= 0.8 * t["amount_usd"]:
            hours = max((_ts(u) - _ts(t)).total_seconds() / 3600 for u in outs)
            alert("TM-02", [t, *outs], f"USD {t['amount_usd']:,.0f} received and {moved / t['amount_usd']:.0%} sent "
                  f"out within {hours:.0f} hours to {len(outs)} counterparties.")
    hr = [t for t in txns if t["counterparty_country"] in high_risk and t["amount_usd"] >= 10000]
    if hr:
        tot = sum(t["amount_usd"] for t in hr)
        alert("TM-03", hr, f"{len(hr)} transfers with high-risk jurisdictions "
              f"({', '.join(sorted({t['counterparty_country'] for t in hr}))}), total USD {tot:,.0f}.",
              weight=45 if tot >= 100000 else 30)
    out_total = sum(t["amount_usd"] for t in txns if t["type"] in _OUT)
    expected = acc["expected_monthly_outflow_usd"] * window_days / 30
    if expected and out_total >= 5 * expected:
        alert("TM-04", [t for t in txns if t["type"] in _OUT], f"Outflows USD {out_total:,.0f} are "
              f"{out_total / expected:.1f}x the expected USD {expected:,.0f} for {window_days} days.")
    if txns:
        first = min(_ts(t) for t in txns).date()
        idle = (first - _d(acc["last_activity_before_window"])).days
        inflow = sum(t["amount_usd"] for t in txns if t["type"] in _IN)
        if idle >= 365 and inflow >= 50000:
            alert("TM-05", [t for t in txns if t["type"] in _IN], f"Account idle {idle} days, then USD "
                  f"{inflow:,.0f} received.")
    rnd = [t for t in txns if t["type"] == "wire_out" and t["amount_usd"] % 10000 == 0]
    if len(rnd) >= 3:
        alert("TM-06", rnd, f"{len(rnd)} outgoing wires in exact multiples of USD 10,000.")
    return alerts


@hive_tool("enterprise")
def fin_run_aml_rules(account_id: str = "", window_days: int = 30) -> dict:
    """Run the AML transaction-monitoring scenarios (TM-01..TM-06) over an account or all monitored accounts.

    Args:
        account_id: Account id such as 'ACC-30245'. Leave empty to scan every monitored account.
        window_days: Look-back window in days ending today (default 30).

    Returns:
        Per account: KYC profile, transactions reviewed, alerts (rule, evidence transaction ids, amounts, detail),
        risk score 0-100, severity and the next step required by the AML rulebook.
    """
    data = fixture("fin_aml")
    accounts = {a["account_id"]: a for a in data["accounts"]}
    if account_id and account_id.upper() not in accounts:
        return err(f"unknown account {account_id!r}", accounts=[f"{k} · {v['name']}" for k, v in accounts.items()])
    if not 1 <= window_days <= 365:
        return err("window_days must be between 1 and 365")
    start = dt.datetime.combine(AS_OF - dt.timedelta(days=window_days), dt.time())
    out, clean = [], []
    for aid in ([account_id.upper()] if account_id else list(accounts)):
        acc = accounts[aid]
        txns = sorted([t for t in data["transactions"] if t["account_id"] == aid and _ts(t) >= start], key=_ts)
        alerts = _account_alerts(acc, txns, window_days, data["high_risk_jurisdictions"])
        mult = 1.5 if acc["kyc_risk"] == "high" else 1.0
        score = min(100, round(sum(a["weight"] for a in alerts) * mult))
        sev = "high" if score >= 70 else "medium" if score >= 40 else "low" if alerts else "none"
        step = {"high": "Escalate: open an investigation case within 2 business days (FCP-3 §5); hold further "
                        "outgoing wires pending review.",
                "medium": "Level-1 analyst review within 5 business days; request source-of-funds if unexplained.",
                "low": "Document disposition and close; monitor.", "none": "No alert."}[sev]
        row = {"account_id": aid, "name": acc["name"], "customer_type": acc["customer_type"],
               "business": acc["business"], "kyc_risk": acc["kyc_risk"], "birth_year": acc.get("birth_year"),
               "expected_monthly_outflow_usd": acc["expected_monthly_outflow_usd"], "transactions_reviewed": len(txns),
               "alerts": alerts, "risk_score": score, "severity": sev, "next_step": step,
               "counterparties": sorted({t["counterparty"] for t in txns if t["type"] not in ("cash_deposit", "card")})}
        if account_id:
            row["transactions"] = txns
        (out if alerts or account_id else clean).append(row)
    out.sort(key=lambda r: -r["risk_score"])
    return ok(as_of=data["as_of"], window_days=window_days, accounts=out,
              accounts_without_alerts=[f"{r['account_id']} · {r['name']}" for r in clean],
              rulebook="Quillmark AML Transaction Monitoring Rulebook v4.2 (synthetic)")


_SUFFIX = {"llc", "ltd", "inc", "sa", "srl", "plc", "co", "corp", "corporation", "company", "pllc", "gmbh", "the"}
_ABBR = {"svcs": "services", "svc": "services", "intl": "international", "&": "and", "mgmt": "management"}


def _norm_name(name: str) -> list[str]:
    toks = re.findall(r"[a-z0-9&]+", name.lower().replace(".", ""))
    return [_ABBR.get(t, t) for t in toks if t not in _SUFFIX]


def _name_score(a: str, b: str) -> float:
    ta, tb = _norm_name(a), _norm_name(b)
    s1 = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    s2 = difflib.SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    score = max(s1, s2)
    if len(ta) >= 2 and len(tb) >= 2 and ta[-1] == tb[-1]:
        short, long_ = (ta, tb) if len(ta[0]) <= len(tb[0]) else (tb, ta)
        if len(short[0]) == 1 and long_[0].startswith(short[0]):
            score = max(score, 0.86)      # initial + surname (e.g. 'K. Arvelo' vs 'Kasimir Arvelo')
    return round(score, 3)


@hive_tool("enterprise")
def fin_screen_party(name: str, birth_year: int = 0, country: str = "") -> dict:
    """Screen a customer or counterparty name against the synthetic sanctions, PEP and adverse-media lists.

    Args:
        name: Person or entity name as it appears on the transaction or account.
        birth_year: Year of birth for individuals (0 if unknown) — used to discount false positives.
        country: Country/jurisdiction of the party, if known.

    Returns:
        Candidate matches with fuzzy score (0-1), list type, programme or position, and a disposition:
        strong potential match (>= 0.92), potential match (0.85-0.92) or weak (0.80-0.85), with the required action.
    """
    if len(name.strip()) < 3:
        return err("name too short to screen")
    hits = []
    for e in fixture("fin_aml")["watchlist"]:
        sc = _name_score(name, e["name"])
        if sc < 0.80:
            continue
        disp = "strong potential match" if sc >= 0.92 else "potential match" if sc >= 0.85 else "weak match"
        why = []
        if birth_year and e.get("birth_year") and abs(birth_year - e["birth_year"]) > 2:
            disp, _ = "likely false positive", why.append(f"birth year {birth_year} vs listed {e['birth_year']}")
        if country and e.get("countries") and country not in e["countries"]:
            why.append(f"country {country} not in listed {e['countries']}")
        hits.append({**e, "score": sc, "disposition": disp, "discounting_factors": why})
    hits.sort(key=lambda h: -h["score"])
    top = hits[0]["disposition"] if hits else "no match"
    action = {"strong potential match": "Hold the payment/relationship and escalate to Sanctions Compliance within "
                                        "24 hours (SP-2 §5). Do not tip off the customer.",
              "potential match": "Analyst review within 24 hours: compare identifiers (DOB, address, registration "
                                 "number) before releasing.",
              "weak match": "Document and clear with rationale.",
              "likely false positive": "Clear with documented rationale (identifier mismatch); retain evidence.",
              "no match": "No action."}[top]
    return ok(name=name, matches=hits, outcome=top, required_action=action,
              lists_screened=["Sanctions (synthetic consolidated list)", "PEP (synthetic)", "Adverse media (synthetic)"])


@hive_tool("enterprise")
def fin_map_controls(topic: str, period: str = "2026-Q3") -> dict:
    """Map a regulatory topic to Quillmark's internal policies and controls, with test results and audit evidence.

    Args:
        topic: Topic or keyword, e.g. 'aml_transaction_monitoring', 'sanctions', 'KYC refresh', 'suitability',
            'complaints', 'data retention'.
        period: Testing period (only '2026-Q3' is available in the demo).

    Returns:
        Regulatory obligation, mapped controls (owner, frequency, policy reference), last test (sample, exceptions,
        pass rate, effectiveness rating), evidence items, open issues and evidence gaps.
    """
    data = fixture("fin_controls")
    if period != data["period"]:
        return err(f"no test results for {period!r}", available=[data["period"]])
    q = topic.strip().lower().replace("_", " ")
    key = next((k for k in data["topics"] if q == k.replace("_", " ")), None) or next(
        (k for k, v in data["topics"].items() if any(w in q or q in w for w in v["keywords"])), None)
    if not key:
        return err(f"no controls mapped to {topic!r}", topics=sorted(data["topics"]))
    t = data["topics"][key]
    controls = []
    for c in t["controls"]:
        rate = c["last_test"]["pass_rate_pct"]
        rating = "effective" if rate >= 95 else "needs improvement" if rate >= 85 else "deficient"
        if any("(critical)" in i.lower() for i in c["open_issues"]):
            rating = "deficient"
        gaps = [] if any(e["type"] == "sample workpaper" for e in c["evidence"]) else \
            ["No sample-test workpaper on file — examiners usually ask for one."]
        controls.append({**c, "rating": rating, "evidence_gaps": gaps})
    return ok(topic=key, period=period, obligation=t["obligation"], controls=controls,
              summary={r: sum(1 for c in controls if c["rating"] == r)
                       for r in ("effective", "needs improvement", "deficient")},
              rating_scale=data["rating_scale"], evidence_store="GRC evidence vault (simulated)")


@hive_tool("enterprise", kind="action")
def fin_open_compliance_case(account_id: str, alert_ids: list[str], summary: str, priority: str = "high") -> dict:
    """Open an investigation case in the financial-crime case manager for reviewed alerts (simulated).

    Args:
        account_id: Account under investigation, e.g. 'ACC-30245'.
        alert_ids: Alert ids from fin_run_aml_rules (e.g. ['AL-30245-TM02']).
        summary: Investigator-ready summary of the activity and why it is unusual.
        priority: 'high', 'medium' or 'low'.

    Returns:
        Case id, assigned queue, decision due date and filing deadline guidance (simulated, nothing is filed).
    """
    accounts = {a["account_id"] for a in fixture("fin_aml")["accounts"]}
    if account_id.upper() not in accounts:
        return err(f"unknown account {account_id!r}")
    if priority not in ("high", "medium", "low"):
        return err("priority must be high, medium or low")
    if not alert_ids or len(summary.strip()) < 30:
        return err("alert_ids and a summary of at least 30 characters are required")
    days = {"high": 10, "medium": 20, "low": 30}[priority]
    return ok(case_id=_ref("FCC-2026-", account_id, ",".join(sorted(alert_ids))), account_id=account_id.upper(),
              alert_ids=alert_ids, priority=priority, queue="Financial Intelligence Unit — investigations",
              decision_due=(AS_OF + dt.timedelta(days=days)).isoformat(),
              filing_guidance="If activity is determined suspicious, the regulatory report is due within 30 calendar "
                              "days of determination (FCP-3 §6). The customer must not be informed.",
              simulated=True)


# =================================================================================================================
# Fin. Insights / Exec Data Intel helpers (applied to BigQuery results)
# =================================================================================================================


@hive_tool("enterprise")
def fin_flag_material_variances(lines: list[dict], threshold_usd: float = 250000.0, threshold_pct: float = 5.0) -> dict:
    """Apply the FP&A materiality policy to actual-vs-budget (or forecast) lines and flag what needs commentary.

    Args:
        lines: List of {"line": str, "actual": number, "plan": number, "line_type": "revenue"|"expense"} — e.g. P&L
            lines or cost centres from a BigQuery query. 'plan' is the budget or forecast amount.
        threshold_usd: Absolute variance threshold (policy default USD 250,000).
        threshold_pct: Relative variance threshold in % of plan (policy default 5%).

    Returns:
        Each line with variance, variance %, favourable/unfavourable, material flag and the commentary required,
        ranked by absolute variance, plus the net impact on pre-tax profit.
    """
    if not lines:
        return err("lines must not be empty")
    out, net = [], 0.0
    for ln in lines:
        try:
            actual, plan = float(ln["actual"]), float(ln.get("plan", ln.get("budget")))
        except (KeyError, TypeError, ValueError):
            return err(f"each line needs numeric 'actual' and 'plan': {ln}")
        typ = str(ln.get("line_type", "expense")).lower()
        var = actual - plan
        pct = var / abs(plan) * 100 if plan else 0.0
        fav = var > 0 if typ == "revenue" else var < 0
        net += var if typ == "revenue" else -var
        material = (abs(var) >= threshold_usd and abs(pct) >= threshold_pct) or abs(var) >= 1_000_000
        need = ("root cause, owner and recovery action" if not fav else "driver and whether it is one-off or "
                "run-rate") if material else "none"
        out.append({"line": ln.get("line", "?"), "line_type": typ, "actual": round(actual, 2), "plan": round(plan, 2),
                    "variance": round(var, 2), "variance_pct": round(pct, 1),
                    "direction": "favourable" if fav else "unfavourable" if var else "on plan",
                    "material": material, "commentary_required": need})
    out.sort(key=lambda r: -abs(r["variance"]))
    return ok(lines=out, material_count=sum(r["material"] for r in out),
              net_profit_impact=round(net, 2),
              policy=f"Material if |variance| >= USD {threshold_usd:,.0f} AND >= {threshold_pct}% of plan, or "
                     "|variance| >= USD 1,000,000 (FP&A Variance Policy FIN-POL-12).")


@hive_tool("enterprise")
def fin_detect_anomalies(series: list[dict], z_threshold: float = 3.0) -> dict:
    """Find anomalies and the trend in a KPI time series (robust z-score on median/MAD, least-squares slope).

    Args:
        series: Ordered list of {"period": str, "value": number} — e.g. monthly NPS or daily failed-transaction %
            returned by a BigQuery query. At least 6 points.
        z_threshold: Robust z-score above which a point is an anomaly (default 3.0).

    Returns:
        Anomalous periods with value, robust z and direction; trend slope per period and total % change; last vs
        previous period and vs 12 periods earlier when available.
    """
    try:
        pts = [(str(p["period"]), float(p["value"])) for p in series]
    except (KeyError, TypeError, ValueError):
        return err('series items need "period" and numeric "value"')
    if len(pts) < 6:
        return err("need at least 6 points")
    vals = [v for _, v in pts]
    med = statistics.median(vals)
    mad = statistics.median(abs(v - med) for v in vals) * 1.4826
    scale = mad or statistics.pstdev(vals) or 1.0
    anomalies = [{"period": p, "value": v, "robust_z": round((v - med) / scale, 2),
                  "direction": "above" if v > med else "below"}
                 for p, v in pts if abs(v - med) / scale >= z_threshold]
    n = len(vals)
    xbar, ybar = (n - 1) / 2, sum(vals) / n
    slope = sum((i - xbar) * (v - ybar) for i, v in enumerate(vals)) / sum((i - xbar) ** 2 for i in range(n))
    res = {"points": n, "median": round(med, 4), "anomalies": anomalies,
           "trend": {"slope_per_period": round(slope, 4),
                     "direction": "rising" if slope > 0.001 * abs(ybar) else "falling" if slope < -0.001 * abs(ybar)
                     else "flat",
                     "change_first_to_last_pct": round((vals[-1] - vals[0]) / abs(vals[0]) * 100, 1) if vals[0] else None},
           "last": {"period": pts[-1][0], "value": vals[-1],
                    "vs_previous_pct": round((vals[-1] - vals[-2]) / abs(vals[-2]) * 100, 1) if vals[-2] else None}}
    if n >= 13 and vals[-13]:
        res["last"]["vs_12_periods_earlier_pct"] = round((vals[-1] - vals[-13]) / abs(vals[-13]) * 100, 1)
    return ok(**res, method=f"robust z = (x - median) / (1.4826 x MAD); threshold {z_threshold}")


# =================================================================================================================
# After-Care — Corvina Transitional Care Program
# =================================================================================================================

_EMERGENCY_TERMS = ["chest pain", "chest pressure", "severe shortness of breath", "can't breathe", "cannot breathe",
                    "breathless at rest", "short of breath at rest", "fainted", "passed out", "unresponsive",
                    "confused", "confusion", "slurred speech", "face drooping", "one-sided weakness",
                    "coughing up blood", "vomiting blood", "heavy bleeding", "seizure", "blue lips", "suicidal"]
_NEGATION = re.compile(r"^\s*(no|denies|denied|without|not|none)\b", re.I)
_RANK = {"routine": 0, "same_day": 1, "urgent": 2, "emergency": 3}


def _ac(patient_id: str) -> dict | None:
    return fixture("hlt_aftercare")["patients"].get(patient_id.strip().upper())


@hive_tool("enterprise")
def hlt_get_care_plan(patient_id: str) -> dict:
    """Get a discharged (synthetic) patient's care plan: diagnosis, medications, instructions, appointments, red flags.

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-A101'.

    Returns:
        Admission summary, comorbidities, medication schedule, self-care instructions, upcoming appointments,
        condition-specific red flags, recent home readings and the care-team contacts.
    """
    p = _ac(patient_id)
    if not p:
        return err(f"unknown patient {patient_id!r}", patients=sorted(fixture("hlt_aftercare")["patients"]))
    days = (AS_OF - _d(p["admission"]["discharged"])).days
    plan = {k: v for k, v in p.items() if k not in ("adherence",)}
    return ok(patient_id=patient_id.upper(), days_since_discharge=days, **plan,
              care_team=fixture("hlt_aftercare")["care_team"], disclaimer=_HLT_DISCLAIMER)


@hive_tool("enterprise")
def hlt_triage_symptoms(patient_id: str, symptoms: list[str], weight_kg: float = 0.0, temperature_c: float = 0.0,
                        heart_rate: int = 0, systolic_bp: int = 0, spo2_pct: int = 0, glucose_mg_dl: int = 0,
                        pain_score: int = -1) -> dict:
    """Triage a post-discharge check-in against the transitional-care protocol and the patient's red flags.

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-A101'.
        symptoms: Symptoms the patient HAS, in plain English words (translate if the patient wrote in another
            language), e.g. ['ankles swollen', 'more breathless walking'].
            Do not include negated symptoms ('no chest pain'); they are ignored if passed.
        weight_kg: Today's weight in kg (0 if not reported).
        temperature_c: Temperature in Celsius (0 if not reported).
        heart_rate: Heart rate in beats/min (0 if not reported).
        systolic_bp: Systolic blood pressure in mmHg (0 if not reported).
        spo2_pct: Oxygen saturation % (0 if not reported).
        glucose_mg_dl: Blood glucose in mg/dL (0 if not reported).
        pain_score: Pain 0-10 (-1 if not reported).

    Returns:
        Disposition (emergency / urgent / same_day / routine), every rule that fired with its source, the response
        time target, recommended actions and safety-netting advice to read back. A nurse must confirm.
    """
    p = _ac(patient_id)
    if not p:
        return err(f"unknown patient {patient_id!r}", patients=sorted(fixture("hlt_aftercare")["patients"]))
    present, ignored = [], []
    for s in symptoms:
        for clause in re.split(r"[,;]| and | but ", s):
            if clause.strip():
                (ignored if _NEGATION.search(clause) else present).append(clause.strip().lower())
    text = " | ".join(present)
    fired: list[dict] = []

    def fire(disp, rule, finding):
        fired.append({"disposition": disp, "rule": rule, "finding": finding})

    for term in _EMERGENCY_TERMS:
        if term in text:
            fire("emergency", "UNIVERSAL", f"'{term}' reported")
    for rf in p["red_flags"]:
        hit = next((k for k in rf["keywords"] if k in text), None)
        if hit:
            fire(rf["disposition"], rf["id"], f"{rf['finding']} ('{hit}')")
    if weight_kg and p.get("weight_rules"):
        wr, log = p["weight_rules"], p["home_readings"].get("weight_kg", [])
        gain_d = round(weight_kg - p["discharge_weight_kg"], 1)
        gain_24 = round(weight_kg - log[-1][1], 1) if log else 0
        if gain_24 >= wr["gain_24h_kg"]:
            fire("urgent", "HF-W1", f"Weight up {gain_24} kg since yesterday (threshold {wr['gain_24h_kg']} kg/24h)")
        if gain_d >= wr["gain_vs_discharge_kg"]:
            fire("urgent", "HF-W2", f"Weight up {gain_d} kg since discharge ({p['discharge_weight_kg']} kg; "
                 f"threshold {wr['gain_vs_discharge_kg']} kg)")
    if spo2_pct:
        rules = p.get("spo2_rules", {"emergency_below": 88, "urgent_below": 92})
        if spo2_pct < rules["emergency_below"]:
            fire("emergency", "VIT-SPO2", f"SpO2 {spo2_pct}% (< {rules['emergency_below']}%)")
        elif spo2_pct < rules["urgent_below"]:
            fire("urgent", "VIT-SPO2", f"SpO2 {spo2_pct}% (< {rules['urgent_below']}%)")
    if systolic_bp:
        if systolic_bp < 90:
            fire("emergency", "VIT-BP", f"Systolic BP {systolic_bp} mmHg (< 90)")
        elif systolic_bp >= 180:
            fire("urgent", "VIT-BP", f"Systolic BP {systolic_bp} mmHg (>= 180)")
    if heart_rate:
        if heart_rate > 130 or heart_rate < 40:
            fire("emergency", "VIT-HR", f"Heart rate {heart_rate}/min")
        elif heart_rate > 110:
            fire("urgent", "VIT-HR", f"Heart rate {heart_rate}/min (> 110)")
    if temperature_c >= 39.5:
        fire("urgent", "VIT-TEMP", f"Temperature {temperature_c} °C (>= 39.5)")
    elif temperature_c >= 38.3:
        fire("urgent" if p["condition_program"] == "post_op_hip" else "same_day", "VIT-TEMP",
             f"Temperature {temperature_c} °C (>= 38.3)")
    if glucose_mg_dl:
        gr = p.get("glucose_rules", {"emergency_below": 54, "urgent_below": 70, "urgent_above": 300})
        if glucose_mg_dl < gr["emergency_below"]:
            fire("emergency" if "confus" in text else "urgent", "VIT-GLU",
                 f"Glucose {glucose_mg_dl} mg/dL (< {gr['emergency_below']}): treat now with 15 g fast sugar, recheck in 15 min")
        elif glucose_mg_dl < gr["urgent_below"]:
            fire("urgent", "VIT-GLU", f"Glucose {glucose_mg_dl} mg/dL (< {gr['urgent_below']})")
        elif glucose_mg_dl > gr["urgent_above"]:
            fire("urgent", "VIT-GLU", f"Glucose {glucose_mg_dl} mg/dL (> {gr['urgent_above']})")
    if p["condition_program"] == "diabetes":
        lows = [r for r in p["home_readings"].get("glucose_mg_dl", []) if r[1] < 70]
        if len(lows) >= 2:
            fire("urgent", "DM-PATTERN", f"{len(lows)} home glucose readings < 70 mg/dL since discharge "
                 f"({', '.join(f'{r[1]} at {r[0]}' for r in lows)}) — insulin dose review needed")
    if pain_score >= 7:
        fire("same_day", "PAIN", f"Pain {pain_score}/10")
    disp = max((f["disposition"] for f in fired), key=_RANK.get, default="routine")
    actions = {
        "emergency": ["Advise the patient to call emergency services now (do not drive themselves)",
                      "Notify the on-call physician immediately (hlt_create_care_task escalate_on_call)"],
        "urgent": ["Transitional-care nurse calls back within 1 hour", "Consider same-day clinic slot",
                   "Notify the responsible clinician"],
        "same_day": ["Nurse or clinic follow-up today (within 8 hours)"],
        "routine": ["Reinforce the care plan and the next appointment", "Routine check-in in 48-72 hours"]}[disp]
    return ok(patient_id=patient_id.upper(), disposition=disp,
              response_target={"emergency": "immediate", "urgent": "<= 1 hour", "same_day": "<= 8 hours",
                               "routine": "next scheduled contact"}[disp],
              fired_rules=sorted(fired, key=lambda f: -_RANK[f["disposition"]]), ignored_negated=ignored,
              recommended_actions=actions,
              safety_net="If you get chest pain, severe breathlessness, fainting, confusion or heavy bleeding, call "
                         "emergency services immediately.",
              protocol="Corvina Transitional Care Protocol TCP-04 (synthetic)", disclaimer=_HLT_DISCLAIMER)


@hive_tool("enterprise")
def hlt_medication_adherence(patient_id: str) -> dict:
    """Assess post-discharge medication adherence from refill data and pill-box / app dose logs (synthetic).

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-A123'.

    Returns:
        Per medication: days supplied vs days since discharge (proportion of days covered), doses taken/missed in the
        last 5 days, critical-medication flags, the patient-reported barrier and a suggested intervention.
    """
    p = _ac(patient_id)
    if not p:
        return err(f"unknown patient {patient_id!r}", patients=sorted(fixture("hlt_aftercare")["patients"]))
    adh = p["adherence"]
    days = max(1, (AS_OF - _d(p["admission"]["discharged"])).days)
    rows, flags = [], []
    for med in p["medications"]:
        supplied = adh["refills"].get(med["name"], 0)
        pdc = round(min(1.0, supplied / days), 2)
        log = adh["dose_log_last_5_days"].get(med["name"])
        taken_pct = round(log["taken"] / log["scheduled"] * 100) if log and log["scheduled"] else None
        issue = None
        if supplied == 0:
            issue = "never filled"
        elif taken_pct is not None and taken_pct < 80:
            issue = f"{log['scheduled'] - log['taken']} missed doses in 5 days"
        elif pdc < 0.8:
            issue = "supply gap"
        row = {"medication": med["name"], "class": med["class"], "schedule": med["schedule"],
               "critical": med["critical"], "days_supplied": supplied, "pdc": pdc,
               "doses_taken_pct_5d": taken_pct, "missed": log["missed"] if log else [], "issue": issue}
        rows.append(row)
        if issue and (med["critical"] or issue == "never filled"):
            flags.append(f"{med['name']}: {issue}" + (" (critical medication)" if med["critical"] else ""))
    text = adh["patient_reported"].lower()
    suggestion = ("Pharmacist outreach for copay assistance or a formulary alternative; confirm pick-up today"
                  if "copay" in text or "cost" in text else
                  "Discuss timing (e.g. move the afternoon diuretic earlier) and teach-back on why it matters"
                  if "bathroom" in text else
                  "Clinician review of dosing (possible over-treatment)" if "shaky" in text else
                  "Reinforce schedule; no barrier reported")
    return ok(patient_id=patient_id.upper(), days_since_discharge=days, source=adh["source"], medications=rows,
              critical_flags=flags, patient_reported_barrier=adh["patient_reported"], suggested_intervention=suggestion,
              threshold="PDC < 0.80 or < 80% of scheduled doses = non-adherent (TCP-04 §5)",
              disclaimer=_HLT_DISCLAIMER)


@hive_tool("enterprise", kind="action")
def hlt_create_care_task(patient_id: str, task_type: str, urgency: str, summary: str,
                         message_to_patient: str = "") -> dict:
    """Create a care-team task or patient message: nurse callback, clinic visit, pharmacist review, escalation (simulated).

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-A101'.
        task_type: 'nurse_callback', 'clinic_visit', 'pharmacist_review', 'escalate_on_call' or 'patient_message'.
        urgency: 'emergency', 'urgent', 'same_day' or 'routine'.
        summary: Clinical summary for the receiving team (SBAR style preferred).
        message_to_patient: Text to send to the patient (required for 'patient_message'; plain language, <= 480 chars).

    Returns:
        Task id, owning team, due time or booked slot and the channel used (simulated — nothing is sent).
    """
    data = fixture("hlt_aftercare")
    p = _ac(patient_id)
    if not p:
        return err(f"unknown patient {patient_id!r}")
    types = ("nurse_callback", "clinic_visit", "pharmacist_review", "escalate_on_call", "patient_message")
    if task_type not in types or urgency not in _RANK:
        return err("invalid task_type or urgency", task_types=list(types), urgencies=list(_RANK))
    if task_type == "patient_message" and not message_to_patient.strip():
        return err("message_to_patient is required for patient_message")
    if len(message_to_patient) > 480:
        return err("message_to_patient must be <= 480 characters")
    now = dt.datetime.fromisoformat(data["as_of"])
    due = now + {"emergency": dt.timedelta(minutes=5), "urgent": dt.timedelta(hours=1),
                 "same_day": dt.timedelta(hours=8), "routine": dt.timedelta(hours=72)}[urgency]
    slot = None
    if task_type in data["slots"]:
        slot = next((s for s in data["slots"][task_type] if dt.datetime.fromisoformat(s) >= now and
                     (urgency in ("same_day", "routine") or dt.datetime.fromisoformat(s) <= due)
                     ), data["slots"][task_type][0])
    team = {"nurse_callback": data["care_team"]["nurse_line"], "clinic_visit": "Clinic scheduling",
            "pharmacist_review": data["care_team"]["pharmacist"], "escalate_on_call": data["care_team"]["on_call"],
            "patient_message": f"Patient outreach via {p['channel']}"}[task_type]
    return ok(task_id=_ref("CT-", patient_id, task_type, summary[:60]), patient_id=patient_id.upper(),
              task_type=task_type, urgency=urgency, owner=team, due_by=due.isoformat(timespec="minutes"),
              booked_slot=slot, channel=p["channel"] if task_type == "patient_message" else "care-team worklist",
              message_preview=message_to_patient[:160] or None, language=p["language"], simulated=True)


# =================================================================================================================
# Trial Screener — Corvina Clinical Research Office (synthetic patients, fictional trials)
# =================================================================================================================


def _trial(trial_id: str) -> dict | None:
    return next((t for t in fixture("hlt_trials")["trials"] if t["trial_id"].lower() == trial_id.strip().lower()
                 or t["short_name"].lower() == trial_id.strip().lower()), None)


def _patient(patient_id: str) -> dict | None:
    return fixture("hlt_patients")["patients"].get(patient_id.strip().upper())


def _has_term(p: dict, term: str, within_days: int = 0, ref: dt.date = AS_OF) -> str | None:
    term = term.lower()
    for dx in p["diagnoses"]:
        if term in dx["term"].lower() and (not within_days or (ref - _d(dx["date"])).days <= within_days):
            return f"{dx['term']} ({dx['date']})"
    if not within_days:
        for h in p.get("history", []):
            if term in h.lower():
                return h
    return None


def _latest(p: dict, test: str) -> dict | None:
    rows = [m for m in p["measurements"] if m["test"].lower() == test.lower()]
    return max(rows, key=lambda m: m["date"]) if rows else None


def _cmp(v: float, op: str, a: float, b: float | None = None) -> bool:
    return v >= a if op == ">=" else v <= a if op == "<=" else a <= v <= (b if b is not None else a)


def _eval(p: dict, c: dict, ref: dt.date) -> dict:
    r, kind = c["rule"], c["rule"]["kind"]
    res = {"id": c["id"], "type": c["type"], "criterion": c["text"]}

    def done(status, evidence, explain, **kw):
        return {**res, "status": status, "evidence": evidence, "explanation": explain, **kw}

    facts = p.get("facts", {})
    if kind == "age":
        ok_ = p["age"] >= r.get("min", 0) and p["age"] <= r.get("max", 200)
        return done("pass" if ok_ else "fail", f"age {p['age']}", "Age within range." if ok_ else "Age out of range.")
    if kind == "diagnosis":
        dx = next((d for d in p["diagnoses"] if any(t in d["term"].lower() for t in r["any_of"])), None)
        if not dx:
            return done("fail", "no matching diagnosis", "Required diagnosis not found in the record.")
        if r.get("stages") and dx.get("stage") not in r["stages"]:
            if not dx.get("stage"):
                return done("missing_data", dx["term"], "Stage not documented.", data_needed="Documented stage")
            return done("fail", f"{dx['term']}, stage {dx['stage']}", f"Stage {dx['stage']} not in {r['stages']}.")
        return done("pass", f"{dx['term']}" + (f", stage {dx['stage']}" if dx.get("stage") else "") + f" ({dx['date']})",
                    "Diagnosis matches.")
    if kind == "biomarker":
        bm = next((b for b in p.get("biomarkers", []) if b["gene"].upper() == r["gene"]), None)
        if not bm:
            return done("missing_data", "no result", f"No {r['gene']} result on file.",
                        data_needed=f"{r['gene']} mutation test report")
        good = bm["variant"].upper() == r["variant"].upper()
        return done("pass" if good else "fail", f"{bm['gene']} {bm['variant']} ({bm['method']}, {bm['date']})",
                    f"{r['gene']} {r['variant']} {'confirmed' if good else 'not present (different variant)'}.")
    if kind in ("fact_min", "fact_max", "fact_in", "fact_true", "fact_false"):
        f = r["field"]
        if f not in facts:
            return done("missing_data", "not documented", f"'{f}' not documented.", data_needed=f)
        v = facts[f]
        good = {"fact_min": lambda: v >= r["value"], "fact_max": lambda: v <= r["value"],
                "fact_in": lambda: v in r["values"], "fact_true": lambda: v is True,
                "fact_false": lambda: v is False}[kind]()
        dated = f" ({facts[f + '_date']})" if f + "_date" in facts else ""
        return done("pass" if good else "fail", f"{f} = {v}{dated}", "Meets requirement." if good else
                    "Does not meet requirement.")
    if kind == "measurement":
        tests = r["test"] if isinstance(r["test"], list) else [r["test"]]
        alt = r.get("alt_if")
        use_alt = bool(alt and _has_term(p, alt["condition"]))
        ev, statuses, needed = [], [], []
        for test in tests:
            m = _latest(p, test)
            if not m:
                statuses.append("missing_data")
                needed.append(f"{test} (within {r['window_days']} days)")
                ev.append(f"{test}: none")
                continue
            age = (ref - _d(m["date"])).days
            if age > r["window_days"]:
                statuses.append("missing_data")
                needed.append(f"repeat {test} (last {m['date']}, {age} days old; window {r['window_days']} days)")
                ev.append(f"{test} {m['value']} {m['unit']} ({m['date']}, outside window)")
                continue
            if "x_uln" in r:
                mult = alt["x_uln"] if use_alt and "x_uln" in alt else r["x_uln"]
                lim = mult * m["uln"]
                good = _cmp(m["value"], r["op"], lim)
                ev.append(f"{test} {m['value']} {m['unit']} (ULN {m['uln']}, limit {lim:g}; {m['date']})")
            else:
                lim = alt["value"] if use_alt and "value" in alt else r["value"]
                good = _cmp(m["value"], r["op"], lim, r.get("value_hi"))
                rng = f"{lim}-{r['value_hi']}" if r["op"] == "between" else f"{r['op']} {lim}"
                ev.append(f"{test} {m['value']} {m['unit']} (needs {rng}; {m['date']})")
            statuses.append("pass" if good else "fail")
        status = "fail" if "fail" in statuses else "missing_data" if "missing_data" in statuses else "pass"
        note = f" Alternate threshold applied ({alt['condition']})." if use_alt else ""
        return done(status, "; ".join(ev), {"pass": "Within limits.", "fail": "Outside protocol limits.",
                                            "missing_data": "Result missing or outside the protocol window."}[status]
                    + note, **({"data_needed": "; ".join(needed)} if needed else {}))
    if kind == "imaging":
        im = sorted([i for i in p.get("imaging", []) if i.get("largest_lesion_mm")], key=lambda i: i["date"])
        if not im:
            return done("missing_data", "no measurable imaging", "No imaging with lesion measurements.",
                        data_needed=f"CT/MRI within {r['window_days']} days")
        recent = [i for i in im if (ref - _d(i["date"])).days <= r["window_days"]]
        last = max(recent, key=lambda i: i["largest_lesion_mm"]) if recent else im[-1]
        age = (ref - _d(last["date"])).days
        if age > r["window_days"]:
            return done("missing_data", f"{last['modality']} {last['date']} ({age} days old)",
                        "Imaging outside the window.", data_needed=f"Repeat imaging within {r['window_days']} days")
        good = last["largest_lesion_mm"] >= r["min_lesion_mm"]
        return done("pass" if good else "fail", f"{last['modality']} {last['date']}: {last['finding']}",
                    "Measurable disease present." if good else "No lesion >= 10 mm.",
                    window_expires=(_d(last["date"]) + dt.timedelta(days=r["window_days"])).isoformat())
    if kind == "absent_history":
        hits = [h for t in r["any_of"] if (h := _has_term(p, t, r.get("within_days", 0), ref))]
        if hits:
            return done("fail", "; ".join(hits), "Exclusion applies.")
        if not p.get("history_reviewed", True):
            return done("missing_data", "history not reviewed", "Medical history not reviewed.")
        return done("pass", "not found in diagnoses/history", "Exclusion not present.")
    if kind == "no_prior_drug_class":
        hits = [t for t in p.get("therapies", []) if t["drug_class"] in r["classes"]]
        return done("fail" if hits else "pass", "; ".join(f"{t['name']} ({t['start']} to {t['last_dose']})"
                                                          for t in hits) or "no prior exposure",
                    "Prior exposure — excluded." if hits else "No prior exposure.")
    if kind == "washout":
        recent = []
        for t in p.get("therapies", []):
            if t["category"] in r["categories"]:
                gap = (ref - _d(t["last_dose"])).days
                if gap < r["days"]:
                    recent.append((t, gap))
        if recent:
            t, gap = max(recent, key=lambda x: _d(x[0]["last_dose"]))
            earliest = (_d(t["last_dose"]) + dt.timedelta(days=r["days"])).isoformat()
            return done("fail", f"{t['name']} last dose {t['last_dose']} ({gap} days ago)",
                        f"Washout of {r['days']} days not complete.", earliest_eligible_date=earliest,
                        time_limited=True)
        last = [t for t in p.get("therapies", []) if t["category"] in r["categories"]]
        ev = "; ".join(f"{t['name']} last {t['last_dose']}" for t in last) or "none"
        return done("pass", ev, f"Washout of {r['days']} days satisfied.")
    if kind == "brain_mets":
        bm = facts.get("brain_mets")
        if not bm:
            return done("missing_data", "not documented", "Brain metastasis status not documented.",
                        data_needed="Brain MRI or documented status")
        if bm["status"] == "none":
            return done("pass", bm.get("note", "none"), "No brain metastases.")
        if bm["status"] == "treated_stable":
            wk = (ref - _d(bm["treated"])).days // 7
            good = wk >= r["stable_weeks"]
            return done("pass" if good else "fail", bm.get("note", ""), f"Treated {wk} weeks ago and stable — "
                        f"{'allowed' if good else 'not yet allowed'} (>= {r['stable_weeks']} weeks).")
        return done("fail", bm.get("note", bm["status"]), "Active/untreated brain metastases.")
    if kind == "serology":
        sero = p.get("serology", {})
        missing = [t for t in r["tests"] if t not in sero]
        pos = [f"{t}: {sero[t]}" for t in r["tests"] if t in sero and "positive" in sero[t].lower()
               and "controlled" not in sero[t].lower()]
        if pos:
            return done("fail", "; ".join(pos), "Active infection — excluded.")
        if missing:
            return done("missing_data", "; ".join(f"{t}: {sero[t]}" for t in sero) or "none on file",
                        f"No result for {', '.join(missing)}.", data_needed=" + ".join(f"{t} serology" for t in missing))
        return done("pass", "; ".join(f"{t}: {sero[t]}" for t in r["tests"]), "No active infection.")
    if kind == "pregnancy":
        if p["sex"] != "F" or not facts.get("childbearing_potential"):
            return done("pass", "not of childbearing potential" if p["sex"] == "F" else "male", "Not applicable.")
        m = _latest(p, "Pregnancy test")
        if not m or (ref - _d(m["date"])).days > r["window_days"]:
            return done("missing_data", "no recent pregnancy test", "Negative pregnancy test needed within "
                        f"{r['window_days']} days of first dose.", data_needed="Serum pregnancy test")
        good = str(m["value"]).lower().startswith("neg")
        return done("pass" if good else "fail", f"pregnancy test {m['value']} ({m['date']})", "Checked.")
    if kind == "med_class_absent":
        hits = [m for m in p.get("medications", []) if m["drug_class"] in r["classes"]]
        return done("fail" if hits else "pass", "; ".join(m["name"] for m in hits) or "none on medication list",
                    "Prohibited medication." if hits else "No prohibited medication on the list.")
    if kind == "stable_med_class":
        meds = [m for m in p.get("medications", []) if m["status"] == "active"]
        main = [m for m in meds if m["drug_class"] in r["classes"]
                and (ref - _d(m["start"])).days >= r["min_weeks"] * 7]
        also_ok = all(any(m["drug_class"] == a and (ref - _d(m["start"])).days >= r["min_weeks"] * 7 for m in meds)
                      for a in r.get("also", []))
        good = bool(main) and also_ok
        return done("pass" if good else "fail", "; ".join(f"{m['name']} since {m['start']}" for m in meds
                                                          if m["drug_class"] in r["classes"] + r.get("also", []))
                    or "none", "Stable background therapy." if good else "Required stable therapy not documented.")
    return done("needs_review", "", f"Rule kind {kind!r} needs manual review.")


_DATA_NEEDED = {"age": "age at consent", "diagnosis": "pathology/diagnosis with stage",
                "biomarker": "molecular test report", "fact_min": "documented clinical fact",
                "fact_max": "documented clinical fact", "fact_in": "documented clinical fact",
                "fact_true": "documented capacity/consent status", "fact_false": "documented status",
                "measurement": "dated lab/vital/test result within the window",
                "imaging": "CT/MRI with lesion measurements within the window", "absent_history": "medical history",
                "no_prior_drug_class": "prior therapy history", "washout": "last-dose dates of prior therapy",
                "brain_mets": "brain imaging / metastasis status", "serology": "hepatitis B/C and HIV serology",
                "pregnancy": "pregnancy test (if of childbearing potential)",
                "med_class_absent": "current medication list", "stable_med_class": "medication start dates"}


def _outcome(results: list[dict]) -> tuple[str, str | None]:
    fails = [r for r in results if r["status"] == "fail"]
    earliest = max((r["earliest_eligible_date"] for r in fails if r.get("time_limited")), default=None)
    if fails and all(r.get("time_limited") for r in fails):
        return "not_yet_eligible", earliest
    if fails:
        return "likely_ineligible", None
    if any(r["status"] == "missing_data" for r in results):
        return "pending_data", None
    if any(r["status"] == "needs_review" for r in results):
        return "needs_review", None
    return "likely_eligible", None


@hive_tool("enterprise")
def hlt_get_patient_record(patient_id: str) -> dict:
    """Get a synthetic patient's research-relevant record: diagnoses, biomarkers, labs, imaging, therapies, history.

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-P014'.

    Returns:
        The de-identified synthetic record (age, sex, diagnoses with stage, biomarkers, dated measurements, imaging,
        prior therapies with last-dose dates, medications, history, serology, performance status, notes).
    """
    p = _patient(patient_id)
    if not p:
        return err(f"unknown patient {patient_id!r}", patients=sorted(fixture("hlt_patients")["patients"]))
    return ok(patient_id=patient_id.upper(), **p, disclaimer=_HLT_DISCLAIMER)


@hive_tool("enterprise")
def hlt_get_trial_criteria(trial_id: str = "") -> dict:
    """List recruiting trials, or get one trial's inclusion/exclusion criteria with the data each criterion needs.

    Args:
        trial_id: Trial id (e.g. 'CVH-ONC-2026-014') or short name (e.g. 'HERON-2'). Empty lists open trials.

    Returns:
        Trial summaries (phase, condition, site, PI, coordinator, slots) or the full criteria list for one trial.
    """
    data = fixture("hlt_trials")
    if not trial_id.strip():
        return ok(trials=[{k: t[k] for k in ("trial_id", "short_name", "title", "phase", "sponsor", "condition",
                                             "site", "pi", "coordinator", "slots_remaining", "status")}
                          for t in data["trials"]])
    t = _trial(trial_id)
    if not t:
        return err(f"unknown trial {trial_id!r}", trials=[x["trial_id"] for x in data["trials"]])
    crit = [{"id": c["id"], "type": c["type"], "text": c["text"],
             "data_needed": _DATA_NEEDED.get(c["rule"]["kind"], c["rule"]["kind"])} for c in t["criteria"]]
    info = {k: v for k, v in t.items() if k not in ("criteria", "status")}
    return ok(**info, recruitment_status=t["status"], criteria=crit)


@hive_tool("enterprise")
def hlt_screen_patient(patient_id: str, trial_id: str = "", screening_date: str = "2026-11-06") -> dict:
    """Evaluate a synthetic patient against every criterion of a trial (or rank all recruiting trials) — pre-screen only.

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-P014'.
        trial_id: Trial id or short name. Leave empty to screen against all recruiting trials and rank them.
        screening_date: Planned screening date YYYY-MM-DD; lab/imaging windows and washouts count back from it.

    Returns:
        Per criterion: status (pass / fail / missing_data / needs_review), evidence with dates and explanation;
        overall outcome (likely_eligible / pending_data / not_yet_eligible / likely_ineligible / needs_review),
        missing-data actions and the earliest eligible date when only a washout blocks. For all trials: a ranking.
    """
    p = _patient(patient_id)
    if not p:
        return err(f"unknown patient {patient_id!r}", patients=sorted(fixture("hlt_patients")["patients"]))
    try:
        ref = _d(screening_date)
    except ValueError:
        return err("screening_date must be YYYY-MM-DD")
    trials = fixture("hlt_trials")["trials"]
    if not trial_id.strip():
        order = {"likely_eligible": 0, "needs_review": 1, "pending_data": 2, "not_yet_eligible": 3,
                 "likely_ineligible": 4}
        ranking = []
        for t in trials:
            res = [_eval(p, c, ref) for c in t["criteria"]]
            out, earliest = _outcome(res)
            ranking.append({"trial_id": t["trial_id"], "short_name": t["short_name"], "condition": t["condition"],
                            "outcome": out, "earliest_eligible_date": earliest,
                            "passed": sum(r["status"] == "pass" for r in res), "criteria": len(res),
                            "blocking": [f"{r['id']}: {r['criterion']}" for r in res if r["status"] == "fail"][:4],
                            "missing": [r["id"] for r in res if r["status"] == "missing_data"]})
        ranking.sort(key=lambda x: (order[x["outcome"]], -x["passed"] / x["criteria"]))
        return ok(patient_id=patient_id.upper(), screening_date=ref.isoformat(), ranking=ranking,
                  next_step="Screen the best-ranked trial in detail (call again with its trial_id).",
                  disclaimer=_HLT_DISCLAIMER)
    t = _trial(trial_id)
    if not t:
        return err(f"unknown trial {trial_id!r}", trials=[x["trial_id"] for x in trials])
    res = [_eval(p, c, ref) for c in t["criteria"]]
    out, earliest = _outcome(res)
    actions = [f"{r['id']}: {r['data_needed']}" for r in res if r["status"] == "missing_data" and r.get("data_needed")]
    expiring = [f"{r['id']}: imaging window ends {r['window_expires']}" for r in res if r.get("window_expires")]
    return ok(patient_id=patient_id.upper(), trial_id=t["trial_id"], short_name=t["short_name"],
              screening_date=ref.isoformat(), outcome=out, earliest_eligible_date=earliest, criteria=res,
              counts={s: sum(r["status"] == s for r in res) for s in ("pass", "fail", "missing_data", "needs_review")},
              missing_data_actions=actions, window_notes=expiring, pi=t["pi"], coordinator=t["coordinator"],
              slots_remaining=t["slots_remaining"],
              note="Pre-screening on synthetic data. Eligibility is confirmed only by the investigator after "
                   "informed consent and protocol screening procedures.", disclaimer=_HLT_DISCLAIMER)


@hive_tool("enterprise", kind="action")
def hlt_log_prescreen(patient_id: str, trial_id: str, outcome: str, coordinator_note: str) -> dict:
    """Record a pre-screening result in the research pre-screening log for PI review (simulated).

    Args:
        patient_id: Synthetic patient id, e.g. 'SYN-P014'.
        trial_id: Trial id, e.g. 'CVH-ONC-2026-014'.
        outcome: likely_eligible, pending_data, not_yet_eligible, likely_ineligible or needs_review.
        coordinator_note: The note for the study coordinator and PI.

    Returns:
        Log entry id, routing (coordinator + PI) and the rule that the patient is not contacted before PI review.
    """
    t = _trial(trial_id)
    if not _patient(patient_id) or not t:
        return err("unknown patient or trial")
    if outcome not in ("likely_eligible", "pending_data", "not_yet_eligible", "likely_ineligible", "needs_review"):
        return err("invalid outcome")
    if len(coordinator_note.strip()) < 40:
        return err("coordinator_note is too short")
    return ok(log_id=_ref("PSL-", patient_id, t["trial_id"], outcome), patient_id=patient_id.upper(),
              trial_id=t["trial_id"], outcome=outcome, routed_to=[t["coordinator"], t["pi"]],
              log_status="awaiting PI review", contact_rule="No patient contact about the trial until the PI approves "
              "and the treating physician agrees (Pre-screening SOP CRO-SOP-09).", simulated=True)


# =================================================================================================================
# Claim Denial — Corvina Patient Financial Services
# =================================================================================================================


def _den() -> dict:
    return fixture("hlt_denials")


def _assess(cl: dict) -> dict:
    d = _den()
    code = d["codes"][cl["denial_code"]]
    cat = code["category"]
    payer = d["payers"][cl["payer"]]
    base = d["category_base_rates"][cat]
    p = 0.5 * base + 0.5 * payer["overturn_rates"].get(cat, base)
    drivers = [f"base rate {cat} {base:.0%}", f"{cl['payer']} overturn rate {payer['overturn_rates'].get(cat, base):.0%}"]
    ev = cl.get("evidence", {})
    if ev.get("auth_on_file"):
        p += 0.35
        drivers.append("authorization was on file (+35pp)")
    if ev.get("emergency") and any("emergency" in n.lower() and "exempt" in n.lower() for n in payer["policy_notes"]):
        p += 0.30
        drivers.append("emergency services exempt from prior auth per payer policy (+30pp)")
    if ev.get("proof_of_timely_filing"):
        p += 0.45
        drivers.append("proof of timely original submission (+45pp)")
    adj = {"strong": 0.10, "moderate": 0.0, "weak": -0.15}[ev.get("evidence_strength", "moderate")]
    if adj:
        p += adj
        drivers.append(f"documentation {ev.get('evidence_strength')} ({adj * 100:+.0f}pp)")
    deadline = _d(cl["denial_date"]) + dt.timedelta(days=payer["appeal_window_days"])
    days_left = (deadline - AS_OF).days
    if days_left < 0:
        p, drivers = 0.0, drivers + ["appeal window closed"]
    p = round(min(0.95, max(0.02 if days_left >= 0 else 0.0, p)), 2)
    if cat == "duplicate":
        action = "no appeal — verify the original claim was paid and close"
    elif cat in ("missing_information", "coding", "bundling"):
        action = "submit a corrected claim (not an appeal)"
    elif days_left < 0:
        action = "write-off review — appeal window closed"
    elif p >= 0.40:
        action = "appeal (Level 1)"
    elif p >= 0.25:
        action = "appeal only after peer-to-peer review / added documentation"
    else:
        action = "write-off review unless new documentation is found"
    return {"category": cat, "meaning": code["meaning"], "likelihood": p, "drivers": drivers,
            "expected_recovery_usd": round(p * cl["denied_usd"], 2), "deadline": deadline.isoformat(),
            "days_to_deadline": days_left, "recommended_action": action}


@hive_tool("enterprise")
def hlt_denial_worklist(payer: str = "", min_denied_usd: float = 0.0) -> dict:
    """Rank open denied claims by expected recovery and deadline so the team works the right claims first.

    Args:
        payer: Optional payer name filter (e.g. 'Silverline').
        min_denied_usd: Only include denials at or above this amount.

    Returns:
        Open denials with denial code and meaning, category, denied amount, appeal likelihood, expected recovery,
        days to the appeal deadline, recommended action (appeal / corrected claim / write-off review) and totals.
    """
    rows = []
    for cl in _den()["claims"]:
        if payer and payer.lower() not in cl["payer"].lower():
            continue
        if cl["denied_usd"] < min_denied_usd:
            continue
        a = _assess(cl)
        urgency = 1.5 if 0 <= a["days_to_deadline"] <= 30 else 1.0
        rows.append({"claim_id": cl["claim_id"], "payer": cl["payer"], "service": cl["service"],
                     "denial_code": cl["denial_code"], "meaning": a["meaning"], "category": a["category"],
                     "denied_usd": cl["denied_usd"], "likelihood": a["likelihood"],
                     "expected_recovery_usd": a["expected_recovery_usd"], "days_to_deadline": a["days_to_deadline"],
                     "recommended_action": a["recommended_action"],
                     "priority_score": round(a["expected_recovery_usd"] * urgency)})
    rows.sort(key=lambda r: -r["priority_score"])
    return ok(as_of=_den()["as_of"], claims=rows, total_denied_usd=round(sum(r["denied_usd"] for r in rows), 2),
              total_expected_recovery_usd=round(sum(r["expected_recovery_usd"] for r in rows), 2),
              model="Illustrative likelihood model: category base rate blended with payer overturn history, "
                    "adjusted for evidence (Denial Management Playbook §4).")


@hive_tool("enterprise")
def hlt_get_denied_claim(claim_id: str) -> dict:
    """Get one denied claim with the denial reason, payer rules, appeal likelihood drivers and required enclosures.

    Args:
        claim_id: Claim id, e.g. 'CLM-26-004211'.

    Returns:
        Claim facts (service, codes, amounts, dates), denial code meaning and category, payer appeal window and
        levels, policy notes, likelihood with drivers, expected recovery, recommended action and documents on hand.
    """
    cl = next((c for c in _den()["claims"] if c["claim_id"].lower() == claim_id.strip().lower()), None)
    if not cl:
        return err(f"unknown claim {claim_id!r}", claims=[c["claim_id"] for c in _den()["claims"]])
    payer = _den()["payers"][cl["payer"]]
    return ok(**cl, assessment=_assess(cl), payer_rules={k: payer[k] for k in
                                                          ("appeal_window_days", "corrected_claim_window_days",
                                                           "levels", "submission", "policy_notes")},
              note="Patient references are synthetic; codes are illustrative.")


@hive_tool("enterprise")
def hlt_draft_appeal_letter(claim_id: str, arguments: list[str], requested_action: str = "reprocess and pay") -> dict:
    """Draft a payer appeal letter from the claim facts and the agent's appeal arguments (draft only — never sent).

    Args:
        claim_id: Claim id, e.g. 'CLM-26-004211'.
        arguments: 2-5 factual appeal arguments, each one sentence, citing documents or payer policy.
        requested_action: What the payer should do (default 'reprocess and pay').

    Returns:
        Letter text, enclosure list, submission channel and deadline, plus warnings (e.g. a corrected claim is the
        right route, or the deadline has passed). Requires human review and signature.
    """
    got = hlt_get_denied_claim(claim_id)
    if got["status"] != "ok":
        return got
    if not 1 <= len(arguments) <= 6:
        return err("provide 1-6 arguments")
    a, pr = got["assessment"], got["payer_rules"]
    warnings = []
    if "corrected claim" in a["recommended_action"]:
        warnings.append("This denial is usually resolved with a corrected claim, not an appeal.")
    if a["days_to_deadline"] < 0:
        warnings.append("The appeal window has closed — the payer will likely reject this letter.")
    elif a["days_to_deadline"] <= 30:
        warnings.append(f"Deadline in {a['days_to_deadline']} days ({a['deadline']}).")
    args = "\n".join(f"{i}. {s.strip()}" for i, s in enumerate(arguments, 1))
    encl = "\n".join(f"- {d}" for d in got["documents"]) or "- (none on file — attach supporting records)"
    letter = (
        f"Corvina Health Network — Patient Financial Services (fictional)\n"
        f"Date: {AS_OF.isoformat()}\n\n"
        f"To: {got['payer']} — Provider Appeals ({pr['levels'][0]})\n"
        f"Re: Appeal of denied claim {got['claim_id']} | Member ref {got['patient_ref']} | Date of service "
        f"{got['service_date']} | Denial {got['denial_code']} ({a['meaning']}) | Amount in dispute "
        f"USD {got['denied_usd']:,.2f}\n\n"
        f"Dear Appeals Reviewer,\n\n"
        f"Corvina Health Network requests reconsideration of the denial of the claim above for "
        f"{got['service']} (CPT {got['cpt']}; ICD-10 {', '.join(got['icd10'])}) provided at {got['facility']}. "
        f"We ask that you {requested_action}.\n\n"
        f"Grounds for appeal:\n{args}\n\n"
        f"The enclosed records support these points. Please contact our appeals desk with any questions.\n\n"
        f"Enclosures:\n{encl}\n\n"
        f"Sincerely,\n[Name, title — to be completed by the reviewer]\nCorvina Health Network (fictional)")
    return ok(claim_id=got["claim_id"], letter=letter, submission=pr["submission"], deadline=a["deadline"],
              warnings=warnings, letter_status="DRAFT — requires human review and signature; not submitted",
              simulated=True)


# =================================================================================================================
# Clinical Docs — documentation completeness and illustrative coding
# =================================================================================================================

_DOC_ELEMENTS = [   # English patterns first; Spanish alternatives let notes written in Spanish be scored too
    ("subjective_section", 1, True, r"(^|\n)\W*(s:|subjective|subjetivo)"),
    ("objective_section", 1, True, r"(^|\n)\W*(o:|objective|objetivo)"),
    ("assessment_section", 1, True, r"(^|\n)\W*(a:|assessment|evaluaci[oó]n|valoraci[oó]n|an[aá]lisis)"),
    ("plan_section", 1, True, r"(^|\n)\W*(p:|plan)"),
    ("chief_complaint", 1, True, r"chief complaint|\bcc\b|reason for visit|motivo de (la )?consulta"),
    ("history_of_present_illness", 2, True, r"history of present illness|\bhpi\b|enfermedad actual|padecimiento actual"),
    ("review_of_systems", 1, False, r"review of systems|\bros\b|revisi[oó]n (por|de) (sistemas|aparatos)"),
    ("vital_signs", 2, True, r"\b\d{2,3}/\d{2,3}\b|blood pressure|\bbp\b|presi[oó]n arterial|tensi[oó]n arterial"),
    ("physical_exam", 2, True, r"exam(ination)?\b|examen|exploraci[oó]n f[ií]sica"),
    ("medication_reconciliation", 2, True, r"medication reconciliation|med(ication)?s? reconciled|reconcil|conciliaci[oó]n"),
    ("allergies", 1, True, r"allerg|nkda|no known drug allergies|alerg"),
    ("diagnoses_in_assessment", 2, True, r"(\ba:|assessment|evaluaci[oó]n|valoraci[oó]n|an[aá]lisis)[\s\S]{0,400}?\b(failure|"
                                          r"diabetes|copd|hypertension|pharyngitis|fibrillation|disease|pain|infection|"
                                          r"exacerbation|insuficiencia|epoc|hipertensi[oó]n|faringitis|fibrilaci[oó]n|"
                                          r"enfermedad|dolor|infecci[oó]n|exacerbaci[oó]n)\b"),
    ("follow_up_interval", 1, True, r"follow[- ]?up|return (in|if)|\brtc\b|recheck|seguimiento|control en|regresar|"
                                    r"volver (en|si)"),
    ("patient_education", 1, False, r"educat|teach[- ]?back|counsel|educaci[oó]n|educad|orientaci[oó]n"),
    ("mdm_or_time", 1, False, r"medical decision making|\bmdm\b|total time|minutes|toma de decisiones|tiempo total|minutos"),
]
_TELEHEALTH = [("telehealth_consent", 1, True, r"consent"),
               ("telehealth_modality", 1, True, r"\bvideo\b|audio[- ]only|telephone|videollamada|solo audio|tel[eé]fono"),
               ("patient_location", 1, True, r"patient (is )?(located|at home|location)|from (her|his|their) home|"
                                             r"paciente (se encuentra|ubicad|en (su )?casa)|desde (su )?casa|domicilio")]
_NOT_DOC = ("[not documented", "[no documentado")


@hive_tool("enterprise")
def hlt_documentation_completeness(note_text: str, encounter_type: str = "outpatient_follow_up") -> dict:
    """Score a clinical note for documentation completeness against the Corvina documentation standard.

    Args:
        note_text: The full SOAP note text to check.
        encounter_type: 'outpatient_follow_up', 'telehealth' or 'urgent_care'.

    Returns:
        Score 0-100, verdict (complete >= 85 with no critical gaps / needs revision), present and missing elements
        (critical flagged), and placeholders such as '[not documented]' that a clinician must resolve.
    """
    if len(note_text.strip()) < 80:
        return err("note_text is too short to assess")
    if encounter_type not in ("outpatient_follow_up", "telehealth", "urgent_care"):
        return err("encounter_type must be outpatient_follow_up, telehealth or urgent_care")
    text = note_text.lower()
    elements = _DOC_ELEMENTS + (_TELEHEALTH if encounter_type == "telehealth" else [])
    present, missing, total, got = [], [], 0, 0
    for name, weight, critical, pat in elements:
        total += weight
        m = re.search(pat, text)
        clause = re.split(r"\.\s|\n", text[m.start():], maxsplit=1)[0] if m else ""
        if m and not any(x in clause for x in _NOT_DOC):
            present.append(name)
            got += weight
        else:
            missing.append({"element": name, "critical": critical,
                            **({"marked_not_documented": True} if m else {})})
    placeholders = re.findall(r"\[(not documented[^\]]*|no documentado[^\]]*|to be confirmed[^\]]*|"
                              r"clinician to confirm[^\]]*|por confirmar[^\]]*)\]", text)
    score = round(got / total * 100)
    critical_missing = [m["element"] for m in missing if m["critical"] and not m.get("marked_not_documented")]
    marked = [m["element"] for m in missing if m.get("marked_not_documented")]
    verdict = "needs revision" if score < 85 or critical_missing else \
        "complete — clinician to confirm placeholders" if marked else "complete"
    return ok(score=score, verdict=verdict, present=present, missing=missing, critical_missing=critical_missing,
              marked_not_documented=marked, placeholders_to_resolve=len(placeholders),
              standard="Corvina Clinical Documentation Standard CDS-3",
              note="Automated completeness check only; it does not verify clinical accuracy.")


_ALIASES = [(r"\bhfref\b|reduced ejection fraction", "systolic heart failure"), (r"\bchf\b", "heart failure"),
            (r"\bt2dm?\b|type ii diabetes|\bdm2\b|diabetes mellitus type 2", "type 2 diabetes"),
            (r"\bhtn\b", "hypertension"), (r"\bckd\b", "chronic kidney disease"), (r"\ba-?fib\b", "atrial fibrillation"),
            (r"strep throat", "strep pharyngitis"), (r"chronic obstructive pulmonary disease", "copd"), (r"oedema", "edema"), (r"hypoglycaemia", "hypoglycemia"),
            (r"hyperglycaemia", "hyperglycemia"), (r"\b3a\b", "stage 3a"), (r"\b3b\b", "stage 3b"),
            # Spanish problem wording -> the crosswalk's English keywords
            (r"(agudizaci[oó]n|descompensaci[oó]n aguda) de (la |una )?insuficiencia card[ií]aca cr[oó]nica|"
             r"insuficiencia card[ií]aca cr[oó]nica (agudizada|descompensada)", "acute on chronic heart failure"),
            (r"fracci[oó]n de eyecci[oó]n reducida|\bicfer\b", "systolic"),
            (r"insuficiencia card[ií]aca", "heart failure"), (r"sist[oó]lica", "systolic"),
            (r"enfermedad renal cr[oó]nica|\berc\b", "chronic kidney disease"), (r"estadio 3a", "stage 3a"),
            (r"estadio 3b", "stage 3b"), (r"cr[oó]nica|cr[oó]nico", "chronic"),
            (r"hipertensi[oó]n( arterial)?", "hypertension"), (r"diabetes (mellitus )?tipo 2|\bdm ?2\b", "type 2 diabetes"),
            (r"hiperglucemia", "hyperglycemia"), (r"hipoglucemia", "hypoglycemia"), (r"\bepoc\b", "copd"),
            (r"exacerbaci[oó]n|reagudizaci[oó]n", "exacerbation"),
            (r"faringitis estreptoc[oó]cica|faringoamigdalitis estreptoc[oó]cica", "strep pharyngitis"),
            (r"faringitis|faringoamigdalitis", "pharyngitis"), (r"estreptococ", "strep"),
            (r"fibrilaci[oó]n auricular", "atrial fibrillation"), (r"permanente", "permanent"), (r"edema", "edema"),
            (r"exfumador(a)?", "former smoker"), (r"insulina a largo plazo|uso prolongado de insulina", "long-term insulin"),
            (r"dosis omitidas|olvido de dosis", "missed doses")]


@hive_tool("enterprise")
def hlt_suggest_codes(problems: list[str], mdm_level: str = "moderate", visit_type: str = "established_office",
                      days_since_discharge: int = -1) -> dict:
    """Suggest illustrative ICD-10-CM and E/M codes for an encounter's assessed problems (coder review required).

    Args:
        problems: Assessed problems in clinical words (e.g. ['acute on chronic systolic heart failure',
            'type 2 diabetes', 'hypertension']).
        mdm_level: Medical decision-making level: 'straightforward', 'low', 'moderate' or 'high'.
        visit_type: 'established_office', 'new_office' or 'telehealth_established'.
        days_since_discharge: Days since hospital discharge (-1 if not a post-discharge visit), for transitional
            care management.

    Returns:
        Per problem the best-matching code with description and specificity/query notes, combination-coding notes,
        the E/M level, a transitional-care consideration and the mandatory review disclaimer.
    """
    ref = fixture("hlt_coding")
    if mdm_level not in ("straightforward", "low", "moderate", "high"):
        return err("mdm_level must be straightforward, low, moderate or high")
    if not problems:
        return err("problems must not be empty")
    out, codes = [], set()
    for prob in problems:
        t = prob.lower()
        for pat, rep in _ALIASES:
            t = re.sub(pat, rep, t)
        cands = [e for e in ref["icd10"] if all(k in t for k in e["keywords"])]
        best = max(cands, key=lambda e: sum(len(k) for k in e["keywords"]), default=None)
        if best:
            codes.add(best["code"])
            out.append({"problem": prob, "code": best["code"], "description": best["description"],
                        **({"specificity_note": best["specificity_note"]} if best.get("specificity_note") else {})})
        else:
            out.append({"problem": prob, "code": None, "description": "no match in the illustrative crosswalk",
                        "specificity_note": "Refer to the coder."})
    combos = []
    if any(c.startswith("I50") for c in codes) and "I10" in codes:
        combos.append("Hypertension with heart failure: report I11.0 (hypertensive heart disease with heart failure) "
                      "instead of I10, plus the I50.x type code.")
    if any(c.startswith("I50") for c in codes) and "I10" in codes and any(c.startswith("N18") for c in codes):
        combos.append("Hypertension + heart failure + CKD: consider I13.0 with I50.x and N18.x.")
    if any(c.startswith("E11") and c != "E11.22" for c in codes) and any(c.startswith("N18") for c in codes):
        combos.append("Diabetes with CKD: E11.22 plus the N18.x stage is presumed linked unless documented otherwise.")
    vt = "new_office" if visit_type == "new_office" else "established_office"
    em = ref["em"][vt][mdm_level]
    tele = ref["telehealth_note"] if visit_type.startswith("telehealth") else None
    tcm = None
    if 0 <= days_since_discharge <= 14 and mdm_level in ("moderate", "high"):
        opt = ref["tcm"]["high" if mdm_level == "high" and days_since_discharge <= 7 else "moderate"]
        tcm = f"Consider TCM {opt['code']} instead of a standalone E/M if requirements are met. {ref['tcm']['note']}"
    return ok(diagnoses=out, combination_notes=combos, em_code=em, em_basis=f"{mdm_level} MDM, {vt}",
              telehealth_note=tele, transitional_care=tcm, disclaimer=ref["note"])

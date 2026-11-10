"""Cross-realm helper tools: sample documents, dates, ROI and critical-path scheduling."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict, deque

from ._base import doc_paths, doc_text, err, hive_tool, ok


@hive_tool("common")
def get_sample_document(key: str) -> dict:
    """Load a synthetic sample document (transcript, RFP, SOW draft, policy, email thread, code file...).

    Args:
        key: Document key exactly as given in the request or your instructions, e.g. 'transcript_steering_q3'.
            Never guess keys.

    Returns:
        The document text and its length in characters.
    """
    text = doc_text(key)
    if text is None:
        return err(f"no sample document {key!r}",
                   hint="use only a key given in the request or your instructions; otherwise work from the request")
    return ok(key=key, text=text, chars=len(text))


@hive_tool("common")
def list_sample_documents(prefix: str = "") -> dict:
    """List available synthetic sample documents, optionally filtered by key prefix (e.g. 'rfp_', 'sow_').

    Args:
        prefix: Optional key prefix filter.

    Returns:
        Document keys with their first heading line.
    """
    out = []
    for key, p in doc_paths(prefix).items():
        first = next((ln.strip("# ").strip() for ln in p.read_text().splitlines() if ln.strip()), "")
        out.append({"key": key, "title": first})
    return ok(documents=out)


@hive_tool("common")
def current_date() -> dict:
    """Return today's date (UTC) and ISO week, for scheduling and due-date math."""
    today = dt.datetime.now(dt.timezone.utc).date()
    return ok(date=today.isoformat(), iso_week=today.isocalendar().week, weekday=today.strftime("%A"))


@hive_tool("common")
def compute_roi(investment_usd: float, annual_benefit_usd: float, annual_run_cost_usd: float = 0.0,
                years: int = 3, discount_rate: float = 0.08) -> dict:
    """Compute ROI, NPV, payback period and IRR-style summary for a technology investment.

    Args:
        investment_usd: One-off implementation cost.
        annual_benefit_usd: Recurring yearly benefit (savings + new revenue).
        annual_run_cost_usd: Recurring yearly run cost (licences, cloud, support).
        years: Evaluation horizon in years (1-10).
        discount_rate: Discount rate for NPV (e.g. 0.08).

    Returns:
        ROI %, NPV, payback months and a year-by-year cash-flow table.
    """
    if investment_usd <= 0 or years < 1 or years > 10:
        return err("investment must be > 0 and years between 1 and 10")
    net = annual_benefit_usd - annual_run_cost_usd
    flows, cum, payback = [], -investment_usd, None
    npv = -investment_usd
    for y in range(1, years + 1):
        prev = cum
        cum += net
        npv += net / (1 + discount_rate) ** y
        if payback is None and cum >= 0 and net > 0:
            payback = round(((y - 1) + (-prev / net)) * 12, 1)
        flows.append({"year": y, "net_benefit": round(net, 2), "cumulative": round(cum, 2)})
    roi = (net * years - investment_usd) / investment_usd * 100
    return ok(roi_pct=round(roi, 1), npv_usd=round(npv, 2), payback_months=payback, cash_flows=flows,
              assumptions={"years": years, "discount_rate": discount_rate})


@hive_tool("common")
def critical_path(tasks: list[dict], start_date: str = "") -> dict:
    """Compute the critical path, slack and project duration for a list of tasks (CPM).

    Args:
        tasks: List of {"id": str, "name": str, "duration_days": number, "depends_on": [ids], "owner": str}.
        start_date: Project start as YYYY-MM-DD (default: next Monday). Durations are calendar days.

    Returns:
        Project duration, ordered critical path, per-task early/late start-finish and slack, plus a Mermaid Gantt.
    """
    try:
        if any(not str(t.get("id") or "").strip() for t in tasks):
            return err("every task needs a non-empty 'id' (e.g. 'T1')")
        by_id = {t["id"]: {**t, "depends_on": [d for d in (t.get("depends_on") or []) if str(d).strip()]}
                 for t in tasks}
        for t in by_id.values():
            for d in t["depends_on"]:
                if d not in by_id:
                    return err(f"task {t['id']} depends on unknown task {d}")
        indeg = {k: len(v["depends_on"]) for k, v in by_id.items()}
        succ = defaultdict(list)
        for k, v in by_id.items():
            for d in v["depends_on"]:
                succ[d].append(k)
        q, order = deque(k for k, n in indeg.items() if n == 0), []
        while q:
            k = q.popleft()
            order.append(k)
            for s in succ[k]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        if len(order) != len(by_id):
            return err("dependency cycle detected")
        es, ef = {}, {}
        for k in order:
            es[k] = max((ef[d] for d in by_id[k]["depends_on"]), default=0)
            ef[k] = es[k] + float(by_id[k]["duration_days"])
        duration = max(ef.values(), default=0)
        lf, ls = {}, {}
        for k in reversed(order):
            lf[k] = min((ls[s] for s in succ[k]), default=duration)
            ls[k] = lf[k] - float(by_id[k]["duration_days"])
        rows = [{"id": k, "name": by_id[k].get("name", k), "owner": by_id[k].get("owner", ""),
                 "es": es[k], "ef": ef[k], "ls": ls[k], "lf": lf[k], "slack": round(ls[k] - es[k], 2)}
                for k in order]
        path = [r["id"] for r in rows if abs(r["slack"]) < 1e-9]
        today = dt.date(2026, 11, 6)   # the demo world's fixed "today" (same as the synthetic systems of record)
        start = dt.date.fromisoformat(start_date) if start_date else today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
        gantt = ["gantt", "  title Delivery schedule", "  dateFormat YYYY-MM-DD"]
        for r in rows:
            r["start"] = (start + dt.timedelta(days=r["es"])).isoformat()
            r["finish"] = (start + dt.timedelta(days=r["ef"])).isoformat()
            tag = "crit, " if r["id"] in path else ""
            label = r["name"][:40].replace(":", " ")
            gantt.append(f"  {label} :{tag}{r['id']}, {r['start']}, {max(1, round(r['ef'] - r['es']))}d")
        return ok(duration_days=duration, start=start.isoformat(),
                  finish=(start + dt.timedelta(days=duration)).isoformat(), critical_path=path, schedule=rows,
                  mermaid_gantt="\n".join(gantt))
    except (KeyError, TypeError, ValueError) as e:
        return err(f"invalid task list: {e}")

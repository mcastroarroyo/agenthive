# Quillmark Bank — KPI Dictionary and Board Reporting Style Guide

*Synthetic reference for the Wursta Agent Hive demo. Quillmark Bank is fictional; definitions are illustrative.*

**Owner:** Strategy & Performance Office · **Approved by:** Executive Committee, 2026-02-10

## 1. KPI definitions (as agreed by the board)

| KPI | Definition | Better when | Source column |
|---|---|---|---|
| Revenue | Direct revenue of the business unit (NII + fees) | Higher | revenue_usd_m |
| Cost-income ratio (CIR) | Direct operating expense excluding credit provisions / revenue | Lower | cost_income_ratio_pct |
| Net interest margin (NIM) | Net interest income / average interest-earning assets, annualised | Higher | net_interest_margin_pct |
| NPL ratio | Non-performing loans (90+ days past due for cards) / gross loans | Lower | npl_ratio_pct |
| Credit provisions | Expected-credit-loss charge for the month | Lower | credit_provisions_usd_m |
| AUM | Private Wealth assets under management at month end | Higher | aum_usd_m |
| Net new assets (NNA) | Client inflows minus outflows, excluding market moves | Higher | net_new_assets_usd_m |
| NPS | Relationship Net Promoter Score, survey of active customers | Higher | nps |
| Digital active % | Active customers who used a digital channel in the last 30 days | Higher | digital_active_pct |
| Complaints | Complaints received in the month | Lower | complaints |
| Failed transaction % | Failed / attempted transactions by channel (abandonment % for the contact centre) | Lower | fin_channel_daily.failed_pct |

**Bank totals.** Sum volumes (revenue, expense, customers, complaints). Never average ratios across business units —
recompute them from their numerator and denominator (e.g. total opex / total revenue) or show them by unit.
Business-unit CIR excludes Corporate Center costs; say so when quoting it.

**Comparisons.** Quarterly KPIs compare against the same quarter of the prior year (seasonality) and against plan
where a plan exists. Monthly anomalies compare against the trailing trend.

## 2. Known events calendar (for explaining anomalies)

| Date | Event | Expected footprint |
|---|---|---|
| 2026-03 onward | Policy-rate cuts | NIM compression in Retail, Commercial and Cards |
| 2026-05-12 to 2026-05-13 | Mobile-app outage (08:10-14:40 on 12 May; degraded on 13 May) | Mobile failed % spike, online banking and contact-centre volumes up, Retail NPS and digital-active dip in May, complaints up, ops-loss refunds |
| 2026-07 to 2026-08 | Card-not-present fraud ring (peak 4-8 August) | Card fraud losses, card complaints, contact-centre volume and abandonment spike; Cards CIR up |
| 2026-07 | Commercial real-estate (office) downgrade | Commercial provisions and NPL ratio up |
| 2026-09 | Mobile-app relaunch campaign (moved from October) | Marketing spend up; digital activity up |

If an anomaly does not match a known event, say so and recommend who should investigate — never speculate.

## 3. Board writing style

1. **Lead with the answer** in one sentence with the number and the comparison ("Q3 revenue was USD X m, Y% above Q3
   2025").
2. **Three to five insights**, each with a number, a comparison and a cause supported by data or a documented event.
3. **One table** at most, with units in the header (USD m, %, pp).
4. **What to watch** — one or two forward-looking items framed as questions or risks, not forecasts.
5. Use percentage points (pp) for changes in ratios and percent (%) for changes in amounts.
6. Round to one decimal for ratios and to USD 0.1 m for amounts; never present more precision than the data has.
7. State the data cut-off ("data to 30 September 2026") and that figures are management information (unaudited).

## 4. Data governance

The warehouse tables are refreshed after month-end close (fifth business day). Channel data is daily. Figures in
this demo are synthetic; any resemblance to a real institution is coincidental.

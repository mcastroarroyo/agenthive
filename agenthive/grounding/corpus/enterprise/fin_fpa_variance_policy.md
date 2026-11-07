# Quillmark Bank — FP&A Variance Policy and Q3 2026 Management Context (FIN-POL-12)

*Synthetic finance policy for the Wursta Agent Hive demo. Quillmark Bank is fictional; figures are illustrative.*

**Owner:** Head of FP&A · **Applies to:** monthly close, quarterly business reviews and the CFO pack

## 1. Plan versions

- **Budget** — approved annual plan (FY2025 Budget, FY2026 Budget), stored as scenario `budget`.
- **Reforecast** — the Q3 2026 Reforecast (6+6) prepared on 2026-07-20: January-June are actuals, July-December
  are forecast. Stored as scenario `forecast`.
- **Full-year outlook** = actuals for closed months + reforecast for the remaining months.
- The latest closed month is September 2026 (Q3 2026 closed on 2026-10-06).

## 2. Sign conventions

Ledger amounts are stored as positive numbers for both revenue and expense. Variance = actual − plan.
A revenue variance is **favourable** when positive; an expense variance is favourable when negative.
Pre-tax profit impact = revenue variances − expense variances.

## 3. Materiality — when commentary is required

A variance requires written commentary when **both** of these are true:

- the absolute variance is USD 250,000 or more, **and**
- the variance is 5% or more of plan;

or, regardless of percentage, when the absolute variance is USD 1,000,000 or more.

Commentary for an unfavourable material variance states the root cause, the owner and the recovery action (or why
none is possible). Commentary for a favourable material variance states the driver and whether it is one-off or
run-rate. Commentary is drafted by the finance business partner and approved by the cost-centre owner.

## 4. Chart of accounts (management view)

| Account | Name | P&L line |
|---|---|---|
| 4100 | Net interest income | Net interest income |
| 4200 | Fees & commissions | Fee & commission income |
| 4300 | Advisory & management fees | Wealth fees |
| 4400 | Interchange & card fees | Card & payment fees |
| 6100 | Salaries & benefits | Personnel |
| 6200 | Technology & software | Technology |
| 6250 | Cloud & data centre | Technology |
| 6300 | Occupancy | Occupancy |
| 6400 | Marketing | Marketing |
| 6500 | Professional fees | Professional fees |
| 6600 | Fraud & operational losses | Fraud & operational losses |
| 6700 | Credit loss provisions | Credit loss provisions |

**Business units and cost centres:** Retail Banking (RB-100 Branch Network, RB-120 Consumer Lending, RB-200
Digital Banking), Commercial Banking (CB-300 Commercial Lending, CB-310 Treasury & Payment Services), Private
Wealth (PW-400 Advisory, PW-410 Trust & Estate), Cards & Payments (CP-500 Card Issuing, CP-510 Merchant Services),
Corporate Center (CC-900 Technology, CC-910 Operations, CC-920 Risk & Compliance). Corporate Center costs are not
allocated to business units in management reporting.

## 5. Q3 2026 management context (known drivers)

These events were reported by cost-centre owners during the Q3 close. Use them to explain variances, but always
quantify from the ledger.

- **Data-centre exit slipped (CC-900, account 6250).** The FY2026 Budget assumed the legacy data centre would close
  at the end of June 2026 and cloud and data-centre cost would fall by about 45% from July. The exit slipped to
  October 2026; both environments ran in parallel through Q3, and migration egress added cost. The Q3 Reforecast
  anticipated most of this. Owner: CTO office.
- **Software licence true-up (CC-900, account 6200).** A one-off true-up of about USD 1.1 million from the core
  banking platform vendor was booked in August 2026. It was not in the budget or the reforecast. One-off.
- **Card-fraud ring (CP-500 and CP-510, account 6600).** A card-not-present fraud ring hit in July and peaked in
  August 2026; losses normalised in September after new device-binding controls. Card complaints and contact-centre
  volumes spiked in the same weeks.
- **Commercial real-estate downgrade (CB-300, account 6700).** Office-sector exposures were downgraded in July 2026;
  provisions rose to roughly USD 1.9 million per month versus a USD 1.2 million monthly budget.
- **Margin compression (account 4100).** Policy-rate cuts from March 2026 compressed net interest income across
  lending units; the budget assumed a flat margin.
- **Wealth fees ahead of plan (PW-400, PW-410, account 4300).** Market appreciation and strong net new assets lifted
  advisory fees through 2026 — run-rate, not one-off.
- **Commercial hiring freeze (CB-300, account 6100).** Vacancies left open since April 2026 — favourable but
  temporary.
- **KYC remediation (CC-920, account 6500).** Contractors engaged from July 2026 to clear the periodic-review backlog.
- **Digital campaign timing (RB-200, account 6400).** The mobile-app relaunch campaign planned for October ran in
  September — a timing difference within the year.
- **May 2026 mobile outage (CC-910, account 6600).** Customer refunds and fee waivers after the 12-13 May outage.

## 6. Forecast accuracy

Forecast accuracy is measured as MAPE of the reforecast versus actuals by cost centre for the quarter following the
reforecast. Target: below 3% for revenue and below 5% for expense lines.

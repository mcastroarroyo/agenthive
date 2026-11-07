# Quillmark Bank — AML Transaction Monitoring & Sanctions Screening Rulebook (FCP-3 / SP-2)

*Synthetic rulebook for the Wursta Agent Hive demo. Quillmark Bank, the jurisdictions and the lists are fictional.
Thresholds are illustrative and are not regulatory guidance.*

**Owner:** Chief Financial Crime Officer · **Scenario version:** 4.2 (thresholds last reviewed 2026-07-01)

## 1. Transaction-monitoring scenarios

| Rule | Name | Trigger | Weight |
|---|---|---|---|
| TM-01 | Structuring | 3 or more cash deposits of USD 8,000-9,999.99 within 7 days, totalling USD 25,000 or more | 45 |
| TM-02 | Rapid movement (pass-through) | Incoming wire of USD 50,000 or more with 80% or more wired out within 72 hours | 50 |
| TM-03 | High-risk jurisdiction | Any transfer of USD 10,000 or more with a high-risk jurisdiction; weight 45 when the total in the window reaches USD 100,000 | 30 / 45 |
| TM-04 | Velocity vs profile | Outflows in the window at least 5x the expected outflow in the KYC profile | 25 |
| TM-05 | Dormant reactivation | No activity for 12 months or more, then inflows of USD 50,000 or more | 30 |
| TM-06 | Round-amount wires | 3 or more outgoing wires in exact multiples of USD 10,000 | 10 |

The default look-back window is 30 days. TM-02 applies to wire transfers only — payroll and other ACH outflows of
legitimate businesses are excluded after the 2026 tuning exercise reduced false positives from dental, medical and
retail clients.

**High-risk jurisdictions (synthetic list):** Isla Marant, Republic of Calvera, Free Port of Ostravia.

## 2. Scoring and severity

The account risk score is the sum of the weights of the rules that fired, multiplied by 1.5 for customers rated
high risk at KYC, capped at 100.

| Score | Severity | Required action | Service level |
|---|---|---|---|
| 70-100 | High | Escalate: open an investigation case; hold further outgoing wires pending review | Case opened within 2 business days |
| 40-69 | Medium | Level-1 analyst review; request source of funds if unexplained | 5 business days |
| 1-39 | Low | Document the disposition and close | 5 business days |

## 3. Investigation and reporting

- Investigators decide each case within 30 calendar days of escalation (target 10 business days for high
  priority).
- If activity is determined to be suspicious, the regulatory report is filed within 30 calendar days of the
  determination.
- **No tipping off:** staff must never tell or imply to the customer that an alert, investigation or report
  exists. Customer-facing teams receive only "hold pending review" instructions.
- Case narratives state facts: who, what, when, where, amounts, transaction ids and why the activity is unusual for
  this customer. Opinions and speculation are not permitted.

## 4. Sanctions, PEP and adverse-media screening (SP-2)

Every customer at onboarding and every wire before release is screened against the consolidated sanctions list,
the PEP list and adverse media. Fuzzy name matching normalises legal suffixes (LLC, Ltd, S.A., Inc) and common
abbreviations.

| Match score | Disposition | Action |
|---|---|---|
| 0.92 or more | Strong potential match | Hold the payment or relationship; escalate to Sanctions Compliance within 24 hours |
| 0.85-0.92 | Potential match | Analyst compares identifiers (date of birth, address, registration number) within 24 hours before release |
| 0.80-0.85 | Weak match | Document and clear with rationale |

A match is cleared as a **likely false positive** when a strong identifier differs (for example a birth year more
than 2 years apart, or a different registration country) — the rationale and evidence must be retained.
Initial-plus-surname matches (e.g. "K. Arvelo") are always reviewed by an analyst.

PEP matches are not prohibited relationships: they trigger enhanced due diligence (source of wealth and senior
management approval).

## 5. Known patterns in 2026

- Q3 2026 saw an increase in pass-through activity via individual accounts receiving funds from the Republic of
  Calvera and wiring onward within two days.
- Dormant real-estate holding companies receiving large inbound wires followed by escrow-style outgoing wires were
  identified as an emerging typology in October 2026.
- Cash structuring across multiple branches (the same customer using 3 or more branches within a week) remains the
  most common TM-01 pattern.

## 6. Quality assurance

Financial Crime QA samples 10% of closed alerts monthly. Late alerts and late potential-match dispositions are
recorded as control exceptions in the GRC register (see the Compliance Control Framework).

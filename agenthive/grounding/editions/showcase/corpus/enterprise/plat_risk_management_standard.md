# Delivery Risk Management Standard

**Owner:** Priya Raman, Head of PMO (Transformation Office) · **Last reviewed:** 2026-05-12 · **Status:** current

## Purpose

A single, quantified way to identify, score, own and escalate delivery risks on every programme in the company.
Prometheus (the Pantheon risk and schedule agent) scores registers with the `score_risk_register` tool using exactly
the scales below.

## Risk versus issue

A **risk** is something that may happen and would affect the programme. An **issue** is something that has
happened. When a risk materialises, close it as "occurred", open an issue and link the two. Issues are managed in
the RAID log and the weekly status report.

## Scoring — 5 × 5

**Likelihood (L)**

| Score | Label | Guide |
|---|---|---|
| 1 | Rare | Less than 10% |
| 2 | Unlikely | 10–30% |
| 3 | Possible | 30–50% |
| 4 | Likely | 50–80% |
| 5 | Almost certain | More than 80% |

**Impact (I)** — use the highest applicable row.

| Score | Schedule | Cost | Quality / reputation |
|---|---|---|---|
| 1 | Under 2 days | Under 1% of budget | Cosmetic |
| 2 | 2–5 days | 1–3% | Minor rework, business unaware |
| 3 | 1–2 weeks | 3–7% | Visible defect or a milestone missed |
| 4 | 2–4 weeks | 7–15% | Go-live at risk; business sponsor escalation |
| 5 | More than 4 weeks | More than 15% | Regulatory breach, data loss or contract dispute |

**Score = L × I**, from 1 to 25.

| Score | Rating | Response |
|---|---|---|
| 20–25 | **Critical** | Sponsor informed within 48 hours; mitigation plan reviewed daily |
| 12–19 | **High** | Reported in the weekly status report; mitigation reviewed weekly by the PM |
| 6–11 | **Medium** | Reviewed every two weeks |
| 1–5 | **Low** | Reviewed monthly; may be accepted |

## Mandatory fields

Every register entry has: id, description written as "cause → event → consequence", likelihood, impact, score,
rating, **a named owner (a person, never a team)**, a mitigation with a due date, a contingency for critical and high
risks, the date raised and the trend (rising, stable, falling). A register with ownerless or unmitigated high risks
fails quality gates G3, G4 and G5.

## Response strategies

- **Avoid** — change the plan so the risk cannot occur (for example, remove a dependency).
- **Reduce** — lower likelihood or impact (for example, build against a mock while waiting for a third-party API).
- **Transfer** — move it contractually (for example, a dependency clause in the vendor contract).
- **Accept** — only for low risks, or for medium risks with business sponsor agreement, recorded in writing.

## Escalation

1. The risk owner updates the risk at least at the rating's review cadence.
2. A risk that moves to **high** is raised at the next weekly programme status meeting.
3. A risk that moves to **critical** is escalated by the programme manager to the business sponsor and the
   Transformation Office director **within 48 hours**, with a recommended decision.
4. If a critical risk has no agreed mitigation within 5 business days, the Transformation Office director raises it
   at the steering committee and the PMO is informed.

## Early-warning signals

Meeting sentiment is a leading indicator. The `detect_meeting_sentiment_risk` skill scores steering and status
meeting transcripts for dissatisfaction, scope creep, disengagement and timeline risk. A "high" score creates a
review task for the programme manager within one business day; it does not replace judgement.

## Risks we see on most programmes

| Risk | Typical L × I | Usual mitigation |
|---|---|---|
| Third-party credentials or APIs arrive late | 4 × 4 | Escalate at kickoff; build against mocks; dependency clause in the vendor contract |
| Business subject-matter experts unavailable for testing | 4 × 3 | Name testers in the project charter; part-time UAT plan |
| Scope added through "small" requests | 4 × 3 | Change requests with estimates; Won't list in the backlog |
| Source data quality worse than assumed | 3 × 4 | Profile sources in week 1; data-quality budget line |
| Change resistance at go-live | 3 × 3 | Champions, pilot group, floor-walkers |
| Key business staff leaving | 2 × 4 | Knowledge capture; shadowing |

## Register hygiene

- Review the full register at least every two weeks and before every steering committee.
- Close risks explicitly with a reason; do not delete them.
- Keep the register in the programme's shared drive and mirror high and critical risks as Jira issues of type Risk
  (Jira Taxonomy and Agile Delivery Standards).

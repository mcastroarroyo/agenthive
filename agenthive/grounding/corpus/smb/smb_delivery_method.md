# The Kitewing Delivery Method — project management standards

Owner: Ines Duarte (Senior Implementation Consultant) with Arjun Mehta (Engineering Manager). Last reviewed 2026-08-20. Synthetic demo document — Kitewing Software is fictional.

The same lightweight method is used for customer implementations, product launches and internal projects. It fits a 60-person company: one page of rules, no PMO.

## Phases and gates

| Phase | Purpose | Gate to exit |
|---|---|---|
| 1. Initiate | Brief, sponsor, success criteria, team | Sponsor approves the brief and success criteria |
| 2. Design | Workshops, solution design, WBS, plan | Plan approved: schedule, RACI, risks, budget |
| 3. Build | Configuration, development, data migration dry runs | Build complete; two migration dry runs passed (implementations) |
| 4. Test | QA, UAT, security review | UAT sign-off by the customer or product owner; no open P1/P2 defects |
| 5. Deploy | Training, cutover, go-live | Go/no-go meeting with the sponsor |
| 6. Hypercare | Stabilise, hand over to support / CSM | Two weeks with no P1 and adoption above 80% |

## Work breakdown structure (WBS)

- Two levels: 3-6 phases and 8-14 work packages for a typical project.
- Every work package has **one accountable owner**, a size (S/M/L), a type, its dependencies and a named deliverable.
- Customer-side work packages are owned by a named customer role (for example "IT Manager (customer)").

## Estimating

- Use **three-point (PERT) estimates** from our reference projects: expected = (optimistic + 4 × most likely + pessimistic) / 6.
- Reference estimates are in working days for the standard crew; convert to calendar days (× 7/5) for the schedule.
- **Contingency:** 10% for low-uncertainty plans, 15% by default, **20% when a legacy migration or a third party is on the critical path.**
- Never commit a date from a single-point guess. Report the expected finish and the P80 finish when a customer asks "how sure are you?"

## Scheduling

- Compute the critical path with the scheduling tool (critical-path method) — never by hand.
- Respect blackout periods: **no go-live or cutover between 21 December and 1 January**, and none on a Friday or on the customer's peak-season Mondays.
- Phase large rollouts by branch: the first branch goes live, then the rest after one stable week.
- Data migration needs **at least two dry runs** before the final cutover export.

## RACI

- Rows are phases or major work packages; columns are people or roles.
- **Exactly one A (accountable) per row.** R = does the work, C = consulted before, I = informed after.
- The sponsor is usually A for go/no-go only.

## Risk management

- Score each risk with likelihood and impact from 1 to 5; exposure = likelihood × impact.
- **High (15 or more):** named owner and mitigation within one week, reviewed weekly. **Medium (8-14):** reviewed every two weeks. **Low:** monitored.
- Start every plan from the risk library for the project type (customer implementation, product launch, internal systems, compliance, marketing campaign) and add project-specific risks.

## Status and RAG

Weekly status is due **Friday by 12:00** to the project's distribution list. Status is computed from the task tracker with earned value:

| RAG | Definition |
|---|---|
| Green | SPI and CPI at least 0.92, nothing late or blocked, forecast on or before target |
| Amber | SPI or CPI below 0.92, or any late or blocked task, or forecast up to 5 days late |
| Red | SPI or CPI below 0.75, or forecast more than 5 days late |

- SPI = earned value ÷ planned value to date; CPI = earned value ÷ actual hours.
- A status update has: RAG and last week's RAG, 3-line summary, late and blocked work with unblock actions, next 7 days, decisions needed. Under 200 words.
- Steering meeting monthly (or at every gate) with the sponsor.

## Escalation

- A blocker older than **5 business days** goes to the sponsor.
- Red status for two consecutive weeks triggers a recovery plan within 3 business days.
- Customer-side blockers are escalated to the customer sponsor by our sponsor, not by the project team.

## Change control

- Any change that adds more than 2 days of effort or $1,000 of cost needs a change request: description, impact on schedule, cost and risk, and sponsor approval.
- Out-of-scope requests (for example custom reports or new languages) are logged and planned for a later phase by default.

## Retrospectives

- Run a retrospective at the end of every sprint, at project mid-point and after go-live. 45-60 minutes.
- **Start with follow-through:** review last retro's actions. An action carried over twice is either made action #1 with a new owner or explicitly dropped.
- Cards go into three columns: went well, to improve, ideas. Vote, cluster into themes, find the root cause of the top themes ("ask why twice").
- Agree **at most three SMART actions** (specific, measurable, owner, due within two weeks) and file them in the task tracker.
- Run a health check (fun, pace, learning, teamwork, delivering value, tooling) on a 1-5 scale and watch the trend.

## Handover

- Implementations hand over to the CSM and support at the end of hypercare with: configuration summary, open issues, adoption dashboard and the customer's success criteria.

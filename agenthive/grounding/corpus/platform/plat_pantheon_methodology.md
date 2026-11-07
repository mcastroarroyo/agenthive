# Pantheon Engagement Methodology

**Owner:** Sofia Lindqvist, Advisory Practice Director · **Last reviewed:** 2026-09-25 · **Status:** current

## What Pantheon is

Pantheon is Wursta's AI-assisted advisory method. A coordinator agent, **Hermes**, decomposes a client problem and
calls five specialist agents, each with its own tools and grounding:

| Specialist | Lens | Main outputs | Deterministic tools |
|---|---|---|---|
| Xenophon | Agile analyst | Epics, user stories with Gherkin, MoSCoW, sized backlog, Jira import | `estimate_story_points`, `create_jira_issues` |
| Daedalus | Cloud architect | Target architecture by layer, rejected alternatives, monthly cost, diagram | `estimate_gcp_monthly_cost`, `render_architecture_diagram` |
| Ariadne | Data architect | Source profile, star schema, ERD, validated DDL | `profile_source_systems`, `render_erd`, `validate_ddl` |
| Prometheus | Risk and delivery | Risk register, critical path, schedule, what-ifs | `score_risk_register`, `critical_path` |
| Proteus | Value advisor | Solution concepts, ROI, battlecard | `compute_roi`, `competitive_battlecard` |

Numbers — points, costs, dates, scores, ROI — always come from the tools, never from the model's head. Hermes
reconciles the outputs and compiles the client deliverable with `compile_engagement_report`.

## Two ways to run it

**Pantheon Rapid Assessment** (parallel, Flash and Flash-Lite): the five lenses read the same brief at the same time
and a synthesis step merges them into a one-page assessment. Use it the same day as a discovery call, for
qualification, or as the input to a SOW. Cost is a few cents per run.

**Hermes full engagement** (coordinator, Argon): Hermes decides which specialists are needed, gives each a focused
brief, iterates when outputs conflict (for example, the architecture cost exceeds the budget Proteus assumed), and
produces an engagement report. Use it when the problem is ambiguous, the deal is large, or the client expects a
strategy document.

Rule of thumb: start with the rapid assessment; escalate to Hermes when the rapid assessment shows more than two
major unknowns or when the opportunity justifies a deep dive.

## Phases

### Phase 0 — Intake (day 0)

Collect the raw material: discovery notes, transcripts, RFPs, whiteboard photos, current-state diagrams. Strip or
anonymise personal data before it enters the agents (see Security and PII Handling for Demos). Record the client's
objectives in their own words.

### Phase 1 — Rapid assessment (day 0–1)

Run the rapid assessment. The engagement lead reviews it, corrects anything the client contradicted, and shares a
one-page version internally within 24 hours of discovery.

### Phase 2 — Deep dive (week 1–2)

Run Hermes with the corrected brief and any new material. Typical sequence: Xenophon and Ariadne first (they expose
scope and data unknowns), then Daedalus (architecture and cost), Prometheus (schedule and risks using the backlog and
architecture), and Proteus last (value and ROI using the real costs). Validate key assumptions with the client in one
workshop.

### Phase 3 — Proposal and SOW (week 2–3)

Turn the engagement report into the proposal and SOW. Scope comes from the Must stories, the fee from the sized
backlog and the architecture, and the risk section and contingency from Prometheus. Quality gate G2 reviews the SOW
(Delivery Quality Gates).

### Phase 4 — Handover to delivery

Push the backlog to Jira with the standard taxonomy (labels `wursta`, `pantheon` and the MoSCoW label), hand over the
risk register, architecture decision records and the data model. The delivery team owns them from here.

## The engagement report

Standard structure: executive summary (five bullets); situation and objectives; recommended architecture with
rejected alternatives; backlog highlights; data model; risks and schedule with the critical path; value and ROI;
next steps; appendix of assumptions. Keep it under 15 pages; detail goes into appendices and the Jira project.

## Human review is mandatory

- Every client-facing Pantheon output is reviewed by an accountable Wursta lead before it leaves the company.
- Reviewers check: numbers match the tool outputs; assumptions are stated; nothing confidential from another client
  appears; the recommendation is consistent across sections.
- Agents make recommendations; people make commitments. Prices and dates in a proposal are approved by the
  engagement director.

## Quality bar

A good Pantheon output names the client's constraints explicitly, rejects at least two alternatives with reasons,
quantifies the top risks with owners, and ends with three concrete next steps that have owners and dates.

## Measuring the method

We track time from discovery to assessment, assessments per architect per week, win rate on assessed deals, and the
variance between Pantheon estimates and actuals at project closure (captured at gate G6).

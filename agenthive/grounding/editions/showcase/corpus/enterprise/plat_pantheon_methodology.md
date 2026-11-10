# Pantheon Transformation Methodology

**Owner:** Sofia Lindqvist, Transformation Office Director · **Last reviewed:** 2026-09-25 · **Status:** current

## What Pantheon is

Pantheon is the Transformation Office's AI-assisted method for shaping programmes. A coordinator agent, **Hermes**,
decomposes a business problem and calls five specialist agents, each with its own tools and grounding:

| Specialist | Lens | Main outputs | Deterministic tools |
|---|---|---|---|
| Xenophon | Agile analyst | Epics, user stories with Gherkin, MoSCoW, sized backlog, Jira import | `estimate_story_points`, `create_jira_issues` |
| Daedalus | Cloud architect | Target architecture by layer, rejected alternatives, monthly cost, diagram | `estimate_gcp_monthly_cost`, `render_architecture_diagram` |
| Ariadne | Data architect | Source profile, star schema, ERD, validated DDL | `profile_source_systems`, `render_erd`, `validate_ddl` |
| Prometheus | Risk and schedule | Risk register, critical path, schedule, what-ifs | `score_risk_register`, `critical_path` |
| Proteus | Value and ROI | Solution concepts, ROI, market-options battlecard | `compute_roi`, `competitive_battlecard` |

Numbers — points, costs, dates, scores, ROI — always come from the tools, never from the model's head. Hermes
reconciles the outputs and compiles the steering-committee report with `compile_engagement_report`.

## Two ways to run it

**Pantheon Rapid Assessment** (parallel, Flash and Flash-Lite): the five lenses read the same brief at the same time
and a synthesis step merges them into a one-page assessment. Use it the same day as a discovery workshop, for idea
qualification (gate G0), or as the input to a business case. Cost is a few cents per run.

**Hermes strategy report** (coordinator, Argon): Hermes decides which specialists are needed, gives each a focused
brief, iterates when outputs conflict (for example, the architecture cost exceeds the budget Proteus assumed), and
produces a strategy report. Use it when the problem is ambiguous, the investment is large, or the steering committee
expects a strategy document.

Rule of thumb: start with the rapid assessment; escalate to Hermes when the rapid assessment shows more than two
major unknowns or when the size of the investment justifies a deep dive.

## Phases

### Phase 0 — Discovery workshops with the business (day 0)

Run the discovery workshops and collect the raw material: workshop notes, transcripts, process maps, whiteboard
photos, current-state diagrams. Strip or anonymise personal data before it enters the agents (see Security and PII
Handling for AI Pilots and Demos). Record the business's objectives in its own words.

### Phase 1 — Rapid assessment (day 0–1)

Run the rapid assessment. The programme lead reviews it, corrects anything the business contradicted, and shares a
one-page version within the Transformation Office within 24 hours of the discovery workshop.

### Phase 2 — Strategy report (week 1–2)

Run Hermes with the corrected brief and any new material. Typical sequence: Xenophon and Ariadne first (they expose
scope and data unknowns), then Daedalus (architecture and cost), Prometheus (schedule and risks using the backlog and
architecture), and Proteus last (value and ROI using the real costs). Validate key assumptions with the business in
one workshop.

### Phase 3 — Business case and funding approval (week 2–3)

Turn the strategy report into the business case. Scope comes from the Must stories, the budget from the sized
backlog and the architecture, and the risk section and contingency from Prometheus. Quality gate G2 reviews the
business case and approves funding (Delivery Quality Gates).

### Phase 4 — Mobilisation

Push the backlog to Jira with the standard taxonomy (labels `transformation`, `pantheon` and the MoSCoW label), hand
over the risk register, architecture decision records and the data model. The programme team owns them from here.

## The strategy report

Hermes compiles it as the steering-committee report. Standard structure: executive summary (five bullets); situation
and objectives; recommended architecture with rejected alternatives; backlog highlights; data model; risks and
schedule with the critical path; value and ROI; next steps; appendix of assumptions. Keep it under 15 pages; detail
goes into appendices and the Jira project.

## Human review is mandatory

- Every Pantheon output shared outside the Transformation Office is reviewed by an accountable lead before it is
  shared.
- Reviewers check: numbers match the tool outputs; assumptions are stated; nothing confidential from another business
  unit or programme appears; the recommendation is consistent across sections.
- Agents make recommendations; people make commitments. Budgets and dates in a business case are approved by the
  business sponsor and Finance at gate G2.

## Quality bar

A good Pantheon output names the business's constraints explicitly, rejects at least two alternatives with reasons,
quantifies the top risks with owners, and ends with three concrete next steps that have owners and dates.

## Measuring the method

We track time from discovery workshop to assessment, assessments per architect per week, the share of assessed
business cases approved at gate G2, and the variance between Pantheon estimates and actuals at programme closure
(captured at gate G6).

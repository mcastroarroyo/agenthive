# Agent Deployment Checklist (ADK + Agent Engine)

**Owner:** Tomás Herrera, AI Engineering Lead (AI CoE) · **Last reviewed:** 2026-10-02 · **Status:** current
**Supersedes:** Agent Deployment Checklist v1 (Cloud Run + LangChain), which no longer applies.

## Purpose and scope

This is the source of truth for releasing an agent built with the Google Agent Development Kit (ADK) and hosted on
Vertex AI Agent Engine. It covers demo and pilot agents in the company's agent catalog and production agents used by
the business. Production agents must meet every item. Demo agents must meet the items marked **[demo]**.

## 1. Design

- **[demo]** Catalog entry complete: id, tagline, persona, use cases, model tier with a reason, tools, grounding,
  a numbered instruction, output format, at least three sample prompts that work with the demo data, and KPIs.
- **[demo]** Model tier follows the Model Tier Policy — the cheapest tier that does the job; Argon only with a
  written justification and at most one or two per realm.
- Pattern chosen deliberately (single, sequential, parallel, coordinator or loop) and documented in the entry.
- Human-in-the-loop points identified for every action with side effects (sending, booking, writing to a system).

## 2. Tools

- **[demo]** Every function tool has a type hint on every parameter and a docstring that explains the arguments and
  the return value. The docstring is the tool description the model sees — write it for the model.
- **[demo]** Tools return a dictionary with a `status` of ok or error and never raise on bad input.
- **[demo]** Side-effecting tools are simulated in demos and say so in their result.
- Tool names are globally unique and specific (`fin_portfolio_exposure`, not `get_data`).
- Tools call only approved Google APIs through the runtime's service identity; no other network calls.

## 3. Grounding and data

- **[demo]** Every knowledge-base document has a title, an owner and a review date (Knowledge Management Policy).
- One data store per realm; documents indexed; each sample prompt returns the expected document in the top three.
- BigQuery access is read-only, restricted to named tables, with a maximum-bytes-billed cap per query.
- **[demo]** Only synthetic data in demo environments (Security and PII Handling for AI Pilots and Demos).

## 4. Quality

- **[demo]** Offline tests pass with `HIVE_OFFLINE=1`: catalog integrity, tool contracts and agent builds.
- An evaluation set of at least 20 prompts with expected tool calls and reference answers; pass rate of 85% or more
  before go-live. Regressions block deployment.
- Red-team prompts: prompt injection through documents and emails, requests for out-of-scope actions and attempts to
  extract personal data.
- Latency budget: p50 under 8 seconds for single agents and under 25 seconds for coordinators.

## 5. Security

- The runtime uses a dedicated service identity with least-privilege roles; no user-managed service-account keys.
- Secrets live in Secret Manager — never in code, the catalog or committed environment files.
- No project IDs, project numbers or service-account emails in the repository, slides or screenshots.
- Organisation policies and VPC Service Controls perimeters reviewed for production agents.
- Input and output screening (for example Model Armor) configured where the data owner or Information Security
  requires it — verify current product availability in the target region.

## 6. Deployment

- Build the agent from the catalog with the factory; no hand-written per-agent glue code.
- Deploy to Agent Engine in the approved region. Record the resource name in the deployment log, not in the
  repository.
- Cloud Trace and Cloud Logging enabled. Prompts and responses are logged only if the data classification allows.
- Budget alert on the project at 50%, 90% and 100% of the monthly forecast.
- Smoke test: run every sample prompt against the deployed agent; all must succeed.

## 7. Operations

- A named business owner and a named technical owner.
- A runbook: how to roll back to the previous version, how to disable a single tool, who is on call.
- Monthly review of cost per conversation and tool error rate.
- Re-run the evaluation set quarterly and after any model version change.

## Sign-off

The technical owner signs sections 1–6; the business owner signs section 7 and the evaluation results. For production
agents the sign-off is evidence for quality gate G5 (see Delivery Quality Gates).

## Common failure modes

- **Vague tool docstrings** make the model call the wrong tool. Fix the docstring before touching the instruction.
- **Single curly braces in instructions** are read by ADK as state templating. Use double braces only for step
  outputs, and never a single-brace word.
- **Coordinators with too many sub-agents** (more than six) become slow and erratic; split them by realm.
- **Demo data that does not match the sample prompts** — every sample prompt must work against the fixtures.
- **Silent model upgrades** — pin model versions in the tier configuration and re-run evaluations before moving.

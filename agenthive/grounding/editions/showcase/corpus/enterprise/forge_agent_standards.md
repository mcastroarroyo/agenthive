# Agent Forge Standards for Business-Unit Agents (2026.11) — Spec, Code, Tests and Tune-ups

**Owner:** Elena Marsh, Agent Forge Platform Owner (AI CoE) · **Last reviewed:** 2026-11-01 · **Status:** current
**Supersedes:** Forge standards 2026.09.

## Purpose

Every agent the AI Centre of Excellence (AI CoE) builds or changes in Agent Forge for a Halvern Group business unit
must meet these standards. The Plan stage checks the spec, the Build stage checks the code with the static check, the
Test stage enforces the release gate, and tune-up jobs bring older agents up to the current version of this document
without changing what they do.

## The spec template

A spec is complete when it has: name, business unit, goal (one sentence), users, inputs, outputs, topology,
connectors, tools, secrets, memory, time zone, settings, test cases, acceptance criteria and open questions.

- **Topology** — `single` by default. Use a `workflow` of ordered sub-agents only when stages need different tools,
  different models or an approval between them (for example: search emails, then process orders).
- **Connectors** — ids from the connector registry, each marked ready, draft or missing. Missing connectors go to the
  connector build path first; a draft connector blocks the agent.
- **Tools** — snake_case names, the connector method each calls and a one-line purpose (it becomes the docstring).
- **Secrets** — NAMES only, in UPPER_SNAKE_CASE. Google Workspace connectors act as the signed-in user through OAuth
  and need no secrets.
- **Memory** — ids, timestamps and short summaries only.
- **Settings** — schedule, time zone, `DRY_RUN=true` in sandbox for any send or write.
- **Tests and acceptance** — at least one test per tool and at least one acceptance test per acceptance criterion;
  never fewer than three test cases.
- **Clarifying questions** — at most three, each with the default the forge assumes if nobody answers, so a build
  never stalls while the business unit is consulted.

## Forge standards checklist (FS)

| Id | Standard | What is checked |
|---|---|---|
| FS-01 | Tool contract | Docstring (30+ characters, with an Args section), type hints on every parameter, a return type, a status ok/error dict |
| FS-02 | Secrets by reference | Secrets read from the environment (test pane) or Secret Manager; never in code, prompts, tests or logs |
| FS-03 | Test coverage | One test per tool, one acceptance test per criterion; the whole suite passes on every change |
| FS-04 | Pinned connector versions | Each connector pinned to a minor version; upgrades are explicit modify jobs |
| FS-05 | Retries and backoff | 429 and 5xx retried up to 3 times with exponential backoff; a timeout on every call |
| FS-06 | Pagination to the end | List calls follow pagination to the last page or a declared cap, and say when the cap was hit |
| FS-07 | Explicit time zone | Dates computed and shown in the business unit's declared time zone |
| FS-08 | Memory hygiene | No raw email bodies or personal data in memory; 90-day retention |
| FS-09 | Structured, redacted logging | Structured logs without secrets or full payloads; prompts and logs pass redaction |
| FS-10 | Model from tier config | No hard-coded model ids; the model comes from the forge tier configuration |
| FS-11 | Output contract | A declared output format checked by an acceptance test |
| FS-12 | Side-effect guard | Sends and writes are drafts or dry runs in sandbox and need explicit approval |
| FS-13 | Workspace as the signed-in user | Workspace access through OAuth as the user; no shared mailbox passwords or broad delegation |
| FS-14 | Plain-English errors | User-facing errors never include stack traces, tokens or raw payloads |

## Generated code requirements

- Google Agent Development Kit (ADK) in Python: `root_agent` defined at module level; `Agent` for single agents,
  `SequentialAgent` with `sub_agents` for workflows.
- Connector calls go through the forge's connector API clients, never raw credentials in code.
- The static check parses the code and tests (it never executes them) and fails on: syntax errors, missing ADK
  structure, tools without docstrings or type hints, hard-coded secrets, required secrets that are never read from the
  environment or Secret Manager, and dangerous calls (eval, exec, shell). It warns on hard-coded model ids, network
  calls without timeouts and tools without a test.

## The release gate

A version may be deployed to the sandbox only when every test in its suite passes in the test pane. Blocked tests —
for example because a session secret is missing — count as failures. A failing regression test is never skipped or
deleted to pass the gate.

## Change requests

A change request from a business unit produces a new version. The builder changes only what the request needs, adds
a regression test named after the problem, and the whole suite is re-run. Typical example: "the LTV in the
spreadsheet is always 0" — the regression test checks the value against the live connector schema, not an old mock.

## Tune-up jobs

A tune-up brings an agent built to an older standards version up to the current one **without changing its
behaviour**: same rules, same outputs, same schedule, same connector scopes. Automatic fixes (pins, retries, logging,
model config, docstrings) are applied directly; changes that need judgement (missing tests, memory trimming, output
contracts) are proposed for builder review. A tune-up is a modify job, re-runs the full suite and produces a new
version that goes through the sandbox like any other.

# Delivery Quality Gates

**Owner:** Priya Raman, Delivery Excellence · **Last reviewed:** 2026-02-27 · **Status:** current

## Purpose

Seven gates, from qualification to closure, that every Wursta engagement passes. Gates are short, evidence-based
reviews — not committees. They protect clients from surprises and protect Wursta from commitments it cannot keep.

## Gate outcomes

- **Pass** — proceed.
- **Pass with conditions** — proceed, with named conditions, owners and due dates; the conditions are tracked in the
  risk register and re-checked at the next gate.
- **Fail** — do not proceed; fix and re-submit.

A gate may be waived only by the engagement director, in writing, with the reason recorded.

## The gates

### G0 — Qualify (before investing in a proposal)

- Evidence: client problem in their own words, sponsor identified, budget range, timing, competition, fit with
  Wursta's offerings.
- Approver: account executive and practice lead.

### G1 — Solution review (before the proposal is sent)

- Evidence: Pantheon rapid assessment or Hermes engagement report; target architecture with rejected alternatives;
  first-pass cost estimate; top five risks; assumptions list.
- Approver: a senior architect who did not write the solution.

### G2 — Commercial and SOW approval (before signature)

- Evidence: SOW from the current template; scope tied to the Must stories; fee built from the sized backlog;
  contingency justified by the risk register; client dependencies with dates; payment milestones; acceptance criteria;
  data-processing terms where personal data is involved.
- Approver: engagement director and Finance.
- Typical conditions: residency or data-processing wording to be confirmed by the client's compliance officer;
  open counts (users, mailboxes, data volumes) to be confirmed before the start date.

### G3 — Design sign-off (before build)

- Evidence: architecture decision records; security design reviewed; data model with validated DDL; backlog refined
  to Definition of Ready for the first two sprints; risk register with owners and mitigations for all high and
  critical risks.
- Approver: client technical lead and Wursta lead architect.

### G4 — Build complete and test readiness (before UAT)

- Evidence: all Must stories meet the Definition of Done; test environment stable; UAT plan with **named client
  testers** and dates; known defects listed with severity; performance and security tests done where relevant.
- Approver: engagement manager and client product owner.
- The most common reason for failing G4 is UAT testers not named or not available.

### G5 — Go-live readiness (before production cutover)

- Evidence: UAT signed off; no open S1 defects and an agreed plan for S2 defects; cutover plan and rollback plan
  (for Workspace migrations, the Workspace Migration Cutover Weekend Runbook; for agents, the Agent Deployment
  Checklist); support and hypercare model agreed; communications ready; go/no-go criteria agreed.
- Approver: client sponsor and engagement director.

### G6 — Closure and knowledge capture (within 20 business days of the end of hypercare)

- Evidence: acceptance certificate; closure report with estimate-versus-actual (effort, cost, schedule); lessons
  learned; reusable assets handed to the practice; knowledge-base documents updated and owned; risks and issues
  closed.
- Approver: engagement director and Delivery Excellence.

## How to run a gate

1. The engagement manager books 30–45 minutes and shares the evidence two business days before.
2. The reviewer checks evidence against the criteria above — not opinions.
3. The outcome, conditions, owners and dates are recorded in the engagement's gate log and in Jira (issue type Task,
   label `wursta`, component PMO).
4. Conditions not met by their due date are escalated like a high risk (Delivery Risk Management Standard).

## Agent support for gates

- Pantheon outputs are the evidence for G1 and feed G2 and G3.
- Prometheus produces the schedule and scored risk register used at G2 to G5.
- The `detect_meeting_sentiment_risk` skill can be run on steering transcripts before G4 and G5 to surface early
  warnings.
- Agents prepare evidence; people approve gates.

## Gate metrics

Percentage of engagements passing each gate first time, average number of conditions per gate, conditions overdue,
and correlation between gate outcomes and client satisfaction at closure. Delivery Excellence reports them quarterly.

# Delivery Quality Gates

**Owner:** Priya Raman, Head of PMO (Transformation Office) · **Last reviewed:** 2026-02-27 · **Status:** current

## Purpose

Seven gates, from idea intake to closure, that every programme in the company passes. Gates are short,
evidence-based reviews — not committees. They protect the business from surprises and protect the company from
funding commitments it cannot deliver.

## Gate outcomes

- **Pass** — proceed.
- **Pass with conditions** — proceed, with named conditions, owners and due dates; the conditions are tracked in the
  risk register and re-checked at the next gate.
- **Fail** — do not proceed; fix and re-submit.

A gate may be waived only by the Transformation Office director, in writing, with the reason recorded.

## The gates

### G0 — Idea intake and qualification (before investing in an assessment)

- Evidence: business problem in the business's own words, business sponsor identified, indicative budget range,
  timing, alternatives considered (including doing nothing), fit with the company's strategy and the enterprise
  architecture roadmap.
- Approver: business sponsor and Transformation Office director.

### G1 — Assessment and solution review (before the business case is drafted)

- Evidence: Pantheon rapid assessment or Hermes strategy report; target architecture with rejected alternatives;
  first-pass cost estimate; top five risks; assumptions list.
- Approver: an enterprise architect who did not write the solution.

### G2 — Business case and funding approval (before funding is released)

- Evidence: business case from the current template; scope tied to the Must stories; budget built from the sized
  backlog; contingency justified by the risk register; dependencies on other teams and vendors with dates; funding
  tranches tied to milestones; acceptance criteria; a data protection impact assessment where personal data is
  involved.
- Approver: business sponsor and Finance.
- Typical conditions: residency or data-protection wording to be confirmed by the compliance officer; open counts
  (users, mailboxes, data volumes) to be confirmed before the start date.

### G3 — Design sign-off (before build)

- Evidence: architecture decision records; security design reviewed; data model with validated DDL; backlog refined
  to Definition of Ready for the first two sprints; risk register with owners and mitigations for all high and
  critical risks.
- Approver: enterprise architect and the programme's lead architect.

### G4 — Build complete and test readiness (before UAT)

- Evidence: all Must stories meet the Definition of Done; test environment stable; UAT plan with **named business
  testers** and dates; known defects listed with severity; performance and security tests done where relevant.
- Approver: programme manager and product owner.
- The most common reason for failing G4 is UAT testers not named or not available.

### G5 — Go-live readiness (before production cutover)

- Evidence: UAT signed off; no open S1 defects and an agreed plan for S2 defects; cutover plan and rollback plan
  (for Workspace migrations, the Workspace Migration Cutover Weekend Runbook; for agents, the Agent Deployment
  Checklist); support and hypercare model agreed; communications ready; go/no-go criteria agreed.
- Approver: business sponsor and Transformation Office director.

### G6 — Closure and knowledge capture (within 20 business days of the end of hypercare)

- Evidence: business acceptance sign-off; closure report with estimate-versus-actual (effort, cost, schedule) and the
  benefits-tracking plan; lessons learned; reusable assets published to the shared asset library; knowledge-base
  documents updated and owned; risks and issues closed.
- Approver: Transformation Office director and the PMO.

## How to run a gate

1. The programme manager books 30–45 minutes and shares the evidence two business days before.
2. The reviewer checks evidence against the criteria above — not opinions.
3. The outcome, conditions, owners and dates are recorded in the programme's gate log and in Jira (issue type Task,
   label `transformation`, component PMO).
4. Conditions not met by their due date are escalated like a high risk (Delivery Risk Management Standard).

## Agent support for gates

- Pantheon outputs are the evidence for G1 and feed G2 and G3.
- Prometheus produces the schedule and scored risk register used at G2 to G5.
- The `detect_meeting_sentiment_risk` skill can be run on steering-committee transcripts before G4 and G5 to surface
  early warnings.
- Agents prepare evidence; people approve gates.

## Gate metrics

Percentage of programmes passing each gate first time, average number of conditions per gate, conditions overdue,
and correlation between gate outcomes and business-sponsor satisfaction at closure. The PMO reports them quarterly.

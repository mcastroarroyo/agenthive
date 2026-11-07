# VDR Standards: Design Review and Validation Report

**Owner:** Delivery Quality (Wursta) · **Templates:** VDR-DR v2.3, VDR-VR v1.6 · **Last reviewed:** 2026-08-30
Synthetic demo document.

## 1. What a VDR is
VDR — Validation and Design Review — is the package of delivery documents a client signs at the two quality gates
of every engagement: the **Design Review (DR)** before build or migration starts, and the **Validation Report (VR)**
before go-live. Signed VDRs are the evidence for milestone acceptance (clause CL-ACC-01) and for partner audits. The
VDR Validator agent checks drafts against these templates before they are sent.

## 2. Design Review (VDR-DR v2.3) — required sections
1. Document control — Version, Date, Author, Status, Client (all mandatory).
2. Revision history — the latest row must equal the version in document control.
3. Executive summary.
4. Scope and requirements traceability — every requirement maps to a design section.
5. Current state (source environment) with volumes.
6. Target design (identity, organisation, data, integrations, diagrams).
7. Security and compliance — authentication, data protection, retention and holds, DLP, external sharing.
8. Migration / implementation approach.
9. Risks, assumptions and dependencies — each risk with a mitigation and an owner.
10. Testing and validation approach — how each requirement will be proven, with tolerances.
11. Operations and support handover — who runs it after go-live, runbooks, hypercare.
12. Sign-off.

**Sign-off roles:** Wursta Delivery Lead, Wursta Solutions Architect, Client Project Sponsor, Client IT Owner. Each row
needs name, date and decision (Approved / Approved with comments / Rejected).

## 3. Validation Report (VDR-VR v1.6) — required sections
1. Document control. 2. Revision history. 3. Summary of results (pass rate, open defects, recommendation).
4. Test scope. 5. Test environment and data. 6. Test cases and results (table: id, test case, result, defect).
7. Defects (id, severity, description, status). 8. Deviations and waivers — every accepted deviation with the
client approver. 9. Data validation evidence (reconciliations, counts, checksums). 10. Recommendation (go / no-go).
11. Sign-off.

**Sign-off roles:** Wursta QA Lead, Wursta Delivery Lead, Client Business Owner.

## 4. Blocking rules (sign-off is refused)
- A required section is missing.
- Document-control version differs from the last revision-history entry.
- A sign-off row is incomplete or a required role is missing.
- The same figure is stated with different values (users, mailboxes, test cases).
- A failed test has no defect id.
- The stated pass rate differs from the pass rate computed from the test table.
- The recommendation is GO while a Severity 1 defect is open — unless a signed waiver is listed under deviations.

## 5. Advisory rules
- Placeholders (TBD, TODO, "[insert diagram]") — must be resolved before final, but a draft can be reviewed.
- Requirements without a design section, risks without owners, tolerances not stated.
- Diagrams referenced but not embedded.

## 6. Severity definitions for defects
- Sev1: data loss or corruption, security exposure, or a business process cannot run. Blocks go-live.
- Sev2: major function impaired, workaround exists. Go-live needs a dated fix plan.
- Sev3: minor function impaired. Sev4: cosmetic.

## 7. Scoring used by the validator
Start at 100; minus 10 per missing section, 5 per missing control field, 8 per blocking issue and 3 per advisory
issue. "Ready for sign-off" needs a score of 85 or more with no missing section and no blocking issue.

## 8. Tips for authors
- Write the testing approach while writing the design — the validator will check that it exists.
- Keep one source for numbers (the pre-flight inventory or the test table) and reference it.
- Ask the sponsor to sign within five business days; chase through the weekly status report.

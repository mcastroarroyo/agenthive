# SOW Standards and Clause Library

**Owner:** Delivery Excellence (Wursta) · **Version:** 4.1 · **Last reviewed:** 2026-10-01 · **Status:** current
Synthetic demo document. Companion to the SOW Legal Playbook (clause risk levels) and the Pricing, Estimation and
Approval Policy.

## 1. Purpose
Every Statement of Work (SOW) Wursta issues must be readable by a non-technical sponsor, priced from the official
rate card and estimation model, and free of open-ended commitments. The SOW Builder agent drafts SOWs to this
standard and runs the automated SOW quality check before a human reviewer sees the draft.

## 2. Required sections and order
Use markdown headings in this order. A SOW missing any of sections 2-11 fails the quality check.
1. Executive summary — the client problem, the outcome and the price in three to five sentences.
2. Scope — objectives and what Wursta will do, in measurable terms.
3. Deliverables — a table numbered D1, D2, ... with description and quantity.
4. Acceptance criteria — one measurable criterion per deliverable, referencing its D-id.
5. Assumptions — standard assumptions (clause CL-ASM-01) plus engagement-specific ones.
6. Out of scope — the standard exclusions (CL-OOS-01) plus everything the client explicitly excluded.
7. Client responsibilities — CL-CLR-01 plus named dependencies (access, DNS, approvals).
8. Milestones and timeline — phases with dates from the critical-path schedule.
9. Pricing and payment — price table and the payment schedule as a table with a percentage column.
10. Change control — CL-CHG-01, verbatim.
11. Governance — CL-GOV-01 with named key people.
12. Open questions — anything that must be answered before signature.
13. Signatures.

## 3. Writing acceptance criteria
- One criterion per deliverable, testable by the client without Wursta's help.
- Use numbers: "99.9% of mail items migrated per wave, with every skipped item listed in the validation report";
  "12 live sessions delivered with attendance lists"; "agent answers 50 test questions with at least 90% rated
  correct by the client's reviewer".
- Never "to the client's satisfaction" (red clause LR-02 in the SOW Legal Playbook).
- Acceptance runs through clause CL-ACC-01: five business days to review, deemed accepted after ten business days
  without a written non-conformity.

## 4. Terms to avoid
The quality check flags these in English, Spanish and Portuguese and deducts points for each:
"etc.", "as needed", "as required", "best effort", "unlimited", "any and all", "and so on", "ongoing support",
"seamless", "if time permits", "where possible", "all data"; Spanish "según sea necesario", "ilimitado", "mejor
esfuerzo", "entre otros"; Portuguese "conforme necessário", "ilimitado", "melhor esforço", "entre outros".
Replace each with a quantity, a duration or a list. Placeholders such as TBD, TBC, TODO, XXX or "[insert ...]"
block the SOW from review.

## 5. Payment schedule rules
- Fixed fee: 15% mobilisation on signature, 75% split across milestones on milestone acceptance, 10% holdback
  released ten business days after final acceptance (clause CL-PAY-01). Rows must add up to exactly 100%.
- Time and materials: monthly in arrears from approved timesheets up to a not-to-exceed (NTE) amount; the client is
  notified at 80% burn (clause CL-PAY-02). T&M without a cap is an amber clause.
- Standard terms are net 30.

## 6. Clause library (v4.1)
| Id | Topic | Use |
|---|---|---|
| CL-ACC-01 | Acceptance procedure | Every SOW |
| CL-CHG-01 | Change control (impact assessment in 3 business days; work only after a signed change order) | Every SOW |
| CL-ASM-01 | Standard assumptions (remote, business hours, volumes +/-10%) | Every SOW |
| CL-OOS-01 | Standard exclusions (hardware, device re-imaging, licences, data clean-up, decommissioning, post-hypercare support) | Every SOW |
| CL-PAY-01 | Fees — fixed fee | Fixed-price SOWs |
| CL-PAY-02 | Fees — time and materials | T&M SOWs |
| CL-CLR-01 | Client responsibilities | Every SOW |
| CL-GOV-01 | Governance (weekly status, fortnightly steering committee, RAID log, 2-day escalation) | Every SOW |
| CL-WAR-01 | 30-day warranty, re-performance as sole remedy | Every SOW |
| CL-DPA-01 | Data protection under the MSA; migration logs deleted 90 days after close | Every SOW handling personal data |
| CL-SUB-01 | Delivery model including the LATAM nearshore centre | When nearshore roles are priced |

Clause text is approved in English, Spanish and Portuguese. Do not edit wording without Legal review; country
clauses for Latin America are listed in the LATAM SOW Guide.

## 7. Review workflow
1. SOW Builder drafts and self-checks (target quality score of 80 or more, verdict "ready for review").
2. Delivery lead reviews scope and estimate; the approver required by the pricing policy signs off price and margin.
3. Legal reviews only when a clause deviates from the library or the SOW Legal Playbook grade is below A/B.
4. The engagement lead sends the SOW with the open questions highlighted.

## 8. Common review findings (FY26)
- Deliverables listed in the scope text but missing from the deliverables table (32% of returned drafts).
- Hypercare described as "support as needed" instead of a number of weeks.
- Payment schedules adding up to 90% because the holdback was forgotten.
- Training quoted as "end-user training" without a number of sessions.

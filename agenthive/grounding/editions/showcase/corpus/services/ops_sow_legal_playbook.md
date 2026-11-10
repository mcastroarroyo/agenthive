# SOW Legal Playbook (clause risk levels)

**Owner:** Legal & Commercial team · **Last reviewed:** 2026-10-14 · **Status:** current
Synthetic demo document — guidance for internal reviewers, not legal advice.

## 1. Risk levels
- **Red — do not sign.** The clause creates unlimited or disproportionate exposure. Any red clause requires Legal
  approval before the SOW leaves Sablewood.
- **Amber — negotiate.** Ambiguous or unfavourable language that is common in drafts. The Delivery Director may accept
  an amber clause with a written reason.
- **Green — standard.** Matches our preferred language.

**Grades:** A = no red and at most 2 amber · B = no red, 3+ amber · C = 1-2 red · D = 3-4 red · F = 5 or more red.
Only A and B SOWs may be sent to a client. Every SOW must also contain these sections: acceptance criteria, change
control, out of scope, assumptions, limitation of liability (or reference to the MSA) and client responsibilities.

## 2. Clause guide
### Scope
- *"including but not limited to"* (LR-04, amber) — open-ended scope. **Preferred:** an exhaustive list; anything else
  is out of scope unless added by change request.
- *"as needed", "ongoing support"* (LR-05, amber) — unbounded service. **Preferred:** hypercare of 4 weeks after
  go-live, up to 40 hours, business hours; ongoing support under a managed-services order.
- *"etc."* in deliverables (LR-06, amber) — list every deliverable with its acceptance criteria.

### Acceptance and revisions
- *"to the Client's sole satisfaction"* (LR-02, red) — subjective; acceptance can be withheld forever. **Preferred:**
  deliverables are accepted when they materially conform to the acceptance criteria; deemed accepted after 10
  business days without a written notice of material non-conformity.
- *"unlimited revisions"* (LR-01, red). **Preferred:** up to two rounds of revisions per deliverable; further changes
  through change control. **Fallback:** three rounds for UI deliverables.

### Warranties and performance
- *"guarantees"* of accuracy, savings or outcomes (LR-03, red) — AI systems are probabilistic. **Preferred:** "Sablewood
  will design the service to target the agreed accuracy on the agreed evaluation set; results are measured, reported
  and improved." **Walk-away:** any financial remedy tied to model accuracy.
- *"best efforts"* (LR-18, amber) — use "commercially reasonable efforts" (LR-17, green).

### Service levels
- Response commitments such as *"within 1 hour, 24x7"* (LR-14, amber) belong only in a managed-services order with
  severity definitions and support hours — never in a project SOW.

### Liability and remedies
- *"liability shall not be limited"* (LR-08, red). **Preferred:** liability as limited in the MSA (fees paid under the
  SOW in the prior 12 months). **Walk-away:** uncapped liability.
- *Penalties / liquidated damages* (LR-07, red). **Preferred:** none. **Fallback:** service credits capped at 5% of the
  phase fee, excused by client-caused delays. Public-sector RFPs with capped LDs (at most 10%) need Delivery Director
  approval.

### Intellectual property
- Assignment of *pre-existing materials, tools and accelerators* (LR-09, red). **Preferred:** the client owns custom
  deliverables on payment; Sablewood keeps pre-existing materials and grants a perpetual licence to use them with the
  deliverables.

### Fees and payment
- *Time and materials* without a cap (LR-10, amber). **Preferred:** T&M with an estimate and a not-to-exceed amount;
  work beyond it needs written approval.
- Payment terms longer than 45 days (LR-11, amber). **Preferred:** net 30.

### Dependencies and client responsibilities
- *"Sablewood shall be responsible for obtaining data from third parties"* (LR-12, amber) — we cannot control third
  parties. **Preferred:** the client procures third-party access and cooperation; third-party delays are client
  dependencies.
- Obligations *"when possible"*, *"promptly"* (LR-13, amber). **Preferred:** within 5 business days of request; delays
  extend the timeline day for day.
- Vague data-quality assumptions (LR-19, amber). **Preferred:** issues found in profiling are logged; remediation beyond
  16 hours is handled by change request.

### Change control and termination
- Changes *"agreed informally by email"* (LR-16, amber). **Preferred:** a written change request signed by both
  parties stating scope, fees and timeline impact.
- Termination for convenience *without payment for work performed* (LR-15, red). **Preferred:** 30 days' notice; the
  client pays for work performed and non-cancellable costs.

## 3. Review workflow
1. Thoth pre-scans the draft clause by clause and proposes a grade and redlines.
2. The engagement lead fixes amber items; Legal reviews every red item.
3. The final SOW is re-scanned; only grades A or B are released.
4. Redlines are sent to the client as tracked changes with a short rationale per clause.

## 4. Writing redlines
Show **original → proposed** text, one sentence of rationale in client-friendly language, and the fallback position
we can accept. Never argue with the client in comments; offer the alternative.

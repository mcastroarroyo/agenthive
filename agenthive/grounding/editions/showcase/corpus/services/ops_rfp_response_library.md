# RFP Response Library & Bid Rules

**Owner:** Bid Office (Sales Operations) · **Last reviewed:** 2026-10-19 · **Status:** current
Synthetic demo document — case studies refer to fictional clients.

## 1. How we decide to bid
Every RFP gets a compliance matrix (requirement → evidence → gap) before anyone writes prose. Mercator produces the
first matrix; the bid lead confirms it.

| Signal | Rule |
|---|---|
| **Go** | Every mandatory requirement is met with direct evidence (a case study, past SOW or documented capability). |
| **Conditional go** | Every mandatory requirement has evidence, but one or more is partial and can be closed before the questions deadline (e.g. securing a second named reference, a partner letter). |
| **No-go** | Any mandatory requirement has no evidence and no credible mitigation — failing a mandatory requirement means disqualification. |

Also escalate to the Delivery Director before bidding when: liquidated damages exceed 10% of contract value or are
uncapped; payment terms exceed 45 days; the authority demands IP assignment of our pre-existing tools; or the
budget ceiling is below our estimate by more than 20%. Commercial terms go to Thoth for a clause-risk grade.

Desirable requirements are scored inside the technical section: aim for at least 60% of desirables met or partially
met with a clear plan.

## 2. Compliance matrix format
One row per requirement: **ID · M/D · requirement (short) · status (met / partial / gap) · evidence ids · response
summary · mitigation**. Partial and gap rows always carry a mitigation: a partner, a clarification question to the
buyer, an alternative approach, or a formal exception.

## 3. Standard answers (approved language)
- **Security certifications:** "Sablewood operates an information security programme aligned to ISO/IEC 27001 and SOC 2
  concepts; we provide our control mapping and complete security questionnaires." *Never* state or imply that we hold a
  certificate we do not hold. If the RFP requires a certificate issued to the bidder, mark the row partial and propose
  the questionnaire plus evidence of controls.
- **Support model:** Sablewood Care provides business-hours (8x5) support with a 4-hour severity-1 response. 24x7 coverage
  with a 1-hour severity-1 response is available only through an optional partner add-on and must be priced separately.
- **On-site support:** not part of our standard model. Offer remote floor-walking plus scheduled on-site days, or a
  local partner — never promise on-site response times we cannot staff.
- **Accessibility:** rider/citizen-facing interfaces are tested against WCAG 2.1 AA with an audit report.
- **Data residency:** our reference design pins storage, processing and model endpoints to US regions; the design
  record documents it.
- **Languages:** bilingual delivery in English and Spanish.
- **Enablement:** standard 6-week knowledge-transfer programme with labs and a certification path for client IT staff.

## 4. References
Only clients marked as **named references** can be offered as contactable references. Anonymised case studies can be
described ("a mid-size US city") but cannot be contacted without the client's written permission — request it through
the account executive at least 10 business days before the submission date.

## 5. Case study index
- **CS-009** — Regional transit agency moves 2,400 staff to Google Workspace in 9 weeks; floor-walkers at each depot;
  SSO and MFA (Lakeshore Metro Transit — named reference, 2025, public sector).
- **CS-011** — City 311 assistant on web and messaging, English and Spanish, human hand-off, WCAG 2.1 AA audit passed;
  61% of questions resolved without an agent (anonymised, 2025, public sector).
- **CS-021** — Logistics provider gets 15-minute on-time-performance analytics on BigQuery from 9 systems (anonymised).
- **CS-025** — Credit union warehouse on BigQuery with data classification and row-level security (Polaris Credit Union).
- **CS-014** — Regional insurer cuts claims triage time 42% with Gemini and human review (Calder & Finch Insurance).
- **CS-006** — Senior living operator rolls out Gemini Enterprise to 900 staff with micro-trainings (Solace Senior Living).

Past SOWs that back these: SOW-2025-031 (transit migration), SOW-2025-044 (311 assistant), SOW-2025-022 (logistics data
platform), SOW-2026-008 (claims triage), SOW-2026-012 (warehouse with row-level security).

## 6. Win themes we reuse
1. **One accountable partner** across collaboration, data and AI — integrated bids beat three separate vendors.
2. **Proof before promises** — live agent demos and measured outcomes from named references.
3. **Adoption, not just deployment** — floor-walkers, champions and micro-trainings.
4. **Guardrails by design** — PII redaction, Model Armor and human hand-off from day one.

## 7. Executive summary pattern (2 pages max)
Their goal in their words → our understanding of the constraints → the approach in three moves → proof (two case
studies with numbers) → why Sablewood → the first 90 days. Write it last, after the matrix is final.

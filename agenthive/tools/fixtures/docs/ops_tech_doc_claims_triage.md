# Internal Technical Write-up · Claims Triage Assistant (Calder & Finch Insurance, phase 1)

Classification: INTERNAL — engineering write-up for reuse. Case study reference: CS-014 (approved for external use as a
named reference). Author: Priya Nair, Solution Architect. Last updated: 2026-10-22.

## 1. Problem
Calder & Finch (fictional regional P&C insurer, ~1,100 employees) received ~150,000 first-notice-of-loss (FNOL)
submissions a year by email, web form and scanned letters. Claims handlers spent a median 26 minutes per claim reading
attachments, keying policy data and deciding which adjuster queue should own the claim. Backlogs peaked after storms,
when triage delays reached three days.

## 2. Solution (what we built)
- Intake: Gmail and web-form submissions land in a Cloud Storage bucket; Pub/Sub triggers a Cloud Run worker.
- Document understanding: Document AI form parser + OCR for scanned letters; Gemini on Vertex AI (Flash tier) for
  classification of claim type (water damage, auto glass, theft, liability, other) and extraction of policy number,
  loss date, loss location and reported damage.
- PII protection: Sensitive Data Protection de-identifies names, phone numbers and bank details before prompts; Model
  Armor screens prompts and responses for injection and leakage.
- Human in the loop: every suggestion is shown to an adjuster in the existing claims work queue with the evidence
  snippets; the adjuster accepts or overrides with a reason code.
- Analytics: suggestions, overrides and handling times are written to BigQuery; a Looker dashboard tracks accuracy by
  claim type.
- Region: all processing and storage pinned to a US region; no training on client data.

## 3. Results (pilot, 12 weeks, 4 offices)
- Median triage time: 26 → 15 minutes (−42%).
- Routing suggestions accepted by adjusters: 87%.
- Extraction field accuracy (policy number, loss date): 96% on the audited sample of 1,200 claims.
- Storm-week backlog cleared in 1 day instead of 3.
- Adjuster satisfaction (pilot survey): 4.4 / 5.

## 4. Architecture decisions
- ADR-07: Flash over larger models — accuracy difference on the audited sample was under 1 point and cost 6x lower.
- ADR-09: Human review is mandatory for liability claims, whatever the confidence.
- ADR-11: Prompts never include full documents with unredacted PII; only de-identified snippets.

## 5. Lessons learned
- Start with the two highest-volume claim types; long-tail types added later with little effort.
- Reason codes on overrides were the single best source of improvement ideas.
- Adjuster champions in each office mattered more than training sessions.

## 6. Commercials (INTERNAL ONLY — do not share)
- Fixed fee phase 1; delivery margin 31% vs 27% target. Rate card discount 8% agreed for phase 2.
- Internal note: the client asked for exclusivity in the region — declined.

## 7. Reusable assets
- Terraform module for the intake pipeline; prompt templates for FNOL classification; Looker accuracy dashboard;
  adjuster training micro-videos (3 × 6 minutes).

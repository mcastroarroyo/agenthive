# Corvina Clinical Research Office — Pre-screening SOP (CRO-SOP-09)

*Synthetic SOP for the Wursta Agent Hive demo. Corvina Health Network, the sponsors and the trials are fictional.
All patient records used in the demo are synthetic; no PHI is processed.*

**Owner:** Director, Clinical Research Office · **Version:** 3.0 · **Effective:** 2026-03-01

## 1. Purpose

Pre-screening identifies patients who may be candidates for a recruiting trial **before** any trial-specific
procedure or contact. It reduces screen failures after consent and helps investigators prioritise. Pre-screening
never determines eligibility: the principal investigator (PI) confirms eligibility after informed consent and
protocol screening procedures.

## 2. Privacy and data minimisation

- Use only the minimum data needed to assess the criteria. Refer to patients by research id, never by name.
- Pre-screening logs are stored in the research system with access limited to the study team.
- **No patient contact** about a trial until the PI has reviewed the pre-screen and the treating physician agrees.
- AI tools may abstract records and evaluate criteria; a qualified coordinator verifies every result against the
  source record before it is used.

## 3. Criterion status definitions

| Status | Meaning |
|---|---|
| Pass | The record contains dated evidence that the criterion is met (or the exclusion does not apply) |
| Fail | The record contains evidence that the criterion is not met (or the exclusion applies) |
| Missing data | The required result is absent, or present but outside the protocol window |
| Needs review | Evidence is ambiguous or sources disagree (e.g. referral note vs record) |

## 4. Overall outcomes

- **Likely eligible** — every criterion passes. Route to the PI for review.
- **Pending data** — no failures, at least one missing item. List each missing item, who orders it and by when.
- **Not yet eligible** — the only failures are time-limited (washout periods). State the earliest eligible date and
  check that labs and imaging will still be inside their windows on that date.
- **Likely ineligible** — at least one hard failure. Record the failing criteria; do not contact the patient.

## 5. Windows and washouts (defaults unless the protocol says otherwise)

- Safety laboratory tests: within **14 days** before first dose (oncology); within 30 days for most cardiovascular
  and metabolic studies.
- Disease imaging for measurable disease (RECIST 1.1, at least one lesion of 10 mm or more): within **28 days**.
- ECG (QTcF): within 28 days.
- Systemic anticancer therapy washout: **21 days** since the last dose; radiotherapy: 14 days.
- Strong CYP3A4 inducers: stop at least 14 days before first dose (if the protocol prohibits them).
- Pregnancy test for participants of childbearing potential: within 7 days before first dose.

When a window will expire before the planned screening visit, flag it ("imaging window ends 2026-11-17") so the
coordinator can schedule repeat tests in the right order.

## 6. Thresholds expressed relative to normal limits

Liver tests are often expressed as multiples of the upper limit of normal (ULN). Use the laboratory's ULN printed
with the result. Some protocols allow higher limits in specific conditions (for example AST/ALT up to 5 x ULN with
liver metastases, or a higher NT-proBNP threshold in atrial fibrillation) — apply the alternate threshold only when
the condition is documented in the record.

## 7. Recruiting trials (Q4 2026)

| Trial | Short name | Population | Site | Slots |
|---|---|---|---|---|
| CVH-ONC-2026-014 | HERON-2 | Previously treated KRAS G12C-mutated advanced NSCLC (HRX-417, Phase II) | Cancer Institute, Corvina General | 6 |
| CVH-CARD-2026-007 | ZEPHYR-HF | Symptomatic HFrEF on stable guideline-directed therapy (ZPH-12, Phase III) | Corvina Heart Clinic | 11 |
| CVH-ENDO-2026-022 | KIDNEY-SHIELD-2 | Type 2 diabetes with CKD and albuminuria (KSH-209, Phase II) | Corvina Diabetes Center | 3 |

## 8. Coordinator note

The pre-screen note goes to the study coordinator with the PI in copy. It contains: research id, trial, outcome,
the criteria that failed or are missing, the actions to complete pre-screening with owners and dates, the earliest
eligible date if relevant, and a reminder that the patient has not been contacted. Keep it to 5-8 sentences.

## 9. Logging

Every pre-screen — including ineligible outcomes — is logged with the date, the trial, the outcome and the
coordinator's initials. Logs support enrolment reporting and diversity monitoring.

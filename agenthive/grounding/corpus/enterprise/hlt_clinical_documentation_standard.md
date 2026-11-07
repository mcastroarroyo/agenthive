# Corvina Health Network — Clinical Documentation Standard (CDS-3) and AI Scribe Policy

*Synthetic standard for the Wursta Agent Hive demo. Corvina Health Network is fictional; coding guidance is
illustrative and must be validated by certified coders against current code sets and payer rules.*

**Owner:** Chief Medical Information Officer · **Version:** 3.2 · **Effective:** 2026-04-01

## 1. Principles

- Document what happened, in the patient's and clinician's words, at the time of care.
- An AI scribe drafts; the clinician reviews, edits and signs. Unsigned AI drafts are not part of the legal record.
- Never add findings, vitals, doses, allergies or history that were not stated or measured. When a required element
  was not discussed, write **"[not documented]"** so the clinician can complete it.
- Use the patient's research or synthetic id in demos; never real identifiers.

## 2. Required elements of an outpatient SOAP note

| Section | Required elements (critical in bold) |
|---|---|
| Subjective | **Chief complaint**, **history of present illness** (at least 4 elements: location, quality, severity, duration, timing, context, modifying factors, associated symptoms), review of systems, **medication list and reconciliation**, **allergies** |
| Objective | **Vital signs**, **physical examination**, relevant data reviewed (labs, imaging) |
| Assessment | **Numbered problems with status** (improving, stable, worsening) and diagnoses as specific as the documentation supports |
| Plan | Plan per problem, **follow-up interval**, patient education with teach-back, medical decision making or total time |

**Telehealth visits** also require: the patient's consent to a telehealth visit, the modality (video or audio-only)
and the patient's location at the time of the visit.

**Completeness score:** the documentation check weights each element; a note is complete at 85 or above with no
critical element missing. Elements explicitly marked "[not documented]" are listed for the clinician to confirm
before signature.

## 3. Medical decision making (MDM) — illustrative levels

| MDM level | Typical picture | Established office visit |
|---|---|---|
| Straightforward | One self-limited problem | 99212 |
| Low | Two minor problems, or one stable chronic illness | 99213 |
| Moderate | One chronic illness with exacerbation or progression, or two stable chronic illnesses; prescription drug management | 99214 |
| High | Chronic illness with severe exacerbation, or a threat to bodily function; drug therapy requiring intensive monitoring | 99215 |

New-patient visits map to 99202-99205 at the same MDM levels. Post-discharge visits within 7 days (high MDM) or 14
days (moderate MDM) may qualify for transitional care management (99496 / 99495) when the interactive contact within
2 business days of discharge was documented; report once per 30 days.

## 4. Diagnosis specificity (ICD-10-CM, illustrative)

- **Heart failure:** document type (systolic/HFrEF, diastolic/HFpEF) and acuity (acute, chronic, acute on chronic).
  "Heart failure" alone codes to an unspecified code and triggers a query.
- **Hypertension with heart failure** is coded as hypertensive heart disease with heart failure (I11.0) plus the
  heart-failure type code; with chronic kidney disease as well, consider I13.0.
- **Diabetes with CKD:** the link is presumed (E11.22 plus the N18 stage code) unless the clinician documents another
  cause.
- **COPD:** specify exacerbation (J44.1) versus stable disease (J44.9).
- **Medication non-adherence:** document the reason — financial hardship (Z91.120 for intentional underdosing due to
  financial hardship) versus other reasons (Z91.148).
- Symptom codes (e.g. oedema R60.0) are not reported separately when they are integral to a confirmed diagnosis.

## 5. Clinician queries

When documentation is ambiguous, the coder or AI assistant raises a **non-leading query**: state the clinical
indicators found in the note and ask the clinician to clarify, offering clinically reasonable options including
"other" and "unable to determine". Example: "The note documents HFrEF with weight gain of 2.2 kg and pitting
oedema, treated with increased diuretic. Please clarify the acuity of heart failure: acute, chronic, acute on
chronic, other, unable to determine."

## 6. AI scribe policy

1. Patients are told an AI scribe is in use and may opt out.
2. Audio is deleted after the note is signed; transcripts are retained only as the signed note.
3. Drafts flag every "[not documented]" item and every coding query on top of the note.
4. Quality review samples 2% of AI-drafted notes monthly for fidelity errors (anything in the note not supported by
   the encounter). Target: zero fidelity errors in signed notes.

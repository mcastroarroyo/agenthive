# Corvina Health Network — Transitional Care Protocol (TCP-04)

*Synthetic protocol for the Wursta Agent Hive demo. Corvina Health Network is fictional; thresholds are
illustrative and are not clinical guidance. Every patient in the demo is synthetic.*

**Owner:** Director of Care Transitions · **Version:** 4.1 · **Applies to:** the 30 days after hospital discharge

## 1. Goals

Prevent avoidable readmissions and harm after discharge by contacting every enrolled patient early, catching red
flags fast, and making sure medicines are taken as prescribed. AI assistants support the nurse team; a licensed
clinician confirms every disposition and owns every clinical decision.

## 2. Contact cadence

- First contact within 2 business days of discharge (phone or app), then at day 7, day 14 and day 30.
- Daily automated check-ins for heart failure (weights), diabetes on new insulin (glucose) and COPD (symptoms,
  SpO2) during the first 14 days.
- Every contact uses **teach-back**: the patient repeats the plan in their own words.
- Messages are sent in the patient's preferred language and channel, in plain words, without diagnoses.

## 3. Triage dispositions and response times

| Disposition | Response | Examples |
|---|---|---|
| Emergency | Advise the patient to call emergency services now; notify the on-call physician immediately | Chest pain or pressure, severe breathlessness or breathless at rest, fainting, new confusion, stroke signs, coughing or vomiting blood, heavy bleeding, SpO2 below 88% (below 85% in COPD), systolic BP below 90, heart rate above 130 or below 40 |
| Urgent | Transitional-care nurse calls back within 1 hour; consider a same-day clinic slot | Condition-specific red flags (below), temperature 38.3 °C or more after surgery, systolic BP 180 or more, heart rate above 110, glucose below 70 or above 300 mg/dL |
| Same day | Nurse or clinic follow-up within 8 hours | Pain 7/10 or more, dizziness, opioid-related constipation, new ankle swelling in COPD |
| Routine | Reinforce the plan; next scheduled contact | No red flags |

The most severe rule that fires sets the disposition. Staff may escalate a disposition on clinical judgement but
never downgrade an automated disposition without a clinician's documented review.

## 4. Condition-specific red flags

**Heart failure (HF program)**
- Weight gain of 1.0 kg or more in 24 hours, or 2.0 kg or more above the discharge weight within the first week.
- New or worse leg/ankle swelling; needing more pillows or waking breathless; worse breathlessness on exertion.
- Missed diuretic doses are a common cause of fluid gain — check adherence on every urgent HF call.

**After hip or knee replacement**
- Calf pain, swelling, warmth or redness (possible deep-vein thrombosis) — same-day assessment.
- Wound drainage, pus, spreading redness or wound opening — urgent.
- Sudden inability to bear weight, a "pop", or a shortened or rotated leg (possible dislocation) — emergency.
- Bleeding gums, blood in urine or black stools while on an anticoagulant — urgent.

**COPD**
- Rescue inhaler needed more often than every 4 hours, or worse breathlessness — urgent.
- Sputum turning green or yellow, or increasing in volume — urgent.
- SpO2 target 88-92%; below 88% is urgent and below 85% is an emergency.

**Diabetes on new insulin**
- Glucose below 70 mg/dL: treat immediately with the rule of 15 (15 g fast-acting sugar, recheck in 15 minutes)
  and arrange a nurse callback within 1 hour. Below 54 mg/dL with confusion is an emergency.
- Two or more readings below 70 mg/dL since discharge — the prescriber must review the insulin dose the same day.
- Glucose above 300 mg/dL, vomiting, ketones or fruity breath — urgent.

## 5. Medication adherence

- Adherence is measured from pharmacy refill data (proportion of days covered, PDC) and, where available, connected
  pill organisers or insulin pen loggers.
- **Non-adherent:** PDC below 0.80, or fewer than 80% of scheduled doses taken in the last 5 days.
- A critical medication (diuretic, anticoagulant, insulin, maintenance inhaler, anti-anginal) that is never filled
  or repeatedly missed triggers a pharmacist review the same day.
- Ask about the barrier without judgement: cost, side effects, timing, confusion, beliefs. Common fixes: copay
  assistance or a formulary alternative, moving a diuretic dose earlier in the day, blister packs, simplified
  schedules.

## 6. Tasks and handover

Use SBAR for every task: **S**ituation, **B**ackground, **A**ssessment, **R**ecommendation. Task types: nurse
callback, clinic visit, pharmacist review, escalation to the on-call physician, patient message. All tasks record
the disposition, the rules that fired and who was notified.

## 7. Safety-netting script

Close every contact with: "If you get chest pain, severe breathlessness, fainting, confusion or heavy bleeding, call
emergency services straight away. For anything else that worries you, call the nurse line any time."

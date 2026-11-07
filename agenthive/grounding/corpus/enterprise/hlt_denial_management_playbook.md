# Corvina Patient Financial Services — Denial Management Playbook

*Synthetic playbook for the Wursta Agent Hive demo. Corvina Health Network and the payers named here are fictional.
Payer rules are illustrative; denial codes follow the public CARC-style convention.*

**Owner:** Director, Revenue Integrity · **Reviewed:** 2026-10-20

## 1. Principles

1. Fix the claim, not just the denial: every denial is worked to the right route — corrected claim, appeal,
   verification or write-off review — and its root cause is fed back upstream.
2. Work the queue by **expected recovery** (likelihood x denied amount), adjusted for deadline urgency.
3. Never invent clinical facts or documents. Appeals cite only records on file and the payer's own policy.
4. Patients are not billed for contractual (CO) denials.

## 2. Denial codes and the right route

| Code | Meaning (paraphrased) | Category | Usual route |
|---|---|---|---|
| CO-197 | Precertification/authorization absent | Authorization | Appeal with the authorization, or with the emergency exemption |
| CO-50 | Not deemed medically necessary | Medical necessity | Appeal with clinical documentation; peer-to-peer first when evidence is moderate |
| CO-16 | Claim lacks information / billing error | Missing information | Corrected claim (not an appeal) |
| CO-29 | Time limit for filing expired | Timely filing | Appeal only with proof of timely original submission |
| CO-11 | Diagnosis inconsistent with procedure | Coding | Corrected claim with the right diagnosis |
| CO-4 | Modifier inconsistent or missing | Coding | Corrected claim with the modifier |
| CO-97 | Bundled into another service | Bundling | Corrected claim with modifier 25/59 when documentation supports a separate service |
| CO-18 | Exact duplicate | Duplicate | Verify the original was paid and close |

## 3. Appeal likelihood model (illustrative)

Likelihood = average of the category base rate and the payer's historical overturn rate for that category, then
adjusted for evidence:

- authorization number on file for the date of service: +35 points;
- emergency service exempt from prior authorization under the payer's policy: +30 points;
- proof of timely original submission (clearinghouse acceptance report): +45 points;
- documentation strength: strong +10, moderate 0, weak −15 points.

Category base rates: authorization 45%, medical necessity 35%, missing information 85%, timely filing 10%, coding
70%, bundling 55%, duplicate 3%. Likelihood is capped at 95%; a closed appeal window means 0%.

**Routing thresholds:** 40% or more → Level 1 appeal; 25-40% → appeal only after a peer-to-peer review or added
documentation; below 25% → write-off review unless new documentation is found.

## 4. Payer rules (2026)

| Payer | Appeal window | Corrected-claim window | Levels | Notes |
|---|---|---|---|---|
| Silverline Health Plan | 180 days from denial | 90 days | Level 1 reconsideration (30-day decision), Level 2, external review | Portal Appeals module |
| Pinecrest Mutual | 90 days | 60 days | First-level (45-day decision), second-level | Peer-to-peer available within 14 days of denial |
| Bluewater Senior Advantage | 65 days | 60 days | Reconsideration, independent review entity | Portal |
| State Medical Assistance Program | 120 days | 365 days | Administrative reconsideration, fair hearing | Timely filing 365 days from service |

**Payer bulletins that changed denial patterns in 2026**

- **Silverline bulletin SL-2026-14 (effective 2026-07-01):** prior authorization required for outpatient advanced
  imaging (MRI, CT, PET). Emergency-department services are exempt. Since July, CO-197 denials for advanced imaging
  at Silverline rose sharply — in most cases the authorization *had* been obtained but the number was not
  transmitted on the claim because registration did not capture it. Root-cause fix: make the authorization number a
  hard stop in imaging registration and add a claim-scrubber edit for Silverline imaging CPT codes.
- **Bluewater (effective 2026-08-15):** referring/ordering provider NPI required on all diagnostic claims. A
  clearinghouse mapping change dropped the NPI from loop 2310A, creating CO-16 denials for imaging and laboratory
  claims. Fix: correct the mapping and resubmit corrected claims within 60 days.

## 5. Appeal letter — required elements

1. Provider and payer appeal unit; date; appeal level.
2. Claim number, member reference, date of service, denial code and meaning, amount in dispute.
3. The specific action requested (reprocess and pay, reconsider medical necessity).
4. Two to five numbered, factual arguments citing documents and the payer's policy.
5. Enclosure list matching the arguments.
6. Signature block completed by an authorised reviewer. AI-drafted letters are always reviewed and signed by a
   person before submission.

## 6. Work-queue priorities

1. Deadlines within 30 days.
2. Highest expected recovery.
3. Patterns: when three or more denials share a payer, code and service line in a month, open a root-cause ticket
   with registration, coding or the clearinghouse owner.

## 7. Metrics

Overturn rate, net recovery, days in A/R for denied claims, preventable-denial rate and cost to collect per
claim are reported monthly to the Revenue Cycle Committee.

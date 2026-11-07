# Project brief — Alderbrook Home Services: Kitewing FieldOps rollout

Synthetic demo document. All companies and people are fictional.

**Customer:** Alderbrook Home Services (3 branches, 140 technicians, 22 office and dispatch staff)
**Contract (assumed for planning):** Growth plan + Route Optimizer + Kitewing Assist, Standard implementation + 1 data-migration source. Order form expected by **2026-12-04** — the customer agreed to sign early to protect the spring peak.
**Project start (kickoff):** Monday **2026-12-07**
**Hard deadline:** all branches live before **2027-03-01** (spring peak starts in March)
**Sponsors:** Renata Vos (COO, Alderbrook) · Hannah Brooks (Head of Customer Success, Kitewing)

## Objective
Replace DispatchPro 7 and the maintenance-agreement spreadsheets with Kitewing FieldOps across all three branches before the spring peak, without losing a day of dispatch.

## Success criteria
- All 140 technicians and 22 office staff live on FieldOps before 2027-03-01; DispatchPro 7 switched to read-only.
- 1,800 maintenance agreements billing automatically from the first billing run after go-live.
- Invoices sent the same day as job completion for 90% of jobs within 30 days of go-live.
- Overtime below 9% of technician hours in May-June 2027; first-time fix at 80% or more by June 2027.

## In scope
- Discovery workshops per branch and solution design (dispatch board, job types, service zones, price book).
- Configuration of FieldOps for 3 branches, including inspection form templates for the electrical division.
- Data migration from DispatchPro 7: about 38,000 customers, 52,000 equipment records and the last 3 years of job history (older history archived as files). About 8% duplicate customers expected.
- Maintenance agreements: load 1,800 agreements and set up recurring billing.
- Accounting connector set-up and reconciliation test.
- Route Optimizer and Kitewing Assist (Spanish-language answers — beta — for about 30% of technicians).
- Training: train-the-trainer for 9 technician champions (3 per branch) and dispatcher training for 22 office staff; technician sessions run in 2-hour slots at branch morning meetings.
- Phased go-live: Brookhaven Falls HQ (about 60 technicians) first, then Eastfield and Riverside together.
- Two weeks of hypercare after the last branch goes live.

## Out of scope
- Payroll integration (phase 2), custom reports beyond the 10 standard dashboards, customer-portal branding (phase 2).

## Constraints
- Holiday freeze: no go-live or cutover from 2026-12-21 to 2027-01-01; Alderbrook IT change freeze 2026-12-18 to 2027-01-04.
- Dispatchers are available for workshops and testing only Tuesday-Thursday afternoons.
- DispatchPro 7 exports are produced by the legacy vendor and take 5 business days per run; at least two dry runs plus the final export are needed.
- The security questionnaire and DPA must be approved by Joy Park (IT Manager) before production data is loaded.

## Team
- **Kitewing:** Ines Duarte (lead Implementation Consultant), Grace Obi (Implementation Consultant, joins 2026-11-23), Femi Adeyemi (data-migration support), Rosa Delgado (solution-design handover from presales), Kwame Mensah (CSM from go-live), Sofia Petrov (Assist Spanish beta).
- **Alderbrook:** Carlos Méndez (customer project lead), Joy Park (IT), Ahmed Saleh (electrical division), three branch managers, Frank Doyle (CFO — billing and accounting sign-off).

## Budget
- Fees: Standard implementation $12,000 + data migration $3,500 (fixed).
- Kitewing internal effort budget: 520 hours.

## Known risks (from presales)
- Data quality in DispatchPro 7 (duplicates, missing equipment serial numbers).
- Saturday dispatch shifts during cutover weekends.
- Spanish-language answers are in beta until 2026-12-18.
- Accounting sync must be proven before the first agreement billing run.

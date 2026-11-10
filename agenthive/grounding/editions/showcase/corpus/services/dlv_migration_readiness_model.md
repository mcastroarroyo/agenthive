# Migration Readiness Model

**Owner:** Workspace practice (Sablewood) · **Version:** 1.5 · **Last reviewed:** 2026-09-22 · **Status:** current
Synthetic demo document.

## 1. Purpose
Most failed migrations were never ready to start: no DNS access, no retention decision, nobody owning change. The
readiness model turns a 16-question questionnaire into a weighted score, a list of blockers and a go / conditional
go / no-go decision before a migration SOW is signed or a kickoff date is promised.

## 2. Domains and weights
| Domain | Weight | What "ready" looks like |
|---|---|---|
| Sponsorship & governance | 15 | Named executive sponsor; steering committee and go/no-go decision-maker agreed |
| Identity & directory | 15 | Directory clean (no stale or duplicate accounts; sign-in names match email); SSO approach decided |
| Network, DNS & mail flow | 15 | Admin access to the DNS zone and an approved MX change window; bandwidth for bulk copy |
| Data, retention & compliance | 15 | Retention and legal-hold requirements documented with an owner; data inventory available |
| Applications & integrations | 10 | Every application that sends mail inventoried; Outlook/Exchange add-ins have an answer |
| Devices & clients | 10 | Mobile policy and desktop approach decided |
| People & change | 10 | Client change owner and champions named; training windows and blackouts known |
| Support & operations | 10 | Help desk briefed for hypercare; licences procured |

## 3. Scoring
- Answers score yes = 1, partial = 0.5, unknown = 0.25, no = 0. A domain's score is the average of its questions x 100.
- The overall score is the weight-averaged domain score.
- Six questions are **critical**: executive sponsor, directory clean, DNS access and change window, retention and
  legal hold, mail-sending applications, change owner and champions.

## 4. Decision rules
- **NO-GO** if any critical question is answered "no", or the overall score is below 60.
- **CONDITIONAL GO** if any critical question is "partial" or "unknown", or the score is below 75. Kickoff can be
  scheduled, but the SOW lists the remediation as client responsibilities with dates, and the pilot wave does not
  start until they are closed.
- **GO** otherwise.

## 5. Typical remediation and durations
| Blocker | Remediation | Typical duration |
|---|---|---|
| Stale or duplicate accounts | Disable and clean accounts; fix mismatched sign-in names | 10 business days |
| No DNS access | Name the DNS owner, get a signed change window, test with a TXT record | 5-15 business days (agency-managed DNS takes longest) |
| Retention / hold undefined | Compliance owner approves a Vault retention and hold design | 15-20 business days |
| Unknown mail-sending apps | Log SMTP connections for 14 days, then build the relay plan | 15 business days |
| No change owner | Sponsor appoints one; name 1 champion per 50 users | 5 business days |
| Licences not procured | Purchase and set up billing | 10 business days |

Schedule remediation with the critical-path tool: tasks that can run in parallel (directory clean-up and SMTP
discovery) usually do. Always end with a re-assessment task (2 days).

## 6. Using the result
- Put the verdict and blockers in the proposal; never hide a conditional go.
- The Atlas Pre-Flight Auditor replaces the "data inventory" self-assessment with measured facts once access exists.
- Re-assess before kickoff and again before the pilot wave.

## 7. Reference results (synthetic)
- Kestrel Manufacturing (assessed 2026-08-14): GO, score about 91 — later migrated with Atlas from 2026-10-10.
- Harborline Logistics (2026-11-03): CONDITIONAL GO, score about 77 — stale accounts, agency-managed DNS and
  unknown mail-sending apps (WMS alerts, label printers).
- Quarrystone Credit Union (2026-10-28): NO-GO, score about 53 — no retention / legal-hold owner and no change owner.

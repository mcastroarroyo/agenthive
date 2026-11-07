# Discovery Notes — Tidewell Mutual Insurance: Workspace Migration and AI Claims Assistant

**Date:** 2026-10-21 · **Location:** Tidewell Mutual head office (on site) + video for regional offices
**Wursta:** Ana Torres (Engagement Manager), Diego Salas (Lead Cloud Architect)
**Status:** Internal working notes — synthetic example, all names fictional

## 1. Company snapshot

- Regional property & casualty mutual insurer, **~400 employees**: ~310 at head office, ~60 in 3 regional claims offices, ~30 field adjusters who work remotely from home and vehicles.
- ~210,000 policies in force (home, auto, small commercial). ~38,000 claims per year; volume triples during the spring hail and storm season (April–July).
- Regulated by the state insurance department. The state has adopted an insurance data-security law: written information-security programme, third-party oversight and notification of cybersecurity events within 72 hours.
- Growth plan: add small-commercial lines in two neighbouring states in 2027.

## 2. Objectives (in the client's words)

1. **Get off Exchange** — move from Exchange 2016 on premises and Windows file shares to **Google Workspace within 6 months**. Hard target: everyone on Workspace **before 2027-04-30**, i.e. before storm season.
2. **AI claims assistant** for adjusters and claims handlers: summarise the claim file, answer coverage questions from the policy wording, draft customer letters for review, and help triage first notice of loss (FNOL) during surges.
3. **Shorter claim cycle time** — property claims average **23 days** from FNOL to first payment; VP Claims wants **15 days** without adding headcount.

## 3. Stakeholders

| Name | Role | What they care about |
|---|---|---|
| Helena Brandt | Head of IT — sponsor for the Workspace programme | Stability; her 6-person IT team (one leaves in January); ending the out-of-support mail platform |
| Owen Castellano | VP Claims — sponsor for the claims assistant | Adjuster productivity, storm-season backlog, customer satisfaction |
| Martin Aldous | CFO | Cost vs the incumbent productivity-suite agreement renewing **2027-03-31**; wants the programme cost-neutral by year 2 |
| Nadia Farouk | Chief Compliance & Privacy Officer | Claimant PII, US data residency, audit trail; **no automated claim decisions** |
| Sam Whitlock | Infrastructure Manager | Active Directory, mailbox inventory, 14 TB of file shares, cutover mechanics |
| Priscilla Okonkwo | Claims Operations Manager | Super-user network, training, the claims intake mailbox |

## 4. Current state

**Collaboration**
- Exchange 2016 on premises (2 servers in a database availability group). Extended support ended in October 2025 — the cyber insurer flagged it at renewal.
- **412 user mailboxes**; **~95 shared/resource mailboxes** ("Sam thinks 95, could be more"). Average mailbox 6.2 GB; the largest is 48 GB (CEO's executive assistant). An unknown number of PST files on laptops.
- **~30 mailboxes on litigation hold** (two open lawsuits).
- Active Directory on premises; no single sign-on; MFA only for VPN.
- **14 TB** of departmental file shares on Windows file servers with mapped drives; permissions inherited from 2011-era groups.
- Desktop office suite 2016. Finance runs **40+ macro-enabled workbooks** for reserving and reinsurance reporting.
- ~60% of staff use personal phones for mail (no device management).

**Claims**
- Core claims system: vendor-hosted, SQL Server back end, implemented 2019. 1.8M claims since 2009. Limited REST API; a nightly read replica is available.
- Policy administration on Oracle (on premises); weekly CSV exports.
- Document management server: **9.6M documents** (photos, estimates, letters, police and medical reports) — **about 60% are scanned PDFs or images without a text layer**.
- **140 versions of policy wordings** as PDFs on a file share; coverage questions go to two senior claims specialists.
- Adjuster roster maintained in an Excel workbook.
- The claims intake mailbox (claims@) receives **~1,200 emails a day** during storm surges.

## 5. Pain points

- Adjusters spend **~35% of their time** reading files and writing letters (Owen's estimate, not measured).
- During surges the intake mailbox backs up for 3–4 days; temporary staff need weeks to learn coverage rules.
- "Nobody can find the latest version of anything" — file shares are not searchable.
- Photos from the field arrive by email and are re-attached manually to the claim.
- Security exposure from the out-of-support mail servers; an audit finding is open.
- The two coverage specialists are a bottleneck and one retires in 2027.

## 6. Constraints

- **Timeline:** all users on Workspace before **2027-04-30**. No mail cutover during financial year-end close (**2026-12-21 to 2027-01-15**).
- **Data residency:** claims data and documents must stay in the **US**; Compliance must review the data-processing terms; claimant data must not be used to train models.
- **Human in the loop:** the assistant never approves or denies a claim; every customer letter is reviewed and sent by a handler.
- **Records retention:** claims correspondence 7 years; litigation-hold mailboxes must be preserved through the migration.
- **People:** IT team of 6; one engineer leaves in January. Claims cannot release super-users during storm season.
- **Commercial:** the incumbent suite agreement renews **2027-03-31** — either exit before then or renew for one more year.

## 7. Budget hints

- Martin mentioned "around **$450–550k for year one, including licences**". The incumbent renewal quote is ~$310k/year for three years.
- Owen has **~$120k** in the claims operating budget for an assistant pilot this fiscal year.
- Client asked whether Google or partner funding programmes could offset the pilot.

## 8. Data sources for the claims assistant

1. Core claims database (claims, claimants, exposures, payments, status history, adjuster notes).
2. Document management (9.6M documents, majority needing OCR).
3. Policy administration (policies, coverages, endorsements, wording versions).
4. Policy wording library (140 PDF versions).
5. Adjuster roster (Excel).
6. Claims intake mailbox (FNOL emails and attachments).
7. Third-party catastrophe feed (CAT event codes).

## 9. Ideas discussed (not decisions)

- Workspace edition with Vault, DLP and data regions — Nadia asked specifically about data regions, which points to an Enterprise-level edition (verify the current edition matrix).
- Directory sync from Active Directory first; decide later whether Google becomes the identity provider.
- Claims assistant on Gemini with Vertex AI Search over policy wordings and claim documents, hosted on Agent Engine; Document AI OCR for the scanned backlog.
- BigQuery for claims analytics in a second phase (cycle time, leakage, storm-surge staffing).

## 10. Open questions

1. Exact count of shared/resource mailboxes and PST files? (Inventory export promised by 2026-10-31.)
2. Identity: keep AD with directory sync, or move to Google as identity provider? MFA for field adjusters on personal phones?
3. Which Workspace edition — is the data-regions requirement firm?
4. Will the claims vendor allow API or read-replica access for the assistant? Does the contract permit extraction of documents?
5. Who reviews AI-drafted letters — handlers or team leads — and at what weekly volume?
6. How to migrate litigation-hold mailboxes with Vault; does Legal need to sign off?
7. Finance macros: convert to Sheets/Apps Script, or keep desktop licences for ~12 power users?
8. Who are the change champions per department?
9. Budget split between IT and Claims; eligibility for funding programmes.
10. Baseline for cycle time — which report is the source of truth?

## 11. Next steps

- Wursta: rapid assessment by **2026-10-24**; SOW draft by **2026-11-06**.
- Tidewell IT: mailbox inventory export by **2026-10-31**.
- Compliance: share the data-processing agreement template.
- Joint workshop with the claims-system vendor in the week of **2026-11-16**.

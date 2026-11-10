# Design Review — Kestrel Manufacturing Workspace Migration (fictional)

## 1. Document control

| Field | Value |
|---|---|
| Version | 1.3 |
| Date | 2026-09-24 |
| Author | Priyanka Desai (Sablewood Solutions Architect) |
| Status | Draft for approval |
| Client | Kestrel Manufacturing Inc. |

## 2. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-09-10 | P. Desai | First draft after discovery |
| 1.1 | 2026-09-16 | P. Desai | Pre-flight scan results added |
| 1.2 | 2026-09-19 | D. Ferraz | Wave approach and cutover window |

## 3. Executive summary
Kestrel will move 1,200 users from Microsoft 365 and the KES-FS01 file server to Google Workspace Enterprise Standard in eight waves between 2026-10-10 and 2026-12-05. Mail, calendar, contacts, OneDrive and 28.2 TB of departmental file shares are in scope. Litigation holds for 24 custodians move to Google Vault before their wave.

## 4. Scope and requirements traceability
| Req | Requirement | Design section |
|---|---|---|
| R1 | Migrate mail, calendar, contacts for all employees | 6, 7 |
| R2 | File shares to Shared drives with equivalent access | 6.2 |
| R3 | Preserve legal holds | 7 |
| R4 | Spanish-language support for Monterrey | 8 |

## 5. Current state (source environment)
- Microsoft 365 E3: Exchange Online (11.5 TB mailboxes), OneDrive (7.2 TB).
- KES-FS01: 12 departmental shares, 9.5 TB, 4.9 million files; Engineering share holds 1.64 million files.
- 37 shared mailboxes, 58 room/equipment resources, 188 distribution lists, 7 applications relaying SMTP.

## 6. Target design
### 6.1 Identity and organisation
Google is the identity provider; directory sync from the on-premises directory. OUs by site (Cedar Falls, Monterrey, Field) with department sub-OUs. Licences: 1,250 seats for 1,250 users (includes growth buffer).

### 6.2 Shared drives
One shared drive per department; restricted areas split into their own shared drives (Finance 6, Legal 4, HR 3). Engineering split into 5 shared drives to stay under the 400,000-item limit. [insert diagram]

### 6.3 Mail flow
MX switches per wave on Saturday 06:00; split delivery during coexistence; SMTP relay service with IP allowlist for the 7 applications.

## 7. Security and compliance
- 2-Step Verification enforced for all users before their wave.
- Vault matter KES-LIT-01 with holds for 24 custodians; retention rule 7 years for Legal.
- DLP rules for Finance and HR: TBD.
- External sharing: allowlisted domains only.

## 8. Migration approach
Atlas suite: pre-flight audit, wave planning (pilot IT, then ascending complexity, executives last), personalised comms in English and Spanish, bulk transfer 10-13 days before cutover, Friday-night delta sync, post-migration validation and daily status.

## 9. Risks, assumptions and dependencies
| ID | Risk | Mitigation |
|---|---|---|
| RK1 | Long paths in Engineering share | Remap share root; shorten folders |
| RK2 | Month-end close for Finance | Finance wave after month-end |
| RK3 | Legal sign-off on Vault holds | Review two weeks before W6 |

## 10. Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Sablewood Delivery Lead | Ana Lucia Mendoza | 2026-09-25 | Approved |
| Sablewood Solutions Architect | Priyanka Desai | 2026-09-25 | Approved |
| Client Project Sponsor | Robert Lindqvist | — | — |
| Client IT Owner | Megan Hollis | 2026-09-26 | Approved with comments |

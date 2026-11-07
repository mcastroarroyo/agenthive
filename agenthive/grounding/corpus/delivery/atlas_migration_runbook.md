# Atlas Migration Runbook (Microsoft 365 and file shares to Google Workspace)

**Owner:** Workspace practice (Wursta) · **Version:** 5.0 · **Last reviewed:** 2026-09-25 · **Status:** current
Synthetic demo document. The Atlas suite (Atlas 1-7) automates this runbook; the demo tenant is the fictional
Kestrel Manufacturing (1,200 users, about 28 TB).

## 1. Phases and the Atlas agents
| Phase | Agent | Output |
|---|---|---|
| Pre-flight audit | Atlas 1 · Pre-Flight Auditor | Inventory, complexity per department, blockers |
| Wave planning | Atlas 2 · Batch Planner | Baseline wave plan with cutover and bulk dates |
| User communications | Atlas 3 · User Comms | Seven-touchpoint sequence per wave and segment |
| Bulk transfer | Atlas 4 · Core Data Mover | Mail, OneDrive to My Drive, file shares to Shared drives |
| Delta and cutover | Atlas 5 · Delta Sync | Final incremental sync, go/no-go, MX switch |
| Validation | Atlas 6 · Post-Migration Validator | Counts, checksums, permission audit, discrepancies |
| Reporting | Atlas 7 · Status Reporter | Daily status for the team and the client |

## 2. Pre-flight checks and standard remediation
- **Litigation holds:** Vault matter and holds created and approved by Legal before the custodians' wave; source
  holds stay for 90 days after cutover.
- **Oversized mailboxes (over 50 GB):** pre-stage 21 days before the wave; ask owners to archive mail older than
  seven years.
- **PST files:** excluded from share transfer by default; ingestion only by change order.
- **Long paths (over 400 characters):** remap the share root deeper or shorten folder names before the bulk pass.
- **Shared drive item limit:** a shared drive holds at most 400,000 items; split large shares by top-level folder.
- **Broken inheritance:** restricted folders become their own shared drive (or a limited-access folder).
- **"Everyone" permissions:** remove at source before the wave — they would map to domain-wide access.
- **Orphaned SIDs:** dropped and logged in the permission audit.
- **Executables (.exe, .msi, .bat):** excluded by extension policy; kept read-only at source.
- **Application mail relays:** SMTP relay service with an IP allowlist; test each application before its wave.
- **Public folders, third-party archives, Teams chat:** out of scope unless contracted.

## 3. Wave planning rules
Pilot wave first (IT, about 40 users) to validate the runbook; then departments in ascending complexity; executives
last as a white-glove wave with their assistants. Waves are capped at 260 users and 7,500 GB by default. Cutovers on
Saturdays at a 7-day cadence; global freezes (Thanksgiving weekend 2026-11-28, year-end 2026-12-26) and department
blackouts (Finance month-end) push a wave to the next slot. Complexity score drivers: average mailbox size, share
of legal-hold users, delegates, folders with unique permissions, oversized mailboxes and shares over the item limit.

## 4. Bulk transfer
- Bulk copy starts max(10 days, data / 800 GB per day + 3 days) before cutover.
- Monitor per workload: % complete, throughput (GB/h), ETA against the delta-sync start (Friday 18:00).
- Error classes and handling:
  - *transient* — throttled_429 (auto-retry with backoff, ~97% recover), network_timeout (~92%);
  - *fixable* — permission_denied_source (grant read to the migration account, then retry; ~85%), path_too_long
    (shorten paths, re-run folder pass; ~98%), target_quota (raise allocation);
  - *policy skip* — item_too_large (over 25 MB per item), unsupported_type; reported, not retried;
  - *permanent* — corrupt_item; reported.
- Health thresholds on actionable errors: green below 0.1%, amber 0.1-0.5%, red at 0.5% or more. Red, or an ETA
  after the delta start, is escalated to the migration lead the same day.

## 5. Delta sync and cutover
Final delta starts Friday 18:00; MX switches Saturday 06:00 (12-hour window). Delta size is estimated from the
hours since the last bulk pass: about 62 new mail items per user per day (85 KB average) and 0.35% of files changed
per day (1.9 MB average), plus any unfinished bulk data. See the Atlas Cutover Checklist for gates.

## 6. Validation tolerances
- Unexplained item variance at most 0.1% per workload (explained skips listed separately).
- Checksum sample (1,000-2,000 files per wave): mismatches at most 0.05%.
- 100% of delegations and shared-mailbox groups recreated; external shares reviewed by owners.
- Users are told about skipped items (for example mail over 25 MB) in the T+10 wrap-up; the source stays read-only
  for 90 days.

## 7. Hypercare
Two weeks per wave: floorwalkers on Monday 07:00-17:00 at each site, a help chat space, phone extension 4357 and a
daily ticket review. Exit criteria: no open Sev1/Sev2, new tickets under 5 per day for the wave, pulse score 3.5+.

## 8. Issue severity
Sev1 — data loss, security exposure or a site unable to work (cutover stops). Sev2 — a wave's cutover or a
department's work is at risk. Sev3 — limited impact with a workaround. Sev4 — cosmetic. Overall status is red with
any open Sev1 and amber with a Sev2 due within 14 days.

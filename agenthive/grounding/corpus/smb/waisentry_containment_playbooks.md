# WAISentry containment playbooks and escalation runbook

**Owner:** Wursta WAISentry team · **Client runbook:** Kitewing Software (fictional) · **Pre-approval signed:** 2026-10-05
by Marcus Bell (COO & CFO) · Synthetic demo document; all actions in the Agent Hive are simulated.

## Principle
WAISentry contains threats in under 60 seconds because the client **pre-approves** a short list of reversible actions
during onboarding (Day 3). A certified Wursta analyst confirms the incident first; then only these four playbooks run
without asking. Everything else is escalated to the client's on-call contact.

## Pre-approved playbooks
| Id | Playbook | What it does | Minimum severity | Limits | Rollback |
|---|---|---|---|---|---|
| PB-01 | Instant web session termination | Signs the user out of every web and mobile session and revokes OAuth and app-password tokens (Admin SDK: users.signOut + tokens.delete) | high | Up to 10 users per incident | None needed — the user signs in again with a security key |
| PB-02 | OAuth application revocation | Revokes the app for every user who granted it and blocks its client id tenant-wide | high | Apps in the blast radius; never an allowlisted app | Admin unblocks the client id |
| PB-03 | Targeted account suspension | Suspends the account for a fixed window while the password is reset | high | Max 3 accounts per incident, max 4 hours, never super admins or the break-glass account | Automatic un-suspend at the end of the window |
| PB-04 | Drive access quarantine | Removes "anyone with the link" and external permissions from the incident's files; internal access untouched; files never deleted | medium | Files in the blast radius | One-click restore of the recorded permissions |

Typical durations: PB-01 3 s, PB-02 5 s, PB-03 5 s, PB-04 2 s plus 12 s per file. They run in parallel, so a full
containment usually completes in well under a minute.

## Not pre-approved — always escalate
| Action | Owner |
|---|---|
| Device or network isolation (EDR console, switch port) | Client IT — recommended for the next pre-approval review |
| Wipe or reimage a device | Client IT only |
| Firewall or IP blocks | Client IT with analyst guidance |
| Domain or sender blocks in DNSFilter / Mimecast | On-call analyst with client approval |
| Password reset, credential rotation | Client IT / the user |
| Removing a mail filter or forwarding address | On-call analyst with client approval |
| Purging messages from mailboxes | On-call analyst with client approval |
| Deleting accounts, files or mailboxes | Never by WAISentry — client only |
| Holding a payment, verifying vendor bank details | Client finance (Marcus Bell) |
| Changing 2-step verification or tenant-wide settings | Client admin |
| Revoking an allowlisted app, suspending a super admin, suspensions over 4 hours | Client approval |

## Escalation matrix (Kitewing runbook, demo values)
| Severity | Route | Runbook target |
|---|---|---|
| Critical (P1) | Page the on-call certified analyst immediately; phone the client on-call (Noah Kim); payment fraud also Marcus Bell | 15 minutes |
| High (P2) | Phone the client on-call | 30 minutes |
| Medium (P3) | Ticket and email in the next business hour | next business hour |
| Low (P4) | Weekly SOC report | weekly |

Millbrook on-prem issues also go to Hugo Laurent (IT Support Technician).

## Lessons from Kitewing incidents
- **INC-1101-01 (consent phishing → BEC):** PB-01, PB-02, PB-03 and PB-04 completed 29 seconds after confirmation.
  Removing the forwarding filter and holding the $48,600 payment were escalated and done by the client within 17 minutes.
- **INC-1028-01 (infostealer):** PB-01 revoked every session 7 minutes before the attacker replayed the stolen cookie.
  Device isolation waited 14 minutes for client IT.
- **INC-1030-01 (password spray from an unmanaged reception PC):** no playbook applied; isolation took 41 minutes after
  confirmation. **Recommendation:** add on-prem device isolation to the pre-approved list.

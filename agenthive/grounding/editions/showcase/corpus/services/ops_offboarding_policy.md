# Offboarding & Data Deprovisioning Policy

**Owner:** IT Service Desk with Security · **Last reviewed:** 2026-09-30 · **Status:** current
**Control:** WC-AC-03 (timely deprovisioning of leavers). Synthetic demo document.

## 1. Purpose
When someone leaves Sablewood — employee or contractor — their access must end on time, client access first, and their
data must stay available to the business without becoming orphaned. Every step leaves evidence an auditor can verify.
Charon automates the checklist; a human from the Service Desk confirms destructive steps.

## 2. Timing rules
- **Voluntary leavers and contract ends:** steps start at the termination time (the end of the last working day). No
  access is removed before that moment, so the person can hand over properly.
- **Involuntary terminations:** S1 is executed at the moment of notification, before the conversation ends.
- SLAs below are counted from the termination time. Anything past its SLA is reported as overdue in the daily
  Service Desk review.

## 3. The ten steps (in order)
| Step | Action | SLA |
|---|---|---|
| S1 | Suspend sign-in, reset password, revoke sessions, OAuth tokens and app passwords | 1 hour |
| S2 | Remove partner delegated-admin access in client tenants; notify the client PM and the account CSM | 4 hours |
| S3 | Disable user-managed service-account keys the person created; remove personal IAM bindings | 4 hours |
| S4 | Remove GitHub organisation membership; transfer repository ownership to the team | 8 hours |
| S5 | Transfer Drive ownership to the manager; reassign shared-drive manager roles | 3 days |
| S6 | Delegate the mailbox to the manager for 30 days; apply Vault retention | 3 days |
| S7 | Transfer recurring calendar events and Chat space ownership | 3 days |
| S8 | Reclaim SaaS licences (Jira, HubSpot and others) | 5 days |
| S9 | Recover the laptop (remote wipe if not returned) and the security key | 10 days |
| S10 | Convert to an archived user at day 30; delete after the retention period | 30 days |

**Why this order:** client access (S2) and cloud credentials (S3) carry the most risk, so they follow immediately after
the account is suspended. Suspending the account does not delete data, so data transfers (S5-S7) can follow safely.
**Service-account keys** must be disabled explicitly — removing the user does not invalidate keys they created.

## 4. Before suspension
If the leaver is the **sole manager of a shared drive**, add a co-manager before S1 so the drive is never orphaned.
Ask the manager whether any scheduled jobs, webhooks or OAuth integrations run under the leaver's identity; move them
to a team-owned service identity.

## 5. Legal hold
When Legal has placed a hold:
- **No deletion** of mail, Drive, Chat or the account (S10 is blocked until Legal releases the hold).
- Apply the legal Vault hold (indefinite) instead of standard retention in S6.
- Devices are **imaged for Legal before any wipe** (S9).
- Access removal (S1-S4, S8) proceeds normally — a hold preserves data, it does not preserve access.

## 6. Contractors
Contractors usually use their own devices: S9 covers only the security key and removal of company data through
endpoint management. Contractor access to client-delegated projects is reviewed by the engagement lead on the same day.

## 7. Retention
- Archived user from day 30 to month 12; data remains searchable in Vault.
- Deletion after 12 months unless a legal hold or a client contract requires longer.
- Drive files transferred to the manager are re-filed into team shared drives within 30 days.

## 8. Evidence
Each executed step produces an evidence entry: case id, step, actions, actor, timestamp, evidence id and a hash that
chains to the previous entry, so missing or altered entries are detectable. The Service Desk lead signs off the log
within 5 business days. Evidence is retained for 3 years and sampled in the quarterly access review (WC-AC-01).

## 9. Notifications
- Client PMs are notified of removed delegated access the same day: "As part of our offboarding process, <name> no
  longer has administrative access to your tenant. Your Sablewood contact remains <PM>."
- The manager receives the data-transfer summary; HR receives the hardware-return status.

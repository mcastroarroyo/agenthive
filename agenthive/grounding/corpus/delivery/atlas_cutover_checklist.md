# Atlas Cutover Checklist and Go/No-Go

**Owner:** Workspace practice (Wursta) · **Version:** 3.1 · **Last reviewed:** 2026-09-25 · **Status:** current
Synthetic demo document. Used by Atlas 5 (Delta Sync) for every wave.

## 1. Timeline (cutover on Saturday)
| Id | When | Item | Owner | Critical |
|---|---|---|---|---|
| C01 | T-14 | Wave roster frozen and approved by the client PM | Client PM | Yes |
| C02 | T-10 | Bulk transfer started for all workloads | Wursta migration lead | Yes |
| C03 | T-7 | Training sessions scheduled and invites sent | Wursta change lead | No |
| C04 | T-7 | "What is changing" email sent to the wave | Wursta change lead | No |
| C05 | T-3 | MX and autodiscover TTL lowered to 300 seconds | Client network team | Yes |
| C06 | T-3 | Mobile re-add guide published | Wursta change lead | No |
| C08 | T-2 | SMTP relay and application mail flows for the wave tested | Client PM | Yes |
| C09 | T-1 | Go/no-go call held and approver recorded | Client sponsor + Wursta engagement lead | Yes |
| C10 | T-1 | Final "tonight is the night" email sent | Wursta change lead | No |
| C11 | T-1 | Rollback plan reviewed (MX revert; source mailboxes untouched) | Wursta migration lead | Yes |
| C12 | T-0 | Floorwalker and support roster confirmed for Monday | Wursta change lead | No |
| C13 | T-1 | Vault holds verified for custodians in the wave | Client General Counsel | Yes when the wave has legal-hold users |

## 2. Gates
1. **Bulk copy complete:** at least 99% of the wave's data (by GB).
2. **Actionable error rate:** below 0.5% on every workload (transient and fixable errors; policy skips excluded).
3. **Delta fits the window:** estimated scan + transfer time at most 12 hours from the Friday 18:00 start.

## 3. Verdict rules
- **GO:** all gates pass and every critical checklist item is done (C09 is the decision meeting itself).
- **CONDITIONAL GO:** all gates pass and exactly one critical item is still open with a named owner and an ETA
  before the delta start. The go/no-go call records the condition and who confirms it.
- **NO-GO:** any gate fails, more than one critical item is open, or a blocked critical item has no ETA. The wave
  moves to the next cutover slot and the users get a "new date" message from Atlas User Comms.

## 4. Cutover sequence
1. 18:00 Friday — final delta sync starts (mail, Drive, Shared drives).
2. Delta complete — verify counts on a 10-user sample.
3. 06:00 Saturday — switch MX to Google; enable Gmail for the wave's users.
4. 07:00 — smoke tests: send and receive internally and externally, calendar invitations, shared drive access,
   one delegated mailbox, one application relay.
5. 09:00 — rollback point expires; after this the team fixes forward.

## 5. Rollback
Before 09:00 Saturday: revert MX records (TTL is 300 seconds), re-enable Outlook profiles, and post the rollback
message. Source mailboxes are never modified during cutover, so rollback loses nothing. After the rollback point,
issues are handled as hypercare tickets.

## 6. The go/no-go call (T-1, 15:00)
Attendees: client sponsor (approver), client PM, Wursta engagement lead, migration lead and change lead. Agenda:
gates, checklist, open critical items, delta estimate, support roster, decision. The decision and approver are
recorded in the cutover log; Atlas 5 starts the delta only with an approver's name.

## 7. Monday after cutover
Floorwalkers from 07:00, champions drop-in at 10:00 and 15:00, help chat space staffed, ticket review at 12:00 and
16:00. The DAY1 welcome email goes out at 07:00 from the new Gmail.

# Client Health & Escalation Playbook

**Owner:** Leah Brandt, Customer Success Lead · **Last reviewed:** 2026-10-12 · **Status:** current
**Applies to:** every active Sablewood engagement with a steering committee, weekly sync or monthly review.
Synthetic demo document — all accounts and people referenced are fictional.

## Why this playbook exists
Most client escalations are visible in meetings weeks before they reach an executive inbox: a sponsor who stops
attending, a "small" extra request, a second slipped date, a disputed invoice. The meeting-intelligence loop turns those
signals into action the same day: **Janus** turns the recording into a searchable knowledge record, **Helios** audits
the transcript for risk, **Athena** turns action items into owned, dated tasks, and **Oracle** updates the account's
churn-risk score. This playbook defines the thresholds and the response every agent and every human follows.

## The five risk signals
| Signal | What it sounds like | Typical evidence |
|---|---|---|
| Dissatisfaction | "frustrated", "not acceptable", "disappointed", "again?" | Direct complaints, raised voices, sarcasm |
| Scope creep | "while you're at it", "can we also add", "one more thing", "without a CR" | New sources, features or users not in the SOW |
| Disengagement | "busy", "reschedule", "no time", "not a priority" | Executive sponsor absent, cameras off, late joins |
| Timeline risk | "slip", "delay", "blocked", "waiting on", "deadline" | Moved milestones, external dependencies |
| Budget / commercial | invoice disputes, "escalate to finance", renewal doubts | Overdue invoices, hours above forecast |

## Severity levels (RAG)
**Green** — no category scores 0.5 or higher and sentiment is stable. Log the audit; no alert.

**Amber** — any one of:
- one signal category scores 0.5 or higher;
- the executive sponsor missed two consecutive steering meetings;
- latest sentiment dropped more than 0.3 versus the average of the previous three meetings.

Response: alert the PM and the CSM; acknowledge by the next business day; mitigation plan within 5 business days.

**Red** — any one of:
- two or more categories score 0.5 or higher;
- an explicit escalation threat ("I'll escalate to…") or the renewal is questioned;
- latest sentiment is -0.3 or lower.

Response: alert the PM, CSM, Account Executive and Delivery Director; acknowledge within 4 business hours; executive
call with the client sponsor within 5 business days; Oracle re-scores the account the same day.

## Anatomy of a good alert
1. **Headline** — account, meeting, severity, the one-line reason.
2. **Evidence** — 2-4 verbatim quotes with timestamps (e.g. "[04:30] ... not acceptable to our ops leadership").
3. **Why it matters** — renewal date, ARR, upcoming QBR, dependency.
4. **Recommended actions** — at most 5, each with an owner and a date.
Never paraphrase a client's words as harsher than they were, and never include personal opinions about individuals.

## Handling scope creep in the room
- Never agree to new scope in a meeting, even "small" items. Say: "Let us write it up as a change request so you can see
  the effort and timeline impact before anyone decides."
- Draft the change request within 5 business days and label any analysis as "evaluation only — no work until approved".
- Record the request in the decision log so it cannot be re-litigated later.

## Disengaged sponsors
If the executive sponsor misses two steering meetings in a row, the engagement lead requests a 30-minute 1:1 within
10 business days. If attendance stays below 50% over 90 days, the account is at least "watch" regardless of sentiment.

## Churn-risk bands (Oracle)
Oracle's explainable score (0-100) weighs sponsor attendance (15), latest sentiment (15), support load (12), meeting
attendance (10), sentiment trend (10), adoption (10), overdue invoices (10), slipped milestones (10) and NPS (8).

| Band | Score | Play |
|---|---|---|
| Critical | 70-100 | Executive save plan within 5 business days: Sablewood executive call with the sponsor, recovery plan with dated milestones, commercial goodwill review, weekly health check until green. |
| High | 50-69 | Account review (CSM + engagement lead) within 10 business days; re-engage the sponsor; fix the top two drivers; re-score after the next meeting. |
| Watch | 30-49 | CSM monitors bi-weekly; address the top driver; confirm priorities at the next QBR. |
| Healthy | 0-29 | Business as usual — ask for a reference or case study, explore expansion. |

An account is **urgent** when it is high or critical and the renewal is within 120 days. The CSM owns the save plan;
the score and drivers are written to the CRM account record so the AE sees them before every call.

## Data handling
Transcripts and recordings are client-confidential. Index meeting records with **account_team** access by default;
company-wide access is allowed only for workshops and enablement sessions with no commercial content. Quotes in
alerts stay inside Sablewood's Google Chat; never forward them to the client.

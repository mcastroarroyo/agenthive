# WAISentry compliance and cyber-insurance map

**Owner:** Wursta WAISentry team · **Last reviewed:** 2026-11-03 · Synthetic demo document; not legal advice. The client
Kitewing Software is fictional.

## Shared responsibility
WAISentry supplies **monitoring, response and evidence**. It does not make an organisation compliant or insurable on
its own: policies, enforcement (MFA, EDR deployment, backups), training and final answers belong to the client and its
broker, auditor, assessor or counsel. Every mapping below says whether WAISentry **supports** a requirement, covers it
**partially**, or leaves it to the **client**.

## Cyber-insurance questionnaires
Carriers increasingly ask for 24/7 monitoring (MDR), EDR on every endpoint, MFA on email, remote access and admin
accounts, security-log retention, phishing training and funds-transfer fraud controls.
- **Supports:** 24/7/365 monitoring and response; out-of-hours containment without waiting for the insured (four
  pre-approved playbooks); log retention in the client's own tenant (Kitewing: 400 days for scored events, 90 days raw —
  demo configuration); email impersonation correlation; OAuth app control; incident history with outcomes.
- **Partial:** EDR coverage (deployment is the client's), MFA (enforcement is the client's), funds-transfer fraud
  (WAISentry detects payment diversion; the call-back procedure is a finance control), end-of-life systems.
- **Client:** backups (offline / immutable, tested restores), training programme.

## FTC Safeguards Rule (16 CFR Part 314)
Applies to non-bank financial institutions under the GLBA (for example businesses offering consumer financing, tax
preparers, mortgage brokers). WAISentry maps most directly to **§314.4(c)(8)** — monitor and log the activity of
authorised users and detect unauthorised access — and to **§314.4(d)(2)** — continuous monitoring as the alternative to
annual penetration tests plus vulnerability assessments every six months. It feeds the written risk assessment
(§314.4(b)), inventory (§314.4(c)(2)), incident response plan (§314.4(h)), the Qualified Individual's annual report to
the board (§314.4(i)), and the facts needed for the FTC notification of a notification event affecting 500 or more
consumers within 30 days of discovery (§314.4(j)).

## HIPAA Security Rule
**§164.312(b) Audit controls** requires hardware, software and procedural mechanisms that record and examine activity
in information systems that contain or use ePHI. WAISentry records Workspace, endpoint and on-prem activity in the
client's tenant and examines it 24/7 — provided every system holding ePHI is connected. It also supports information
system activity review (§164.308(a)(1)(ii)(D)) and security incident procedures (§164.308(a)(6)(ii)). The Security Rule
sets no log-retention period; required documentation is kept 6 years (§164.316(b)(2)(i)). Tokenisation keeps content
and identities in the tenant; confirm with counsel whether a business associate agreement is needed.

## SOC 2 (Trust Services Criteria)
Supports **CC7.2** (monitor for anomalies), **CC7.3** (evaluate security events), **CC7.4** (respond to incidents);
partial for CC7.5 (recovery), CC6.1/CC6.6 (logical access, boundary protection) and CC6.8 (malicious software).
Kitewing's own SOC 2 Type II renewal fieldwork is in December 2026; WAISentry case files and monthly reports are
evidence for CC7.

## CMMC Level 2 (NIST SP 800-171 Rev. 2)
Supports AU.L2-3.3.1 (create and retain audit logs), AU.L2-3.3.2 (trace individual users — deterministic tokens are
re-identifiable inside the tenant), AU.L2-3.3.5 (correlate audit review), IR.L2-3.6.1 (incident-handling capability),
SI.L2-3.14.6 (monitor communications for attacks) and SI.L2-3.14.7 (identify unauthorised use); partial for
IR.L2-3.6.2 (external reporting stays with the contractor). Confirm the assessment scope — WAISentry components as a
security protection asset — with the assessor.

## Evidence locker (Kitewing, demo)
| Id | Evidence | Date |
|---|---|---|
| EV-01 | Monthly SOC report — October 2026 | 2026-11-02 |
| EV-02 | Telemetry retention configuration | 2026-10-05 |
| EV-03 | Incident case file INC-1101-01 | 2026-11-01 |
| EV-04 | Pre-approved containment authorisation (PB-01 to PB-04) | 2026-10-05 |
| EV-05 | Security Posture & Application Review — baseline and re-check | 2026-10-01 / 2026-11-06 |
| EV-06 | 2-step verification and security-key enrolment report | 2026-11-06 |
| EV-07 | Endpoint EDR coverage report | 2026-11-06 |
| EV-08 | KnowBe4 training completion and phish-prone trend | 2026-11-03 |
| EV-09 | Mimecast and DNSFilter policy exports | 2026-11-03 |
| EV-10 | Escalation matrix and on-call roster | 2026-10-05 |
| EV-11 | Quarterly access review Q3 2026 | 2026-10-16 |
| EV-12 | Zero-PII tokenisation design and data-flow diagram | 2026-10-05 |
| EV-13 | Kitewing incident-response plan | 2026-09-15 |

# WAISentry client profile — Kitewing Software (demo tenant)

**Owner:** Wursta SOC · **Client:** Kitewing Software, Inc. (fictional) · **Live since:** 2026-10-07 18:00 · Synthetic demo
document. All times are Kitewing local time (UTC-6).

## Estate covered
- **Google Workspace** tenant kitewing.example: 62 people (60 employees, 2 contractors) plus an accounts-payable shared
  mailbox, a break-glass super admin and a scan-to-email account. 2-step verification is enforced for everyone; 60
  people use hardware security keys and the 2 contractors use Google prompts until their keys arrive (2026-11-09).
- **Laptops:** 38 macOS, 18 Windows 11 and 6 ChromeOS, about a third used fully remotely; EDR on every macOS and
  Windows laptop except one contractor BYOD machine. ChromeOS relies on verified boot and DNS filtering.
- **Millbrook office (legacy on-prem):** MB-DC01 Active Directory domain controller (badge system, printers, file-share
  sign-in; 41 AD accounts not synced to Workspace), MB-FS01 Windows Server 2016 file server (Projects-Archive, 1.2 TB;
  SMBv1 still enabled), MB-SYSLOG01 syslog forwarder to the in-tenant pipeline, MB-FW01 firewall with IDS/IPS, and two
  office PCs (MB-WS02 print station; MB-WS07 reception PC, removed 2026-10-31).
- **SaaS security tools whose alerts WAISentry collects:** KnowBe4 (awareness + Phish Alert Button), Mimecast (email
  gateway), DNSFilter (DNS security) and a cloud web proxy.

## Contacts
| Role | Person |
|---|---|
| Client security contact / on-call | Noah Kim, IT & Security Administrator |
| Millbrook IT | Hugo Laurent, IT Support Technician |
| Executive sponsor, finance escalations (payments) | Marcus Bell, COO & CFO — signed the pre-approval 2026-10-05 |
| Executive briefing recipient | Dana Whitfield, CEO |

## Incidents since go-live
| Id | Date | Severity | What | Outcome |
|---|---|---|---|---|
| INC-1015-01 | 2026-10-15 | medium | Payroll-lure credential-harvest phishing to 14 users | 1 click blocked at DNS; 14 messages purged |
| INC-1021-01 | 2026-10-21 | high | MFA-fatigue push bombing of a contractor | 11 prompts denied; suspended (PB-03) |
| INC-1023-01 | 2026-10-23 | medium | Legacy remote-access tool on MB-FS01 beaconing to a re-registered domain | Blocked by DNSFilter + IDS; tool removed |
| INC-1028-01 | 2026-10-28 | critical | Infostealer on a Millbrook support laptop; stolen cookie replayed from Frankfurt | Sessions revoked 7 min earlier (PB-01); replay failed |
| INC-1030-01 | 2026-10-30 | high | Password spray against MB-DC01 from the reception PC | 0 successes; port disabled after 41 min |
| INC-1101-01 | 2026-11-01 | critical | Consent phishing of a finance user → hidden forwarding → $48,600 payment diversion attempt | Contained in 29 s; $0 lost |
| INC-1106-01 | 2026-11-06 | medium | Confidential customer ARR export shared publicly and to a personal mailbox | Open — Drive quarantine (PB-04) recommended |

## The Sunday 02:00 story (INC-1101-01)
At 01:58 a finance user received "Shared document: Q4 vendor remittance" from a two-day-old domain. At 02:04 she
granted an unverified app called "PDF Secure Viewer" mail-read, mail-settings and full-Drive access — no password or
MFA needed. At 02:05 the app created a hidden filter forwarding invoice, payment and bank emails to an external
mailbox. At 02:06 a password sign-in from Amsterdam, eight minutes after a Cedar Harbor sign-in, failed at the
security key. At 02:07 a lookalike-vendor email asked accounts payable to change bank details for open invoice
TD-2026-1187 ($48,600), while the app downloaded 38 finance files and created two public links. Gemini triage flagged
the grant 8 seconds after it happened; analyst A-17 confirmed at 02:07:52; the four pre-approved playbooks finished at
02:08:21. The client removed the filter at 02:24 and finance verified the vendor by phone the next morning. A
traditional emailed alert would have been read on Monday at 08:00 — almost 30 hours later.

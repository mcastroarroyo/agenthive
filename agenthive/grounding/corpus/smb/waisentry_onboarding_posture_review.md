# WAISentry onboarding and the Security Posture & Application Review

**Owner:** Wursta WAISentry team · **Source:** WAISentry brief (posture review offer, 48-hour ramp) · **Last reviewed:**
2026-11-02 · Synthetic demo document; the client Kitewing Software is fictional.

## Complimentary Security Posture & Application Review (30 minutes)
A read-only review of the client's Google Workspace tenant through native APIs — nothing is installed on laptops. It
produces a posture score (0-100), the top fixes with effort and owner, and the quick wins. Checks:

| Check | Why it matters |
|---|---|
| 2-step verification coverage (and security keys) | Phishing-resistant keys stop stolen passwords; prompt users can be MFA-fatigued |
| Super-admin count | Every super admin is a full-tenant takeover if phished |
| External sharing defaults (Drive) | "Anyone with the link" defaults leak confidential files |
| Automatic forwarding to external addresses | Hidden forwarding is the core of business email compromise |
| Legacy protocols (IMAP/POP, app passwords) | They bypass 2-step verification |
| Unverified third-party (OAuth) apps | Consent phishing needs no password and bypasses MFA |
| Dormant and orphaned accounts | Old admin accounts are a common way back in |
| Email authentication (SPF, DKIM, DMARC) | Stops direct spoofing of the domain |
| Audit-log export and 24/7 review | Without it a 2:00 AM alert waits until Monday |
| Endpoint coverage (EDR) and end-of-life systems | Unmanaged devices launch attacks unseen |
| Login challenges and password policy | Blocks credential stuffing |
| Mobile device management | Lost phones cannot keep company mail |

Scoring: each check has a weight; pass = full weight, partial = half, fail = none.

**Kitewing example:** the first review (2026-10-01) scored **20**; the re-check on 2026-11-06 scored **75**. Fixed:
2-step verification for everyone, super admins cut from 6 to 3, external auto-forwarding disabled (2026-11-02, after
INC-1101-01), DMARC to quarantine, unverified apps blocked for new grants (2026-11-03). Still open: Marketing OU link
sharing default (caused INC-1106-01), 4 legacy unverified app grants, the scanner's app password, EDR on a contractor
BYOD laptop and the Windows Server 2016 file server (support ends 2027-01-12).

## The 48-hour onboarding (WAISentry brief)
| Day | Name | What happens | Client provides |
|---|---|---|---|
| 1 | Connect the tenant via native APIs | Deploy the telemetry pipeline into the client's own Google Cloud project; read-only Workspace connectors (Admin SDK Reports API, Directory API, Alert Center); create the tenant tokenisation key; connect SaaS security tools (e.g. KnowBe4, Mimecast, DNSFilter, web proxy, EDR) by API | A super admin for about an hour; SaaS tool API access; escalation contacts |
| 2 | Baseline calibration + hybrid setup | Back-fill available audit history; calibrate known devices, travel, VIP and finance roles, sanctioned apps; ship firewall/IDS and domain controller / file server events through a syslog forwarder; test every source end to end | A small VM or appliance for the forwarder; firewall syslog target; VIP list |
| 3 | Continuous active defence | Sign the pre-approved playbooks and escalation matrix; tabletop one simulated incident; 24/7 monitoring goes live; first daily summary | A signatory; on-call phone numbers |

Kitewing: review 2026-10-01, Day 1 2026-10-05, live 2026-10-07 18:00. Cloud-only clients skip the hybrid step.

## Options compared (WAISentry brief)
- **Internal 24/7 SOC:** at least 5 FTE ($450k-$600k a year) plus tooling ($60k-$100k), 6-9 months to ramp, $550k+ a
  year. 24/7/365 is 8,760 hours a year — roughly five people before holidays and sick cover.
- **Traditional MSSP:** tooling $80k-$150k a year with data-volume "taxes", the customer still staffs level 2/3
  investigation, 3-6 months to ramp, $120k+ a year.
- **WAISentry:** staffing and tooling included, 48-hour ramp, predictable monthly fee quoted by Wursta.

Never estimate a WAISentry price; offer the posture review and a quote instead.

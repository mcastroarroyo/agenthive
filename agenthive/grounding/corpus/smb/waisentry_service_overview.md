# WAISentry — service overview, phases and targets

**Owner:** Wursta WAISentry team · **Source:** WAISentry brief (Wursta sales deck) · **Last reviewed:** 2026-11-02
Synthetic demo document for the Wursta Agent Hive. The client used in every example, Kitewing Software, is fictional.

## What WAISentry is
WAISentry is Wursta's managed 24/7 security operations service for cloud-first, hybrid-ready small and mid-size
businesses. It rests on three pillars (WAISentry brief):

1. **24/7/365 human SOC + AI speed** — Gemini triage removes the noise in seconds; certified Wursta analysts verify
   every real threat around the clock.
2. **Zero-PII data privacy** — telemetry is evaluated and correlated inside the client's own Google Cloud tenant and
   tokenised before any alert leaves it (see "WAISentry zero-PII architecture").
3. **Comprehensive coverage** — cloud identity (Google Workspace), distributed laptops (macOS, Windows, ChromeOS) and
   hybrid infrastructure (firewalls, domain controllers, file servers), plus the client's SaaS security tools.

## Why it exists (WAISentry brief)
- **82% of intrusions are malware-free** — attackers use valid accounts, stolen sessions and consent grants, which
  antivirus alone does not see.
- **Business email compromise and payment diversion cause about $2.9B in annual losses.**
- **99% of cloud security failures stem from customer-side identity misconfiguration** (Gartner, as cited in the
  brief). Under the **shared responsibility model** the cloud provider secures the platform; the customer owns
  identities, configuration, sharing and app access — exactly where SMBs are thinnest.
- **The average breach costs $3.31M** (IBM, as cited in the brief).
- **The traditional gap:** an alert emailed at 2:00 AM on a Sunday is first read at 8:00 AM on Monday — the attacker
  has more than a day inside the tenant. WAISentry closes that gap with 24/7 analysts and pre-approved containment.

## Architecture
**Your environment** (Workspace, laptops, on-prem servers, SaaS security tools) → **WAISentry telemetry pipeline**
(API log evaluation and correlation inside the client's Google Cloud tenant; tokenisation) → **Wursta 24/7 SOC**
(certified analysts + Gemini triage). Only tokenised alerts and signals cross from the tenant to the SOC.

## The three phases and their targets
| Phase | What happens | Target (WAISentry brief) |
|---|---|---|
| 1 · AI triage | Gemini scores every event, drops ~99% as normal noise, raises alerts with ATT&CK technique and confidence | 0-15 seconds |
| 2 · Human investigation | A certified Wursta analyst verifies the alert, traces the attack path and blast radius | 1-3 minutes |
| 3 · Coordinated containment | Pre-approved playbooks run, everything else is escalated to the client | under 5 minutes |
| Active containment | The pre-approved actions themselves (session kill, OAuth revoke, suspension, Drive quarantine) | under 60 seconds |

## Options compared (WAISentry brief)
| | Internal 24/7 SOC | Traditional MSSP | WAISentry |
|---|---|---|---|
| Staffing | 5+ FTE, $450k-$600k a year | Customer still staffs level 2/3 | Included |
| Tooling | $60k-$100k a year | $80k-$150k a year ("data taxes") | Included |
| Ramp | 6-9 months | 3-6 months | 48 hours |
| Annual cost | $550k+ | $120k+ plus your own staff | Predictable monthly fee |

WAISentry's fee is quoted by Wursta. **Agents must never estimate a WAISentry price.**

## How the Agent Hive prototypes the service
The WAISentry cluster in the SMB realm demonstrates each stage on synthetic telemetry from the fictional client
Kitewing Software (live on WAISentry since 2026-10-07): AI Triage (Phase 1), WAISentry SOC (the full pipeline),
Identity Threat Detection, OAuth & SaaS Governance, Fleet & Hybrid Monitor, Active Containment (Phase 3), Zero-PII
Tokenizer, Compliance & Cyber-Insurance, and Posture & App Review. In the demo the investigation step **prepares** the
certified analyst's case — in the live service a human analyst verifies it — triage scoring is deterministic and
stands in for Gemini, and every containment action is simulated.

## Kitewing results since go-live (demo data, 2026-10-08 to 2026-11-06)
- 7 incidents: 1 critical consent-phishing / BEC attempt (INC-1101-01, $48,600 at risk, $0 lost, contained 29 seconds
  after analyst confirmation), 1 critical infostealer with a blocked session-hijack attempt (INC-1028-01), 2 high
  (MFA fatigue, on-prem password spray), 3 medium.
- The posture score rose from 20 to 75 between the first review (2026-10-01) and 2026-11-06.
- Daily volumes and noise share are in BigQuery (tables sentry_ingest_daily, sentry_events, sentry_incidents).

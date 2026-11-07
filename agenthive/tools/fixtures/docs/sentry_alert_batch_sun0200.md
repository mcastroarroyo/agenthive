# Telemetry batch TB-1101-0200 — Kitewing Software, Sunday 2026-11-01 01:30-02:30

Synthetic demo document. Export from the WAISentry in-tenant pipeline for the fictional client Kitewing Software
(kitewing.example). Identities are already tokenised (zero-PII): USR- people and mailboxes, EXT- external addresses,
FIL- file names, MSG- message subjects, DEV- laptops. IPs, domains, app names and server names stay in clear.
Times are Kitewing local time (UTC-6).

**Batch id:** TB-1101-0200 · **Raw records in window:** 4,812 · **Events passed to triage:** 47

| Time | Source | Actor | Event |
|---|---|---|---|
| 01:33:12 | workspace.login | USR-D678 | Sign-in from Lisbon, PT (on leave since 2026-10-29), security key, known device |
| 01:37:36 | dnsfilter | DEV-4A1E | Blocked ad/tracker domain pixel-track.example |
| 01:38:21 | mimecast | USR-5DED | Spam from 192.0.2.34 rejected on reputation |
| 01:38:33 | mimecast | USR-E074 | Newsletter delivered from a bulk sender (DMARC pass) |
| 01:40:01 | firewall_ids | MB-FW01 | Inbound port scan from 192.0.2.201 blocked at MB-FW01 |
| 01:40:12 | dnsfilter | DEV-0234 | Blocked ad/tracker domain pixel-track.example |
| 01:46:18 | workspace.login | USR-9BC4 | Sign-in from Cedar Harbor, security key, known device |
| 01:46:52 | mimecast | USR-2E5D | Spam from 192.0.2.34 rejected on reputation |
| 01:48:34 | workspace.login | USR-163D | One wrong password, then success from a known device |
| 01:49:10 | firewall_ids | MB-FW01 | Inbound port scan from 192.0.2.159 blocked at MB-FW01 |
| 01:56:45 | firewall_ids | MB-FW01 | Inbound port scan from 192.0.2.201 blocked at MB-FW01 |
| 01:56:54 | dnsfilter | DEV-D644 | Blocked ad/tracker domain adserve-metrics.example |
| 01:58:02 | mimecast | USR-CFA4 | Delivered 'MSG-AF33' from EXT-58DD (domain 2 days old); URL rewritten by URL Protect; also sent to USR-0E33 and USR-5B90 |
| 01:58:40 | workspace.login | USR-CFA4 | Sign-in from Cedar Harbor (home ISP 203.0.113.61), security key, known device DEV-E7E9 |
| 02:00:19 | syslog.dc | MB-DC01 | Routine Kerberos ticket renewals on MB-DC01 (16 accounts) |
| 02:01:43 | workspace.drive | USR-01C9 | Edited an internal document they own |
| 02:02:19 | workspace.login | USR-B701 | Sign-in from Cedar Harbor, security key, known device |
| 02:03:01 | mimecast | USR-5A39 | Newsletter delivered from a bulk sender (DMARC pass) |
| 02:03:37 | dnsfilter | DEV-E7E9 | Resolved securedoc-viewer.example (registered 2026-10-30, uncategorised at the time — allowed) |
| 02:03:51 | edr | DEV-5A6E | Scheduled EDR scan completed, 0 detections |
| 02:04:11 | workspace.token | USR-CFA4 | Granted 'PDF Secure Viewer' (client 990417-pdfsecureviewer, publisher unverified) scopes gmail.readonly, gmail.settings.sharing, drive |
| 02:05:21 | dnsfilter | DEV-DE37 | Blocked ad/tracker domain adserve-metrics.example |
| 02:05:40 | workspace.gmail | USR-CFA4 | Forwarding address EXT-CBE6 added and filter created by app 'PDF Secure Viewer': subject invoice OR payment OR remittance OR bank OR wire -> forward, skip inbox, mark as read |
| 02:06:12 | workspace.login | USR-CFA4 | Password accepted, security-key challenge failed, from 198.51.100.77 (Amsterdam, NL — AS64501 hosting); previous activity Cedar Harbor 01:58:40 |
| 02:06:58 | workspace.gmail | USR-CFA4 | App 'PDF Secure Viewer' read 412 messages through the Gmail API from 198.51.100.77 |
| 02:07:10 | mimecast | USR-26F5 | 'MSG-92EF' from EXT-D0D2 (lookalike of tessarodesign.example, registered 2026-10-29), reply-to EXT-4805, to the accounts-payable shared mailbox, cc USR-CFA4; delivered with an impersonation banner |
| 02:07:30 | workspace.drive | USR-CFA4 | App 'PDF Secure Viewer' downloaded 38 files from Finance/Vendors including FIL-48E5 |
| 02:07:41 | workspace.drive | USR-CFA4 | App 'PDF Secure Viewer' set 'anyone with the link' on FIL-A3EF and FIL-48E5 |
| 02:08:25 | workspace.gmail | USR-CFA4 | Gmail API call by 'PDF Secure Viewer' from 198.51.100.77 rejected (token revoked by PB-02) — containment verified |
| 02:08:30 | firewall_ids | MB-FW01 | Inbound port scan from 192.0.2.118 blocked at MB-FW01 |
| 02:09:56 | firewall_ids | MB-FW01 | Inbound port scan from 192.0.2.159 blocked at MB-FW01 |
| 02:10:51 | workspace.token | USR-AD7D | Token refresh for sanctioned app Slack |
| 02:10:55 | mimecast | USR-D4D6 | Newsletter delivered from a bulk sender (DMARC pass) |
| 02:11:40 | workspace.login | USR-CC9D | One wrong password, then success from a known device |
| 02:12:36 | dnsfilter | DEV-60B1 | Blocked ad/tracker domain cdn-beacon.example |
| 02:14:10 | workspace.login | USR-8207 | Sign-in from home ISP, security key, known device |
| 02:14:20 | workspace.login | USR-2588 | One wrong password, then success from a known device |
| 02:14:22 | dnsfilter | DEV-A57E | Blocked ad/tracker domain cdn-beacon.example |
| 02:17:42 | syslog.dc | MB-DC01 | Routine Kerberos ticket renewals on MB-DC01 (16 accounts) |
| 02:18:50 | workspace.login | USR-EC4F | Sign-in from home ISP, security key, known device |
| 02:20:54 | mimecast | USR-043F | Newsletter delivered from a bulk sender (DMARC pass) |
| 02:21:43 | mimecast | USR-8645 | Spam from 192.0.2.159 rejected on reputation |
| 02:24:08 | workspace.token | USR-D4D6 | Token refresh for sanctioned app Slack |
| 02:28:41 | mimecast | USR-6FE4 | Newsletter delivered from a bulk sender (DMARC pass) |
| 02:29:03 | syslog.dc | MB-DC01 | Routine Kerberos ticket renewals on MB-DC01 (15 accounts) |
| 02:29:32 | syslog.dc | MB-DC01 | Routine Kerberos ticket renewals on MB-DC01 (6 accounts) |
| 02:29:36 | workspace.login | USR-D39D | Sign-in from home ISP, security key, known device |

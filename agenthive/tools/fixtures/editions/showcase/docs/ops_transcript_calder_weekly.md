# Calder & Finch Insurance · Claims Assistant · Weekly Sync (transcript)

Meeting id: MTG-2026-1103-CFI · Google Meet · Tuesday 2026-11-03, 14:00-14:28 (US Eastern)
Account: Calder & Finch Insurance (ACC-1017) — fictional regional property & casualty insurer
Engagement: Claims triage assistant, phase 2 (SOW-CFI-04) — Gemini on Vertex AI + Document AI + BigQuery
Attendees — Sablewood: Ethan Brooks (Project Manager), Priya Nair (Solution Architect), Leah Brandt (Customer Success Manager)
Attendees — Calder & Finch: Rosa Delgado (Claims Director, executive sponsor), Arjun Mehta (Enterprise Architect),
Claire Beaumont (Claims Operations Lead)

---

[00:00] Ethan Brooks: Afternoon all. Short agenda: phase 2 progress, the adjuster pilot results, and the plan for the December release.

[00:35] Rosa Delgado: Before we start — great work on the pilot. The adjusters in the Hartwell office are asking when everyone else gets it.

[01:20] Priya Nair: Thank you. Phase 2 is ahead of schedule. Water-damage and auto-glass claim types are live in the pilot; the triage assistant classifies the first notice of loss, extracts policy number, loss date and location, and drafts the routing note for the adjuster.

[03:05] Claire Beaumont: The numbers are good. Median triage time on pilot claims went from 26 minutes to 15. Adjusters accept the suggested routing about 87 percent of the time, and when they don't, they leave a reason, which is helpful.

[05:10] Arjun Mehta: From architecture, the human-review step and the PII redaction before prompts passed our internal security review last week. One question: can we keep the model and the documents in the US region only?

[05:45] Priya Nair: Yes — everything is pinned to a US region today, and the design document records it. I'll add the data-residency statement to the release notes.

[07:30] Rosa Delgado: For December, I'd like to add the property-inspection photo summary we discussed. Is that in the current scope?

[08:05] Ethan Brooks: It's listed as optional item 4.3 in the SOW, so it's already in scope as long as we confirm by November 13th. The effort is in the plan.

[08:40] Rosa Delgado: Then let's confirm it now.

[09:15] Ethan Brooks: Decision recorded: property-inspection photo summaries are in for the December release.

[11:00] Leah Brandt: Adoption: 42 of 45 pilot adjusters used the assistant this week. We'd like to run a short feedback survey before the wider rollout.

[11:40] Claire Beaumont: Happy to support. I'll send the survey to the adjusters by Friday.

[13:20] Ethan Brooks: Action items. Priya adds the data-residency statement to the release notes by November 10th. Claire sends the adjuster survey by Friday. I'll update the release plan with the photo-summary feature by November 9th. Arjun shares the security review sign-off document by November 6th.

[15:00] Rosa Delgado: Perfect. Honestly this is one of the smoothest projects we've had. Let's keep this cadence.

[16:10] Arjun Mehta: Agreed.

[27:50] Ethan Brooks: Thanks everyone — see you next Tuesday.

[End of transcript — 28 minutes]

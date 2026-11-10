# Tallbridge Logistics · Project Lighthouse · Steering Committee #6 (transcript)

Meeting id: MTG-2026-1104-TBL · Google Meet · Wednesday 2026-11-04, 10:00-10:41 (US Central)
Account: Tallbridge Logistics (ACC-1042) — fictional mid-market third-party logistics provider
Engagement: Project Lighthouse — BigQuery operations data platform + Gemini Enterprise rollout (SOW-TBL-02)
Attendees — Sablewood: Dana Whitfield (Project Manager), Marco Ruiz (Engagement Lead), Priya Nair (Solution Architect),
Tomás Ibarra (Data Engineer), Leah Brandt (Customer Success Manager)
Attendees — Tallbridge: Owen Castillo (Director of IT), Farah Haddad (Head of Customer Operations),
Victor Lindqvist (Finance Controller)
Invited, did not attend: Helen Marsh (VP Operations, executive sponsor) — sent apologies; Grace Okafor (Sablewood Account Executive)

---

[00:00] Dana Whitfield: Good morning everyone, thanks for joining steering committee number six. Quick note before we start: Helen sent apologies again, she's busy with peak-season planning and asked to reschedule her one-on-one with Marco to later in the month.

[00:41] Owen Castillo: Yeah, she's swamped. Let's just go, I have a hard stop at quarter to.

[01:10] Dana Whitfield: Sure. Status first. The TMS ingestion pipeline is about eighty percent done — shipments, stops and carrier events are landing in BigQuery every fifteen minutes. The carrier telematics feed is still blocked: we've been waiting on the telematics provider to countersign the data-sharing agreement since October 20th.

[02:35] Tomás Ibarra: To add to that — without the telematics feed we can't compute dwell time at customer sites, which is one of the three tiles on the on-time delivery dashboard.

[03:20] Owen Castillo: So what's the new date for the dashboard?

[03:31] Dana Whitfield: Realistically, if the agreement is signed next week, December 6th for version one.

[04:30] Owen Castillo: Honestly, I'm frustrated. This is the second time the dashboard date has slipped. My team was promised the on-time delivery dashboard by November 15th, and now you're telling me December? That's not acceptable to our ops leadership. I'm the one who has to explain this.

[05:12] Marco Ruiz: That's fair, Owen, and I'm sorry we're here again. The dependency on the telematics provider was flagged in the risk log in September, but we should have escalated it harder and earlier on our side.

[06:00] Priya Nair: There's a way to de-risk this. We can build the dashboard against a sample telematics extract — a CSV export your team can pull manually from the provider's portal — so the remaining work isn't sitting behind the agreement. When the API is enabled we swap the source.

[06:48] Owen Castillo: Fine, do that. But I'm disappointed we're only talking about workarounds now.

[07:30] Farah Haddad: Can I raise something? While you're at it, can we also add the customs brokerage data to the platform? Our customs team keeps asking for clearance times. It's one more thing but it should be small — it's just one more source.

[08:45] Marco Ruiz: I want to be careful here. Customs brokerage data is out of scope of SOW-TBL-02 — it's a new source system with its own data model. We'd need a change request with an estimate.

[09:30] Farah Haddad: Can we include it without a CR? Helen would expect it to be part of the platform. It's additional value for the same project.

[10:05] Dana Whitfield: Let us write it up as a change request so you can see the effort and the impact on the timeline before anyone decides. We won't start work on it until it's approved.

[10:40] Farah Haddad: Okay. Not thrilled, but okay.

[12:00] Leah Brandt: On the Gemini Enterprise rollout: 120 of the 300 seats are activated and weekly active usage is 38 percent. Attendance at the training sessions has been low — the feedback we get is that people have no time for training right now and it's not a priority during peak season.

[13:10] Farah Haddad: That's true for my team. Ninety-minute sessions are impossible for dispatchers. Whatever you can do in twenty minutes, they might attend.

[13:45] Leah Brandt: Then we switch to twenty-minute micro-sessions, recorded, with one use case each — dispatch email drafting, exception summaries, carrier follow-ups.

[15:00] Victor Lindqvist: One more topic from finance. We're concerned about the time-and-materials hours on the October invoice, INV-7781. There are about 60 more hours than the forecast we were given. If we can't reconcile that, I'll need to escalate to Helen.

[16:05] Dana Whitfield: Understood. I'll sit down with you and Grace and walk through the timesheets line by line.

[18:00] Marco Ruiz: Let me summarise the decisions so far. One: we build the on-time delivery dashboard on a sample telematics extract to unblock the work, with a target of December 6th for version one. Two: customs brokerage data goes through change request CR-03 — evaluation only, no work until approved. Three: Gemini training moves to twenty-minute recorded micro-sessions.

[19:20] Owen Castillo: Agreed on all three.

[22:00] Dana Whitfield: Action items. I'll send the revised plan with recovery dates by Friday.

[22:30] Owen Castillo: I'll escalate the data-sharing agreement with the telematics provider's account manager by Monday the 9th.

[23:05] Tomás Ibarra: I'll build the dashboard tiles on the sample extract and demo them by November 20th.

[23:40] Marco Ruiz: I'll draft CR-03 for the customs data with an estimate by November 11th.

[24:15] Leah Brandt: I'll schedule three micro-trainings before November 25th.

[24:50] Dana Whitfield: Grace and I will reconcile the October invoice hours with Victor by November 10th.

[25:20] Priya Nair: I'll run data-quality checks on the TMS feed — duplicates and late carrier events — by November 13th.

[30:00] Owen Castillo: Look, I'll be direct. We need to see real progress before the QBR on December 2nd. Otherwise I can't defend renewing the managed-services retainer next year. We're behind and the deadline for our budget is the QBR.

[31:15] Marco Ruiz: Heard. We'll make sure you walk into the QBR with a working dashboard on real data and adoption numbers moving up.

[33:40] Victor Lindqvist: And please, fewer surprises on invoices.

[38:00] Dana Whitfield: Next steering committee is November 18th. I'll ask Helen's assistant to hold the slot. Thanks everyone.

[40:30] Owen Castillo: Thanks. Talk soon.

[End of transcript — 41 minutes]

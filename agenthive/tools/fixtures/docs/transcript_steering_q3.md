# Transcript — Brightwater Distribution: Order Management Modernisation, Q3 Steering Committee

**Date:** 2026-09-24, 15:00–15:40 (video call, recorded with consent) · **Synthetic example — all names fictional**

**Attendees**
- Gregory Haines — VP Operations, Brightwater Distribution (executive sponsor)
- Wendy Cho — PMO Lead, Brightwater
- Raj Iyer — IT Director, Brightwater
- Carla Dominguez — Customer Service Manager, Brightwater
- Ana Torres — Engagement Manager, Wursta
- Diego Salas — Lead Cloud Architect, Wursta

---

**[00:00] Ana Torres:** Thanks, everyone. Agenda: status against plan, the warehouse integration, UAT readiness, and two requests that came in this week. Then decisions and actions.

**[00:41] Ana Torres:** Headline first. Order capture, pricing and the customer portal are built and passing system tests. The warehouse management integration is not. We are **blocked** — we have been **waiting on** the WMS vendor's API credentials for the production sandbox since August 28. Because of that, UAT cannot start on October 5 as planned. Our current estimate is a **three-week slip** for UAT, which puts the December 7 go-live at risk.

**[01:35] Gregory Haines:** Three weeks. We had a slip in June as well. So we are behind **again?** I'll be honest, I'm **frustrated**. I told the board in July that December was solid.

**[01:58] Ana Torres:** I understand. The June slip was ours — the pricing rules were underestimated. This one is on the critical path through an external dependency, and we flagged it as a risk in August.

**[02:20] Gregory Haines:** Flagging it in a status report isn't the same as fixing it. Raj, why don't we have those credentials?

**[02:31] Raj Iyer:** The vendor says their security review needs a signed data-sharing addendum. Legal has it. I've chased twice. Honestly my team is **busy** with the ERP patching this month, so it hasn't had the attention it needs.

**[02:58] Gregory Haines:** That's **unacceptable**. If this is sitting in Legal, I'll **escalate** it to our general counsel today. What date do you need it by?

**[03:12] Diego Salas:** If we have credentials by October 1, we can finish integration testing in about two weeks, and UAT can start October 19. Every week after that moves go-live by a week. There's also a fallback: we can build against a mock of the WMS API now so the order flows are ready, but we can't certify stock reservations without the real system.

**[03:49] Wendy Cho:** Let's do the mock regardless. I don't want to lose another week.

**[04:05] Ana Torres:** Agreed. Next, UAT readiness. Carla, we asked for four named testers from Customer Service for three weeks.

**[04:18] Carla Dominguez:** Yes, about that. We have **no time** in October — it's our peak season. Could we **skip** the full UAT and do a shorter one **later**, maybe after go-live? Training is **not a priority** for my team right now either.

**[04:44] Ana Torres:** I'd strongly advise against skipping UAT. Customer Service are the main users; if they haven't tested the order screens, the first week after go-live will be painful. We could reduce it to two weeks with half-days.

**[05:06] Carla Dominguez:** **Whatever** works, as long as it's not four full-timers. Can we **reschedule** the training sessions to November?

**[05:20] Gregory Haines:** Carla, I hear you, but I'm **not happy** that we'd go live with a system the main users haven't tried. Find me three people for half-days. That's a decision.

**[05:42] Ana Torres:** Thank you. Now the two requests. First, from Wendy's email: EDI order intake for our two largest customers.

**[05:55] Wendy Cho:** Right. **One more thing** I want to be clear on — the two big accounts send orders by EDI and today someone re-keys them. **Can we include** EDI in the December release? It feels like it should have been there from the start.

**[06:17] Diego Salas:** EDI was explicitly **out of scope** in the SOW — section 4.2 lists it under future phases. It's a meaningful piece: mapping two partners' message formats, testing with their IT teams, monitoring. Roughly 20 to 25 working days.

**[06:40] Wendy Cho:** And **while you're at it**, the returns portal — customers keep asking for self-service returns. Could you **also add** that?

**[06:52] Ana Torres:** Both are good ideas. Both are **additional** scope. If we put them into December, December is gone. My proposal: we raise a change request for EDI with an estimate and a separate date, and put the returns portal on the phase-two backlog.

**[07:15] Gregory Haines:** I'm **concerned** we're having this conversation in September. I'm **disappointed** nobody raised EDI in discovery.

**[07:30] Wendy Cho:** To be fair, it was raised — it was parked.

**[07:36] Gregory Haines:** Fine. Change request for EDI, with cost and dates. I'll decide when I see it. Returns portal is phase two. Now, I need a date I can take to the board. Not three options. One date, with what you need from us to hit it.

**[08:02] Ana Torres:** Understood. We will bring a re-baselined plan with the critical path, the client-side dependencies and a confidence level. Is September 30 acceptable?

**[08:15] Gregory Haines:** September 30. And going forward I want a weekly fifteen-minute call with me until we're back on track. I can't keep learning about a **delay** at the steering committee.

**[08:31] Raj Iyer:** One more risk while we're here: the **deadline** for the ERP security patching is October 15. If my team is stuck on that, they can't support the cutover rehearsal in November.

**[08:47] Diego Salas:** Then we should schedule the rehearsal for the week of November 16 and confirm your team's availability now, not in November.

**[09:02] Raj Iyer:** Let me check and come back by Friday.

**[09:10] Ana Torres:** Let me read back decisions and actions.

**[09:14] Ana Torres:** Decisions: one, UAT will happen before go-live — three Customer Service testers at half-days, two weeks. Two, EDI goes through a change request; the returns portal moves to the phase-two backlog. Three, a weekly sponsor call starts next week.

**[09:38] Ana Torres:** Actions. Gregory escalates the WMS data-sharing addendum to general counsel, today. Raj obtains the WMS API credentials by **October 1**. Diego builds the WMS mock and an integration test plan by **September 30**. Ana delivers the re-baselined plan with critical path and confidence level by **September 30**. Wendy submits the EDI change request with business justification by **October 3**; Wursta returns the estimate by **October 8**. Carla names three UAT testers by **September 29** and proposes training dates in November. Raj confirms IT availability for the cutover rehearsal by **September 26**. Ana sets up the weekly sponsor call starting **October 1**.

**[10:32] Gregory Haines:** Good. Next steering committee October 15. I expect to see a plan I can believe.

**[10:40] Ana Torres:** You will. Thanks, everyone.

*[Recording ends 10:44]*

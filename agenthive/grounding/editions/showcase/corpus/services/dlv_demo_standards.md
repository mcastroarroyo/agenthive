# Demo Script Standards (solution demos)

**Owner:** Pre-sales engineering (Sablewood) · **Version:** 1.4 · **Last reviewed:** 2026-10-12 · **Status:** current
Synthetic demo document.

## 1. What a good demo does
A demo is a story about the prospect's problem that happens to use our solution. The audience should leave believing
one to three specific things (for example "the migration is planned from data", "users are looked after", "I will see
status every morning"). Everything in the script serves those beliefs.

## 2. Structure
1. **Audience and goal** — who is in the room, what each person worries about, what they must leave believing.
2. **Storyline in three acts** — problem (their world today), proof (the solution working live on realistic data),
   outcome (what changes for them, with a KPI).
3. **Run-of-show** — a table of segments with minutes and a type: intro, context, live_demo, story, qa, close.
4. **Click path** — numbered steps: which demo moment, the exact input to paste, what to point at in the result.
5. **Talk track** — two or three sentences per segment and one "wow" moment.
6. **Fallback plan** — for every live segment: a recorded run, a screenshot or a cached answer.
7. **Disclaimer** — the data is synthetic and named actions (emails, change orders, retries) are simulated.

## 3. Timing rules (checked automatically)
- Leave at least **10%** of the slot unallocated as buffer.
- Live demo at least **40%** of planned time.
- Intro and context together at most **20%**.
- At least **4 minutes** of Q&A.
- No talk segment (intro, context, story) longer than **6 minutes** without an interaction.
- Every live_demo segment names its fallback.

Example for a 25-minute slot: context 3, live demos 5 + 5 + 4, story 2, Q&A 4 = 23 minutes — fails the buffer rule
(2 minutes is 8%). Cut one live segment to 3 minutes to pass.

## 4. Using the demo environment
- Use each solution's tested demo moments — their inputs are tested against the demo data. Free-form inputs must be
  marked as such in the click path and rehearsed.
- For technical audiences, name the building blocks once (Gemini model, the Google Cloud runtime, the tools and the
  knowledge base); mention the model tier when cost matters to the audience.
- For multi-step solutions, point at the steps as they run (pipeline stages, parallel specialists, draft and critique).
- Never show a real client name or real data; the Workspace Migration Factory demo runs on the fictional Kestrel
  Manufacturing tenant.

## 5. Audience patterns
- **CIO:** risk, timeline, cost, visibility. Show the go/no-go brief and the status report.
- **IT director:** permissions, long paths, mobile devices, rollback. Show the pre-flight blockers and validation.
- **HR / change owner:** adoption, frontline staff, language. Show personalised comms and the adoption plan.
- **COO / business owner:** outcomes and speed. Show the working prototype or the measured result first.
- **CISO / AI governance:** data leakage and audit. Show the redacted prompt and the verdict log.

## 6. Rehearsal and fallback
- Rehearse the full click path the day before on the same network setup.
- Keep a tab with each fallback ready; switch without apologising — "here is a run from this morning".
- If the prospect's bandwidth is poor, drive from the presenter's machine and share a single window.

## 7. After the demo
Send the script's outcome slide and the KPIs within 24 hours, with a proposed next step (discovery workshop or
pilot scope).

# Verdant Agro Cooperative · Farmer Advisory Assistant · Design Workshop Notes

Meeting id: MTG-2026-1030-VAC · In person + Google Meet · Friday 2026-10-30, 09:00-12:00
Account: Verdant Agro Cooperative (ACC-1088) — fictional agricultural cooperative with 14,000 member farmers
Engagement: WhatsApp farmer advisory assistant, phase 1 (SOW-VAC-01)
Wursta: Sam Oduya (Project Manager), Priya Nair (Solution Architect), Lucía Ferrer (Conversation Designer)
Verdant: Joaquín Reyes (General Manager, sponsor), Amara Nwosu (Agronomy Lead), Ben Hollis (IT Coordinator)

## Context
- Goal: members ask crop, weather-alert and input-pricing questions on WhatsApp and get answers grounded in the
  cooperative's agronomy bulletins.
- Phase 1 covers maize and coffee; dairy is a later phase.

## Decisions
- Spanish and English at launch; the assistant answers in the language of the question.
- Agronomy bulletins are the only source for crop advice — no open-web answers on pesticide dosage.
- Escalation to a human agronomist when the assistant's confidence is low or the member reports crop disease.
- Pilot group: 300 members from two districts (Valle Alto and San Isidro).

## Action items
- Amara Nwosu: send the 2025-2026 agronomy bulletins (PDF) and mark any that are outdated — by 2026-11-06.
- Ben Hollis: confirm the WhatsApp Business number and verification status — by next Wednesday.
- Lucía Ferrer: draft the conversation flows for weather alerts and price queries — by 2026-11-10.
- Priya Nair: write the grounding and escalation design (Vertex AI Search data store + handoff) — by 2026-11-12.
- Sam Oduya: send the pilot plan and member-consent text for legal review — by end of next week.
- Joaquín Reyes: nominate two district coordinators for pilot feedback — TBD.

## Open questions
- Can input prices be refreshed daily from the cooperative's ERP, or only weekly?
- Who approves new bulletins before they are indexed?

## Risks
- Bulletins are partly scanned images; OCR quality may be low for tables.
- Member consent for message storage must be captured before the pilot starts.

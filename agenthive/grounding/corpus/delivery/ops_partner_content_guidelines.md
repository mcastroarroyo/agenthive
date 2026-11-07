# Partner Content Curation Guidelines

**Owner:** Partner Operations · **Last reviewed:** 2026-10-09 · **Status:** current
Synthetic demo document — describes how Wursta curates partner enablement material for teams and for AI search.

## 1. Why curate
Partner portals publish a steady stream of playbooks, decks, recordings and programme guides. Unfiltered, they bury the
useful material and leak confidential content into broad search. Cataloger reviews every weekly batch, grades it for
AI-ingestion readiness, tags it and sends each team a short digest of what matters to them.

## 2. AI-ingestion readiness score (0-100)
Every item starts at 100 and loses points for issues that make it hard to index or risky to share:
| Issue | Penalty | Fix |
|---|---|---|
| Scanned PDF or image | −35 | OCR first (ocr-document-text skill) |
| No text layer | −20 | OCR or a written description |
| Longer than 80 pages | −15 | split by chapter before indexing |
| Partner-confidential | −30 | restrict ACLs before indexing |
| Older than 12 months | −10 | check for a newer edition |
Verdicts: **ingest** (70 or more), **fix first** (40-69), **exclude** (below 40). Videos and recordings have no text
layer — send them to Janus for a transcript and knowledge record before indexing.

## 3. Tagging taxonomy
- **Product:** the main product or programme (e.g. Gemini Enterprise, Google Workspace, BigQuery, Vertex AI Agent
  Engine, Customer Engagement Suite, Partner programme).
- **Audience:** sales, presales, delivery, marketing, leadership, partner operations, legal.
- **Motion:** **sell** (positioning, pricing, plays), **build** (technical enablement, labs, architectures) or
  **service** (methodology, adoption, operations).
- **AI readiness:** the verdict above.
- **Sensitivity:** public, partner-internal, partner-confidential.

## 4. Confidential material
Partner-confidential items (incentive matrices, programme guides marked confidential, competitive positioning) are
**never** added to the company-wide index. Index them, if at all, in a restricted collection for the named audience
(for example sales leadership and the deal desk). Legal records such as signed agreements go to the legal repository,
not the enablement index.

## 5. Stale material
Anything older than 12 months is checked for a newer edition before indexing. Pricing documents older than 12 months
are excluded from AI answers entirely — prices must always come from the current official pricing page.

## 6. Filing in Drive
Use the shared drive "Partner Advantage" with folders **<fiscal year> / <product> / <motion>**. Duplicate copies and
"(1)" files are removed; older editions move to "99 Archive". The drive-organization skill proposes moves as a dry run;
a human approves them.

## 7. Team digests
Each week, one digest per team in its Google Chat space:
1. **New and ready** — up to 5 items with one line each on why it matters to that team.
2. **Key takeaways** — 3 bullets per item, written for the audience (sales: plays and qualifying signals; presales:
   demo and positioning; delivery: methods and labs).
3. **Restricted** — confidential items the team can request access to.
4. **Not indexed** — what was excluded and why.
Keep each digest under 300 words and link to the catalogue for detail.

## 8. Ownership
Partner Operations owns the catalogue; each practice lead nominates a reviewer who checks the weekly digest for their
team. Items stay in the catalogue for 18 months unless superseded.

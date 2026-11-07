# Knowledge Management Policy

**Owner:** Grace Achterberg, Knowledge Manager · **Last reviewed:** 2026-01-15 · **Status:** current

## Purpose

Make sure that when a consultant, or an agent such as the Context Librarian, finds an answer in Wursta's knowledge
base, the answer is current, owned and traceable to a source.

## Scope

All internal playbooks, runbooks, standards, policies, templates and reference notes indexed in the knowledge base
for any Agent Hive realm. Client deliverables and client confidential material are **out of scope** and must not be
indexed in shared knowledge bases.

## Principles

1. **Every document has exactly one named owner** — a person, not a team or a distribution list.
2. **Every document is reviewed at least every 12 months.** Reviewing means reading it, confirming or fixing it, and
   updating the review date — not just changing the date.
3. **One source of truth per topic.** When a new document replaces an old one, the old one is marked superseded and
   points to its replacement.
4. **Citations are mandatory.** Agent answers quote the document title for every fact taken from the knowledge base.

## Document header

The first line of every document is its title (`# Title`), and it must match the title in the knowledge-source
registry exactly. Directly below the title: owner, last reviewed date, status and, if applicable, "Supersedes" or
"Superseded by".

## Status lifecycle

| Status | Meaning | What the Context Librarian does |
|---|---|---|
| draft | Being written; not indexed | Not visible |
| current | Owned and reviewed within 12 months | Answers from it normally |
| stale | Not reviewed for more than 12 months | Answers, but warns the user and suggests the owner |
| ownerless | Owner left or moved and nobody has taken over | Answers, warns, and reports it for reassignment |
| superseded | Replaced by a newer document | Points the user to the replacement |
| archived | Kept for record only; removed from the index | Not visible |

The freshness check (`check_document_freshness`) treats a document as stale when it has not been reviewed for more
than 365 days **or** has no owner, and as superseded when the registry names a replacement.

## Resolving conflicts between documents

When two documents disagree, the authoritative one is, in this order:

1. the one that is **not superseded**;
2. the one with a **named owner**;
3. the one **reviewed most recently**;
4. if still tied, the one approved by the practice lead for that topic.

The Context Librarian explains which source it used and why, and the conflict is reported to both owners.

## Ownership changes

- When an owner leaves or changes role, their manager reassigns their documents before the move is complete.
- Ownerless documents are reassigned by the Knowledge Manager **within 30 days**; if no owner is found, the document is
  archived.
- An owner may delegate edits but not accountability.

## Review cadence and reporting

- Owners receive a reminder 30 days before a document turns stale.
- The Knowledge Manager publishes a **monthly curation report**: stale documents, ownerless documents, superseded
  documents still receiving traffic, and the top unanswered questions from the Context Librarian logs.
- Practice leads review the report for their area in their monthly practice meeting.

## Writing guidelines

- Write for someone who has 2 minutes: purpose first, then the steps or rules, then the rationale.
- Prefer numbered steps and tables to long paragraphs; they retrieve and quote better.
- Name roles rather than people inside procedures (people change; the owner field holds the person).
- State numbers explicitly (durations, thresholds, scales) so agents can quote them exactly.
- Describe client work generically ("regional insurer", "city government"); never name clients without written
  permission.

## What never goes into the knowledge base

Personal data, credentials, project identifiers, client confidential information, partner-confidential material
without an access-control decision, and unreviewed AI-generated content.

## Measuring success

Percentage of answers with citations, number of stale and ownerless documents (target: zero ownerless, under 5%
stale), median time to fix a reported conflict, and time-to-answer for policy questions.

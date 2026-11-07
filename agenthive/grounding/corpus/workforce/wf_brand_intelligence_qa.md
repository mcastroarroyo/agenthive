# Brand Intelligence and QA standards

Owner: Wursta Agent Workforce product team. Last reviewed 2026-11-01. Prototype documentation for the Wursta Agent Hive.

## Brand Intelligence

Customers upload their brand guidelines, logo and templates once. Brand Intelligence learns a **brand profile** and every specialist and the Document Studio apply it to every deliverable.

What the profile captures:

| Element | Examples | Used by |
|---|---|---|
| Fonts | Heading and body fonts with fallbacks and sizes | Document Studio (titles, headings, body, slides, sheets) |
| Colours | Primary, accent, secondary, text and background hex codes and where each may be used | Document Studio (title pages, rules, table headers, banding) |
| Logo usage | Wordmark, clear space, minimum size, placement | Document Studio |
| Tone of voice | Tone words, "we are / we are not" | Specialists while writing |
| Writing rules | Sentence length, heading case, spelling (e.g. US English), punctuation, emojis | Specialists, brand check |
| Words to avoid | Banned words with plain replacements | Specialists, brand check |
| Product names | Exact spelling and first-mention rules, wrong forms | Specialists, brand check |
| Customer naming and claims | Customers approved for public use, anonymised-only customers, names that may never appear, prospects, competitors, the claims policy | Specialists, brand check, QA |
| Approved facts and boilerplate | Company facts, approved customer results, "About" paragraph, spokespeople, media contact | Specialists, QA fact-check |

Each profile has a deterministic brand id (for example BRD-91CFB7 for the demo customer Kitewing Software). Re-uploading the same guidelines updates the stored profile instead of creating a new one. When a customer has no guidelines, the Agent Workforce house style is used.

## The brand check (rule-based)

The brand check is deterministic — the same draft always gets the same result:

- **Blocking:** banned words, wrong product names, names that may never appear, anonymised-only customers named, prospects named in public content, result numbers without an approved named customer or a "customer-reported" label, too many hashtags in a social post.
- **Warnings:** competitor names in public content, exclamation marks and emojis over the limit, spelling that breaks the brand's rule, title-case headings, all-caps words, long sentences or a high average sentence length.
- **Pass:** no blocking issues and a score of 80 or more.

Audience matters: in a client proposal addressed to a prospect, naming that prospect is fine; in public content it is blocking.

## QA & fact-check standard

Every deliverable passes QA before it reaches the customer:

1. **Brief coverage** — every requirement in the brief is met: deliverable, audience, length, sections, call to action, deadline-sensitive dates.
2. **Brand** — the rule-based brand check passes (no blocking issues, score 80+).
3. **Facts** — every claim is classified: matches the approved facts, contradicts them, uses a restricted name, is unverified (about the company but not approved), or is a public fact to verify with Google Search. Contradictions and restricted names are always fixed; public facts are verified and cited, or removed.
4. **Numbers** — prices, dates and figures are exactly as given in the brief or the approved facts; estimates are labelled as estimates.
5. **Corrected version** — QA returns the issues table and the full corrected deliverable, ready for Document Studio.

Severity: **Critical** (wrong fact, restricted name, wrong price) blocks delivery; **Major** (brand blocking issue, missing section) must be fixed; **Minor** (style warning) is fixed when cheap.

## Revision workflow

- Customers ask for changes in plain English ("shorter executive summary", "add a slide on risks").
- The change goes to the specialist when the content must be rewritten, or straight to Document Studio for layout and wording edits.
- QA re-checks only what changed.
- Each revision is a new version of the file (v2, v3, …); earlier versions stay available.

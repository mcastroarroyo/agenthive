# Agent Forge Connector Playbook — Reuse, Research, Build and Register

**Owner:** Lena Fischer, Lead Builder · **Last reviewed:** 2026-10-28 · **Status:** current

## Why connectors matter

A connector is a reusable, authenticated API client that any forge agent can attach. Building it once means every
later agent — for the same client or a different one — starts from a working integration. Connectors compound: the
second agent on a stack is much faster than the first.

## Official and custom connectors

**Official connectors** ship with the forge template and are maintained by the platform team: Shopify Admin,
Salesforce, QuickBooks Online, Gmail, Google Drive, Google Sheets, Google Calendar, Google Slides, Google Docs, a
generic REST client and any vendor MCP server. Google Workspace connectors act as the signed-in user through OAuth,
so they need no secrets and see only what that user can see.

**Custom connectors** are researched and built by the forge from documentation the builder uploads or links, or from
the vendor's public API docs. Examples: Tekmetric (auto-shop management), Affinity CRM, Aviationstack (flight data)
and Asset Panda (asset tracking).

## Step 1 — reuse first

Search the registry before building anything. If a ready connector covers the operations the agent needs, attach it.
If it covers most of them, the gap is a **connector_modify** job (a new minor version), not a new connector.

## Step 2 — research the API

- Prefer the vendor's official documentation; cite the pages used.
- Capture: base URL (production and sandbox), authentication (type, header or parameter, how keys are issued),
  the endpoints the agent needs (method, path, purpose), pagination, rate limits, error format and webhooks.
- When **no public docs exist** (some HCM and payroll vendors), the connector stays a **draft** until the vendor
  shares documentation or a sandbox. Never guess endpoints from forum posts.

## Step 3 — write the connector spec

| Field | Rule |
|---|---|
| base_url | https only |
| auth | type (api_key_header, api_key_query, bearer, basic, oauth2_client_credentials, oauth2_authorization_code, oauth_user, none), header or parameter, secret NAMES |
| endpoints | only what agents need; write endpoints are flagged and run as dry runs in sandbox |
| pagination | style (cursor, page, offset, link_header, none) and parameters; always read to the last page or a declared cap |
| rate_limit | the documented limit; client-side throttle below it |
| errors | retry 429 and 5xx with exponential backoff, honour Retry-After, never retry 4xx validation errors |
| test_calls | at least two: one read, one error case (for example an unknown id returning 404) |

Prefer header-based keys over query-string keys: keys in URLs leak into logs.

## Step 4 — validate and register

Validate the spec, fix every error, then register it for the client it is first built for. A connector is **ready
(sandbox)** when its secrets are set in that client's test pane and the test calls pass; otherwise it stays a draft
with the missing secret named. Registration is recorded as a connector (or connector_modify) job.

## Versioning

Connectors follow semantic versions. Agents pin a minor version (standard FS-04). When a vendor changes its API — for
example a field is removed from a newer API version — the connector gets a new version with a changelog entry, and
each agent moves to it through its own modify job and full test run. Unpinned agents silently pick up such changes,
which is how a value can start writing as 0 in a report.

## Secrets

Secrets are always names. Builders put values in the test pane for a session and client admins put them in Secret
Manager for production. Values never go into specs, prompts, chat, code or logs.

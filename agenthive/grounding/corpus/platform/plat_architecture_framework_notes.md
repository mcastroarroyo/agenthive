# Google Cloud Architecture Framework — Wursta Field Notes

**Owner:** Daniel Okafor, Principal Architect · **Last reviewed:** 2025-09-18 · **Status:** stale — due for review

> These are Wursta's own field notes on how we apply Google's Architecture Framework in client designs, written in
> our words. They are not a copy of the framework. Google updates the framework's structure and guidance over time:
> always check the current version on Google's documentation site before quoting a pillar or recommendation.

## How we use the framework

Every architecture we propose (Daedalus does this automatically) justifies each service against at least one
pillar, and lists the alternatives we rejected. Design reviews walk the pillars in the order below, and each pillar
gets a short verdict: meets, meets with conditions, or gap.

At our last review the framework was organised around a system-design foundation plus pillars for operational
excellence; security, privacy and compliance; reliability; cost optimisation; and performance optimisation.
Google has also been publishing cross-pillar perspectives (for example for AI and machine-learning workloads and for
specific industries). Verify the current list before a client presentation.

## System design foundation

What we look for: clear requirements (users, volumes, latency, data residency, recovery objectives), managed
services by default, loose coupling between components, and decisions recorded as architecture decision records.

Questions we ask: What happens at ten times today's volume? Which component is hardest to change later? Which
requirement is actually a constraint, and which is a preference?

Anti-patterns: lifting a data-centre design unchanged; one giant project for every environment; no written
non-functional requirements.

## Operational excellence

What we look for: infrastructure as code, CI/CD with automated tests, observability from day one (logs, metrics,
traces, dashboards, alerts with owners), runbooks and blameless post-incident reviews.

Typical services: Cloud Build, Artifact Registry, Cloud Logging and Monitoring, Cloud Trace, Infrastructure Manager
or Terraform.

Anti-patterns: console-only changes in production; alerts that nobody owns; no rollback path.

## Security, privacy and compliance

What we look for: a solid resource hierarchy with organisation policies; least-privilege IAM with groups, not
individuals; no long-lived service-account keys; encryption with customer-managed keys where the regulator expects
it; perimeters (VPC Service Controls) for sensitive data; data classification and DLP; audit logs retained to
policy; supply-chain controls for containers.

For AI workloads we add: grounding only on approved sources, input/output screening, human review for consequential
decisions, and no customer data used for model training without explicit agreement.

Anti-patterns: owner role granted to people; personal data in logs or prompts by default; secrets in environment
files.

## Reliability

What we look for: recovery objectives agreed with the business per workload; regional or multi-zonal deployment
matching those objectives; health checks and autoscaling; graceful degradation (for example, an agent answering "I
can't reach that system right now" instead of failing); backups tested by restoring them; load and chaos tests for
critical paths.

Anti-patterns: a single zone for a "critical" system; backups never restored; retries without back-off.

## Cost optimisation

What we look for: an owner for every project's spend; budgets and alerts; labels for chargeback; serverless and
autoscaling to match demand; committed-use or edition commitments only after usage stabilises; BigQuery partitioning
and clustering; the cheapest model tier that does the job (Model Tier Policy).

How we estimate: a first-pass monthly estimate from our illustrative price sheet (the `estimate_gcp_monthly_cost`
tool), always followed by the official pricing calculator before anything is quoted to a client.

Anti-patterns: sizing for peak all year; unpartitioned fact tables queried with SELECT *; Argon used for routing.

## Performance optimisation

What we look for: measured latency budgets per user journey; caching at the edge and in the application; the right
data store for the access pattern (Firestore or Spanner for operational, BigQuery for analytics, AlloyDB or Cloud
SQL for relational); asynchronous processing with Pub/Sub for spiky workloads; load tests before go-live.

Anti-patterns: synchronous chains of five services for one user request; analytics queries against the operational
database.

## Review template (one line per pillar)

| Pillar | Verdict | Evidence | Gap and owner |
|---|---|---|---|
| Foundation | | | |
| Operations | | | |
| Security | | | |
| Reliability | | | |
| Cost | | | |
| Performance | | | |

## Why this document is marked stale

It has not been reviewed for more than 12 months and Google has updated the framework since. Until it is reviewed,
treat it as a checklist of questions, and take pillar names and recommendations from Google's current documentation.

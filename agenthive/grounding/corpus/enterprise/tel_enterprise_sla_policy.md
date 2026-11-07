# Kestrava Enterprise SLA and Service Credit Policy

How Kestrava Telecom measures enterprise availability, calculates service credits and informs customers. Applies to MPLS VPN, SD-WAN, Dedicated Internet Access, Private 5G and Cloud Voice.

Fictional policy for the Wursta Agent Hive demo. Kestrava Telecom and all customers named in related data are invented.

## Service tiers

| Tier | Availability target (monthly) | Restore P1 | Restore P2 | Restore P3 | P1 first notice | Credit cap (% of service MRC) |
|---|---|---|---|---|---|---|
| Platinum | 99.98% | 2 h | 4 h | 12 h | 30 min | 40% |
| Gold | 99.95% | 4 h | 8 h | 24 h | 60 min | 30% |
| Silver | 99.9% | 6 h | 12 h | 48 h | 60 min | 20% |

Each contracted service (for example `SVC-1004-P5G`) has its own downtime budget and monthly recurring charge (MRC). Credits are calculated per service.

## How availability is measured

Availability is **site-weighted**, so a short outage at one branch does not count the same as a network-wide outage.

- **Site-minutes** of an incident = outage minutes x sites affected.
- **Downtime budget** for the month = sites x minutes in the month x (100 - target) / 100. A 30-day month has 43,200 minutes; a 31-day month has 44,640.
- **Availability** = 100 x (1 - consumed site-minutes / (sites x minutes in the month)).
- A service is **breached** as soon as consumed site-minutes exceed the budget, even mid-month.
- Packet loss above 5% on a service counts as an outage for the duration of the degradation.

Example: a Platinum MPLS service with 120 sites in November has a budget of 120 x 43,200 x 0.02% = 1,036.8 site-minutes.

## Exclusions

The following incidents are logged but do not consume the budget:

- **Planned maintenance** announced to the customer at least 72 hours in advance.
- **Customer-caused** outages (premises power, customer equipment, customer configuration changes).
- **Force majeure**, only when Kestrava has declared it to the customer in writing. Weather-related outages without a written declaration are not excluded.

## Service credit calculation

### Availability band credit

| Shortfall below target (percentage points) | Credit (% of service MRC) |
|---|---|
| up to 0.05 | 5% |
| more than 0.05 up to 0.20 | 10% |
| more than 0.20 up to 0.50 | 20% |
| more than 0.50 | 30% |

### Incident credits

- **3%** for each P1 incident restored later than the tier target.
- **1%** for each P2 incident restored later than the tier target.
- **1%** for each P1 incident where the first customer notice was later than the tier notice target.
- Incident credits together are capped at **10%** of the service MRC.

### Total and cap

Total credit = band credit + incident credits, capped at the tier cap (Platinum 40%, Gold 30%, Silver 20%). Credit in USD = total percent x service MRC.

### How credits are applied

- **Platinum:** proactive credit, applied automatically on the next invoice. No claim needed.
- **Gold and Silver:** the customer must claim within **30 days after the end of the month**. Account managers should remind eligible customers before the deadline.
- Credits for a month in progress are **provisional** until it closes.

## Incident communications

- **P1 first notice:** within 30 minutes (Platinum) or 60 minutes (Gold, Silver) of the incident opening.
- **P1 updates:** every 60 minutes until service is restored, even when there is no change.
- **Reason for Outage (RFO):** within **5 business days** of restoration for every P1 and P2 incident.

## Breach forecasting and required actions

The SLA Sentinel forecasts each service's month-end position using the 90-day incident history blended with the current month's run-rate.

| Status | Definition | Required action |
|---|---|---|
| breached | Budget already exceeded | Accrue the service credit, send an RFO for each P1/P2, account-manager call with the customer |
| at_risk | Breach probability 60% or higher | Proactive at-risk notice to the customer and account manager within 1 business day; NOC watch list; freeze non-urgent changes on the service |
| watch | Breach probability 30% to 60% | NOC watch list; review open changes and spares |
| healthy | Below 30% | No action |

## Writing customer notices

Every notice about an incident, an at-risk service or a breach follows the same structure:

1. **Facts:** service id, incident id, start time, current status.
2. **Impact:** sites affected and what the customer experiences.
3. **Timeline:** what has been done, the expected restore time and the next update time.
4. **Credit:** the provisional or final credit and how it is applied (automatic or claim).
5. **Next steps:** RFO date, preventive actions, account-manager contact.

Use plain language, the customer's own site names and dates with time zones. Do not name third parties (for example an upstream provider or contractor) as responsible, admit liability beyond the contract, promise credits this policy does not support, or speculate about root cause before the RFO.

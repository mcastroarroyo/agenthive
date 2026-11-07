# Halvard Control Tower Exception Management Playbook

This playbook explains how the Halvard Logistics control tower ranks shipment exceptions, which recovery options exist, who can approve them and how the team runs the day. The Control Tower, Shipment Brief and Logistics Orchestrator agents follow it.

Fictional playbook for the Wursta Agent Hive demo. Halvard Logistics, its carriers and sites are invented.

## Network at a glance

Sites: Ashford Vale DC (AVD), Redmarsh DC (RMD), Port Calder cross-dock (PCX), Port Calder container port Terminal 2 (PCP), Vantor Brackwater plant (BRK). Fourteen lanes (L01-L14) cover drayage, FTL, LTL, parcel, final mile and ocean. The Northgate Pass (Highway N-7) carries all northbound road freight from Ashford Vale; the R-12 southern corridor is the alternate route.

## Severity score

Every exception gets a score:

**score = tier weight x (1 + days late) x temperature factor x promo factor x line-stoppage factor + log10(value in USD) / 2**

| Factor | Value |
|---|---|
| Tier weight | Tier 1 = 3, Tier 2 = 2, Tier 3 = 1 |
| Temperature-controlled cargo | x 2.2 |
| Promo-critical load | x 1.3 |
| Line-stoppage risk (plant inbound) | x 2 |

| Severity | Score |
|---|---|
| Critical | 15 or more |
| High | 8 to under 15 |
| Medium | 4 to under 8 |
| Low | under 4 |

## Cause codes

| Code | Meaning |
|---|---|
| WX | Weather (closures, chain controls) |
| PORT | Port congestion or terminal outage |
| CAP | Carrier capacity (tender rejections, driver shortage) |
| DC | Facility backlog (systems outage, labour) |
| MECH | Equipment breakdown |
| DOCS | Documentation or customs hold |

Codes are internal only and never appear in customer messages.

## Recovery options catalogue

| Option | Typical effect | Typical cost |
|---|---|---|
| Wait | No change; communicate | none |
| Reroute via R-12 southern corridor | About +5 h driving versus N-7 when N-7 is closed | USD 1,350-1,900 |
| Dedicated Halvard Fleet truck | Same-day departure, no consolidation | about USD 1,400-1,900 |
| Re-tender to a backup carrier | Recovers capacity shortfalls | spot rate about +18% |
| Priority discharge at the port | About 2 days earlier off the vessel | USD 1,200 per container plus overtime drayage |
| Inter-DC transfer RMD to AVD | 1 day on lane L14 | about USD 7.90 per unit for TVs |
| Air freight from origin | Fastest for imports | very high; usually VP approval |
| Overtime shifts at a DC | Clears picking backlogs | about USD 3,400 per shift |
| Divert picking to another DC | Protects express promises | handling plus linehaul |
| Transload | Moves critical pallets to faster transport | needs shipper approval for regulated cargo |
| Broker documentation fix | Clears customs holds | about USD 350 |

## Approval limits

| Cost of the recovery action | Approver |
|---|---|
| Up to USD 5,000 | Operations manager on shift |
| Up to USD 25,000 | Director of operations |
| Above USD 25,000 | VP operations |

## Decision rules

1. **Default:** choose the cheapest option that still meets the promised delivery time.
2. If no option meets the promise, choose the option with the best hours saved per dollar within the director's limit, and tell the shipper.
3. **Plant inbound (line-stoppage risk):** choose the option with the highest net benefit, where net benefit = penalty and stoppage avoided minus cost. Bridging buys from approved alternate suppliers count as recovery options.
4. **Temperature-controlled cargo:** product integrity comes first. Check reefer fuel margin and keep cargo within 2-8 C; any transload needs the shipper's QA approval before it happens.
5. **Promo-critical loads:** protect the shipper's event date (for example a Black Friday store set-up) even when the contract promise is already missed.
6. Combine options when they share cost, such as one priority discharge for several containers on the same vessel.

## Daily rhythm

| Time | Activity |
|---|---|
| 06:30 | Exception scan: refresh ETAs, disruptions and severity |
| 07:00 | Daily shipment brief to the logistics manager; approvals requested |
| 12:00 | Checkpoint: progress on recoveries, new exceptions, customer updates sent |
| 17:00 | Checkpoint: night plan, overtime decisions, handover to the night desk |

## Escalation

- Any **critical** exception: duty director informed within 1 hour.
- Temperature excursion outside 2-8 C: shipper QA and Halvard quality lead immediately.
- Line stoppage forecast within 48 hours: shipper materials planning by phone, then email.
- Two or more critical exceptions from the same disruption: open a disruption case and run it through the Logistics Orchestrator.

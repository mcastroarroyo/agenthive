# Halvard Shipper SLAs and Customer Communications

This document lists the service levels Halvard Logistics has agreed with each shipper, how on-time performance and penalties are measured, and the standard for customer updates and the daily shipment brief.

Fictional standard for the Wursta Agent Hive demo. Halvard Logistics and all shippers named are invented.

## Shipper SLA table

| Shipper id | Shipper | Tier | On-time target | Penalty | Notify within | Contact |
|---|---|---|---|---|---|---|
| C-LRK | Larkspur Home & Tech | 1 | 97% | USD 250 per store delivery more than 24 h late; x2 for promo-critical loads | 2 h | Larkspur Supply Desk, supply.desk@larkspur.example (email + shipper portal) |
| C-VAN | Vantor Appliances | 1 | 96% | USD 4,000 per hour of line stoppage caused by late inbound material, capped at USD 40,000 per incident | 2 h | Vantor Materials Planning, materials@vantor.example (phone + email) |
| C-ORL | Orla Pharma Distribution | 1 | 98.5% | USD 1,500 per late temperature-controlled delivery; any excursion outside 2-8 C puts product on hold | 1 h | Orla Quality & Logistics, logistics@orlapharma.example (phone + email) |
| C-GRF | Greenfold Grocers | 2 | 95% | USD 150 per late delivery | 4 h | Greenfold Transport, transport@greenfold.example (email) |
| C-SBR | Sable & Rye Apparel | 2 | 95% | USD 100 per late delivery | 4 h | Sable & Rye Logistics, logistics@sableandrye.example (email) |
| C-PNC | Pinecrest Outdoor | 3 | 92% | Freight charge credited if more than 48 h late | 8 h | Pinecrest Ops, ops@pinecrest.example (email) |

## Definitions

- **On time:** delivered by the promised date and time agreed at booking. Re-promised dates do not reset the measure.
- **Late:** any delivery after the promised time. Larkspur penalties apply only to **store deliveries** more than 24 hours late; flows into Larkspur DCs and parcel injections carry downstream risk but no contract penalty.
- **Promo-critical:** a load the shipper has flagged as needed for a promotion or store reset.
- **Line stoppage:** a Vantor production line stops because inbound material arrived after the plant's buffer ran out. Hours are counted from the end of the buffer to arrival.
- **Notify within:** time from Halvard detecting the exception to the first message to the shipper contact.

## Customer update standard

Every update to a shipper contains:

1. **Shipment ids** covered (every one of them).
2. **Plain-language cause** ("the port terminal has a crane outage and our vessel is waiting at anchor").
3. **New ETA** as a date and time.
4. **Impact** in the shipper's terms (stores affected, buffer end time for the plant line, temperature status for pharma).
5. **Recovery actions** Halvard is taking or proposes, and any decision needed from the shipper.
6. **Next update time.**

Never include internal codes: disruption ids (DSR-...), lane ids (L01-L14) or cause codes (WX, PORT, CAP, DC, MECH, DOCS). Do not blame a named carrier or terminal operator; describe the event.

## Update cadence

| Situation | Cadence |
|---|---|
| Critical exception | Every 4 hours until resolved |
| Tier 1 shipper, any exception | Every 12 hours, and immediately when the ETA changes |
| Tier 2 and 3 | Daily, and when the ETA changes |
| Temperature-controlled cargo | Temperature reading in every update |

An exception counts as "notified" only when the shipper has received the new ETA; a holding message ("we are checking") does not reset the clock if the ETA has since changed.

## Daily shipment brief

The logistics manager receives a brief at 07:00 every day in this format:

1. **Headline:** two sentences — how many shipments are late, the biggest risk and the decision needed today.
2. **What is late and why:** table of exceptions by severity with shipper, consignee, hours late, cause and current ETA, grouped by disruption.
3. **Customer impact:** per shipper, penalty exposure in USD with the calculation, downstream effects (store stock-outs, line stoppage hours, patient-care risk) and whether the notification deadline was met.
4. **Recommended actions:** per critical or high exception, the recommended recovery option with cost, new ETA and who must approve it (ops manager up to USD 5,000, director up to USD 25,000, VP above).
5. **Customer updates:** which shippers are owed an update, with the drafted message ready to send.
6. **Watch list:** disruptions expected to clear or worsen in the next 24 hours.

Keep the brief under one page; detail lives in the control tower.

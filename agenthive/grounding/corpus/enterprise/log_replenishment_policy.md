# Halvard Demand-Driven Replenishment Policy

This policy sets how stock is replenished at the sites Halvard Logistics manages for its shippers: service levels, reorder formulas, rounding, disruption buffers, expediting and purchase-order approval. The Replenishment agent applies it.

Fictional policy for the Wursta Agent Hive demo. Halvard Logistics, Larkspur, Vantor and their suppliers are invented.

## Sites in scope

| Site | Description | Items |
|---|---|---|
| AVD | Ashford Vale DC | Larkspur DC stock (TVs, laptops, audio, consoles, smart home), Vantor finished goods and service parts |
| RMD | Redmarsh DC | Larkspur DC stock for Central and South |
| BRK | Vantor Brackwater plant | Raw materials, including ABS/PC resin (RES-ABS-PC, in kg) |

## Service levels

| ABC class | Cycle service level | z value |
|---|---|---|
| A | 98% | 2.05 |
| B | 95% | 1.64 |
| C | 90% | 1.28 |

Planners may override the service level for a single item with a written reason (for example a promotion).

## Formulas

- **Safety stock (SS)** = z x sqrt(LT x sd² + mean² x sdLT²), where mean and sd are daily demand, LT is lead time in days and sdLT its standard deviation.
- **Reorder point (ROP)** = mean x LT + SS.
- **Inventory position (IP)** = on hand + on order - backorders.
- **Order trigger:** order when IP is at or below ROP.
- **Order-up-to level** = ROP + mean x review period.
- **Order quantity** = the larger of (order-up-to - IP), the EOQ and the MOQ, rounded **up** to the case pack.
- **EOQ** = sqrt(2 x annual demand x order cost / (unit cost x 22%)), using a 22% annual holding rate.
- **Days of supply** = (on hand - backorders) / mean daily demand.

## Review cycle

Items are reviewed every **7 days**; A items are also checked daily during disruptions. Suggested purchase orders are grouped by supplier.

## Demand spikes

If the mean of the last 14 days is more than **1.3x** the planning mean, use the recent mean for this cycle and **investigate the cause** before the next review. Spikes in service parts often signal a quality problem (for example housing replacements rising after a product advisory) and must be shared with the shipper's quality team.

## Disruption buffers

- **Port congestion:** add the terminal's published average delay to the lead time (for example +4 days).
- **Weather closures:** add 1-2 days for affected road lanes.
- Remove the buffer once the disruption has cleared for one full review cycle.

## Expediting

Expedite when on-hand stock runs out **before the next inbound arrives**. Size the expedite to cover the gap plus half a day of demand, rounded to the alternate source's pack size.

| Item | Site | Approved alternate | Lead time | Cost | Rules |
|---|---|---|---|---|---|
| RES-ABS-PC (resin) | BRK | Calder Polymers (domestic) | 3 days | USD 3.60/kg versus 2.85/kg standard | MOQ 2,000 kg, 1,000 kg packs; certificate of analysis required for every lot |
| LUM-65Q8 (65-inch TV) | AVD | Inter-DC transfer from RMD | 1 day | USD 7.90 per unit | Redmarsh keeps at least 7 days of its own demand; maximum 120 units in the current plan |

Items without an approved alternate are expedited by asking the primary supplier for air or priority shipment.

## Excess stock

- **Days of supply above 60:** stop ordering, review open purchase orders and ask the shipper about cancelling or deferring them.
- End-of-life items (for example LUM-55Q8) are never reordered; excess is reported to the shipper's merchandising team.

## Purchase-order approval

| PO value | Approver |
|---|---|
| Up to USD 50,000 | Planner |
| Up to USD 250,000 | Supply manager |
| Above USD 250,000 | Director |

Expedite premiums (the extra cost over the standard source) are approved under the control tower limits: up to USD 5,000 by the operations manager, up to USD 25,000 by the director.

## Output of a replenishment run

Per item: demand used, safety stock, reorder point, inventory position, days of supply, status (order now, expedite, excess or OK), suggested quantity and value, and any expedite proposal. Per supplier: the suggested PO lines and total value.

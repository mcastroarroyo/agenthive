# Larkspur Inventory Planning Standards

These standards define how Larkspur Home & Tech measures stock risk in stores, when stock is rebalanced between stores, and how excess and end-of-life inventory is cleared. The Inventory Risk and Inventory Campaign agents apply them.

Fictional standards for the Wursta Agent Hive demo. Larkspur Home & Tech, its stores and brands are invented.

## Store network

| Region | Stores |
|---|---|
| North | S01 Northgate Plaza, S02 Kingsreach Commons, S03 Elmstead Market, S04 Frostholm (compact) |
| Coast | S05 Port Calder Waterfront (flagship), S06 Silverton Bay, S07 Gullwing Point, S08 Saltmere (compact) |
| Central | S09 Ashford Vale Centre (flagship), S10 Redmarsh Junction, S11 Brackwater Mills, S12 Lowmoor (compact) |
| South | S13 Cindervale, S14 Sunhollow, S15 Marrow Creek (compact), S16 Dunmere Outlet (outlet) |

Online orders ship from Ashford Vale DC and Redmarsh DC, both operated by Halvard Logistics.

## Days of cover

**Days of cover = units on hand / average daily unit sales over the last 28 days.** A position with no sales shows 999 days.

| Risk | Rule |
|---|---|
| Stock-out critical | Cover below 3 days |
| Stock-out | Cover below 7 days |
| Covered by inbound | Stock-out risk, but an on-order delivery lands before stock runs out |
| Overstock | Cover above 60 days |
| Overstock critical | Cover above 90 days |
| End-of-life overstock | End-of-life item whose cover exceeds the days left until its end-of-life date (minimum 30 days) |
| Healthy | Everything else |

Network cover for a SKU is total on hand across stores divided by total daily sales.

## Store-to-store transfers

Transfers are the first response to imbalances, before new purchases or markdowns.

- **Receivers:** stores below 10 days of cover; fill them up to **21 days** (net of inbound arriving within 7 days).
- **Donors:** stores above 40 days of cover; a donor always keeps at least **30 days**.
- **Minimum transfer:** 2 units.
- **Same region first** (2-day lead time), then cross-region (4-day lead time).

| Ship class | Same region (per unit) | Cross-region (per unit) |
|---|---|---|
| Parcel | $1.50 | $4.00 |
| Large (TVs up to 55 inches) | $18 | $42 |
| White-glove (large TVs) | $24 | $55 |

Store managers confirm pick lists in the store system before stock moves.

## Excess inventory

1. **Campaign before markdown.** Overstocked items get a targeted campaign to the best-matching customer segments first (see the promotions guidelines for margin floor and calendar rules).
2. If cover is still above 60 days two weeks after the campaign, consider a second wave or a store transfer.
3. **Clearance markdown** only near end of life or end of season, at the category clearance discount below.
4. Excess above **$50,000 at cost** on a single SKU goes to the merchandising director for review.
5. Holding cost is **25% of unit cost per year** and must be included in every clear-versus-hold decision.

| Category | Clearance discount |
|---|---|
| TV & Home Theater | 35% |
| Computing | 30% |
| Audio | 45% |
| Smart Home | 45% |
| Kitchen | 40% |
| Gaming | 40% |
| Networking | 45% |
| Wearables | 50% |

Clearance below cost is allowed only for end-of-life items, with director sign-off.

## End-of-life calendar

| SKU | Product | End of life | Successor |
|---|---|---|---|
| LUM-55Q8 | Lumetra Q8 55-inch QLED TV | 2027-01-15 | LUM-55Q9 launches 2027-01-15 |
| AUR-BUDS3 | Aurion Buds 3 | 2027-01-31 | Aurion Buds 4, launched 2026-09-15 |
| WAV-AX3000 | Wavelyn AX3000 Wi-Fi 6 router | 2026-12-31 | Wavelyn Wi-Fi 7 router |
| TES-FIT5 | Tessel Fit 5 | 2027-02-28 | Tessel Fit 6 |

**AUR-PARTY2** (Aurion Party Speaker 2) is a seasonal item, not end-of-life: the next selling season starts in April. Holding it over winter is an option, but carry the holding cost.

## Allocation-constrained items

Some items are short because of supply, not planning (for example consoles and large TVs arriving by ocean). For these, do not transfer stock away from stores with confirmed customer orders, and prioritise stores with Black Friday doorbuster commitments.

## Reporting

Weekly inventory review covers: top 10 overstocked SKUs by excess value at cost, stores with stock-out-critical positions, lost margin per day on stock-outs (daily sales x unit margin), transfers proposed and executed, and campaigns running against excess.

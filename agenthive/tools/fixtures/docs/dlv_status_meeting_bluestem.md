# Weekly status meeting — Bluestem Foods analytics platform (SOW-2026-0388)

**Date:** 2026-11-04 · **Duration:** 42 min · **Contract:** SOW-2026-0388 (time & materials, not-to-exceed $296,400)
**Bluestem Foods (fictional):** Karen Voss (Head of Analytics), Pete Alvarado (COO), Nadia Brooks (IT lead)
**Wursta:** Olumide Bakare (data engineer), Sofia Brandt (data engineer), Grace Whitmore (delivery lead)

---

[00:40] **Grace (Wursta):** Quick status: ERP orders, WMS inventory and the retailer EDI pipelines are in production. Marketing spend pipeline is in UAT. Five of the six dashboards are live. The forecast model is training on three years of history; first accuracy report next Wednesday.

[02:15] **Karen (Bluestem):** Good. Honestly, I'm a bit frustrated about the forecast — we're behind where I hoped. The board deadline is December 11 and I need numbers I can defend.

[03:02] **Grace:** Understood. The forecast is on plan for the 11th; the delay was the EDI file format change on your retailers' side in October.

[04:30] **Pete (Bluestem):** While you're at it, can we also add the CRM as a source? Sales wants to see pipeline next to sell-through.

[05:12] **Karen:** And we need three more dashboards for the regional managers — one per region. Same look as the sales one.

[06:40] **Pete:** One more thing: could the inventory numbers be real-time? The warehouse team looks at them every hour.

[08:05] **Karen:** The forecast should also suggest prices for slow movers. Our competitors do dynamic pricing.

[09:20] **Nadia (Bluestem):** Can we include a backfill of five years of history instead of three? Finance wants to compare with pre-pandemic years.

[11:45] **Karen:** Also, please fix the region filter on the inventory dashboard — it drops the Northwest region when you pick "all".

[12:30] **Nadia:** And alert us when the EDI file is late. Last Monday we only noticed at noon.

[14:10] **Pete:** We'd like training for our 40 store managers too, so they can use the dashboards. Maybe two sessions.

[16:00] **Karen:** I'm disappointed we didn't think about the store managers earlier. This is unacceptable if they can't use it at launch.

[17:20] **Grace:** We'll come back with an impact assessment within three business days for anything outside the SOW, as the change-control clause says.

[19:05] **Pete:** Could you also review our cloud bill? It went up 30% this quarter.

[21:40] **Olumide:** For the EDI alert — that's part of the data-quality checks; we can have it by Friday.

[24:10] **Karen:** Fine. Next week I want to see the accuracy numbers and the plan for these requests. We can't slip the December date.

[26:00] **Grace:** Burn so far is about 62% of the not-to-exceed amount. We'll flag at 80% as agreed.

## Actions noted
- Grace: impact assessment for new requests by 2026-11-07.
- Olumide: late-EDI alert by 2026-11-06.
- Sofia: fix inventory dashboard region filter by 2026-11-05.
- Karen: confirm regional dashboard requirements.

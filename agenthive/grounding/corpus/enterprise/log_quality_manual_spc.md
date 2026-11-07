# Vantor Brackwater Plant Quality Manual: SPC, Root Cause and CAPA

This excerpt from the Vantor Appliances Brackwater plant quality manual covers statistical process control, reaction plans, change and material control, root-cause analysis and corrective action. The Mfg Quality agent applies it.

Fictional quality manual for the Wursta Agent Hive demo. Vantor Appliances and its plant are invented.

## Lines and characteristics

| Line | Process | Key characteristic | Specification |
|---|---|---|---|
| BW-2 | Injection molding of the VAN-CM12 coffee-maker housing (mold M-2207, 4 cavities) | `boss_wall_mm`: wall thickness at screw boss B3 | nominal 2.40 mm, LSL 2.28, USL 2.52 |
| BW-1 | Assembly of the VAN-AF55 air-fryer basket handle | `handle_pull_force_n`: handle pull-off force | nominal 182 N, LSL 160, USL 205 |

## Control charts

- **X-bar and R charts**, subgroups of **n = 5**, one subgroup per shift: shift A 06:00, shift B 14:00, shift C 22:00.
- Points are plotted against **Phase I control limits** from the last capability study, not recalculated from current data.
- Constants for n = 5: **A2 = 0.577, D3 = 0, D4 = 2.114, d2 = 2.326**.
- X-bar limits = centre ± A2 x R-bar; R chart upper limit = D4 x R-bar. One sigma of X-bar = A2 x R-bar / 3.

## Out-of-control rules (Western Electric)

| Rule | Signal |
|---|---|
| R1 | 1 point beyond 3 sigma |
| R2 | 2 of 3 consecutive points beyond 2 sigma on the same side |
| R3 | 4 of 5 consecutive points beyond 1 sigma on the same side |
| R4 | 8 consecutive points on one side of the centre line |
| Trend | 6 consecutive points steadily increasing or decreasing |
| R chart | Range above the R upper control limit (variation increase) |

## Reaction plan

When any rule fires:

1. **Stop** and tell the shift lead; do not adjust the process by feel.
2. **Contain:** quarantine all product made since the last good subgroup; 100% inspect it for the affected characteristic and related defects.
3. **Notify Quality within 1 hour.**
4. Check recent changes: material lots, process parameters, equipment alarms, maintenance and staffing.
5. Restart only after Quality signs off on a confirmed cause and a verified correction.

## Capability

- **Cpk of 1.33 or higher** is required for every key characteristic.
- Cpk between 1.0 and 1.33: action plan within 2 weeks, increased sampling.
- **Cpk below 1.0:** containment (100% inspection) and a CAPA are mandatory.
- Cpk uses within-subgroup sigma (R-bar / d2); Ppk uses overall sigma.

## Change management

Any change to a process parameter (for example mold temperature, injection pressure, hold time or cycle time) requires an **engineering change notice (ECN)** and a **validation run** with capability data **before** production. Trials without an ECN are not allowed, including cycle-time reduction trials.

## Material control

- Resin must be dried to a dew point of **-40 C or lower**, with moisture **0.02% or lower** before molding.
- Every **resin lot change** requires a first-article check on the key characteristics.
- **Dryer alarms** require a work order and a moisture test before production continues; acknowledging an alarm is not enough.
- Supplier certificates of analysis are checked on receipt; out-of-spec moisture goes to the dryer qualification procedure.

## Root-cause tools

- **5-why:** ask "why" until the answer is a process or system gap, not a person. Each "why" must be backed by evidence (data, events, inspection).
- **Fishbone (6M):** Man (people and training), Machine, Method, Material, Measurement, Mother nature (environment). Record every candidate cause and mark which are confirmed by data.

## CAPA and 8D

| Step | Content | Deadline |
|---|---|---|
| D1 | Team | Day 1 |
| D2 | Problem description (what, where, when, how many) | Day 1 |
| D3 | Containment | Within 24 h |
| D4 | Root cause (occurrence and escape) | Within 5 working days |
| D5 | Chosen corrective actions | With D4 |
| D6 | Implement and verify | Agreed date |
| D7 | Prevent recurrence (procedures, ECN process, FMEA update) | Agreed date |
| D8 | Close and recognise the team | After verification |

- The full **8D report** is due within **10 working days**.
- **Effectiveness check** after **30 days** of production: capability back above 1.33 and defect rates at baseline.
- Each action has one owner and a due date.

## Customer complaints

- Acknowledge every customer complaint within **24 hours** and confirm containment.
- Link the complaint to date codes and production lots; check SPC and defect data for the same period.
- Share the 8D with the customer when it is closed.

## Defect monitoring

Weekly Pareto of defects per line in parts per million. A defect type whose recent rate is **2x or more** its baseline is treated as a significant increase and triggers a root-cause review, even if the line's SPC chart is in control.

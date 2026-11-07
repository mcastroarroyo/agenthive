# Kestrava Retention and Next-Best-Offer Playbook

This playbook defines which offers Kestrava Telecom may make to consumer subscribers, the guardrails that protect margin and customers, and the measurement standard every retention, cross-sell and win-back campaign is judged by.

Fictional playbook for the Wursta Agent Hive demo. Kestrava Telecom and its subscribers are invented.

## Campaign types

- **churn_save:** retain subscribers with a high churn score; success is lower churn than the holdout.
- **cross_sell:** sell an additional product (for example 5G Home to mobile customers); success is higher conversion than the holdout.
- **win_back:** recover customers who ported out in the last 90 days; success is port-ins above the holdout.

## Offer catalogue

| Offer id | Offer | Kind | Cost to Kestrava | Eligibility |
|---|---|---|---|---|
| OFF-SPEED2G | Fiber Max 2 Gig upgrade, same price for 12 months | retention | $49.20 | Fiber 1 Gig, tenure 12+ months, no arrears |
| OFF-MOB15 | 15% off mobile for 12 months | retention discount | 15% of $58 per line x 12 months | Mobile postpaid, contract ends within 60 days |
| OFF-DATA50 | +50 GB monthly data for 6 months | retention | $9 | Capped mobile plan used at 80% or more of the cap |
| OFF-ONE-BUNDLE | Kestrava One: add 5G Home at 20% off for 12 months | cross-sell | $120 | Mobile postpaid, address in 5G Home coverage, no Kestrava home broadband |
| OFF-DEVICE200 | $200 device upgrade credit | retention | $200 | Mobile postpaid, device 24+ months old, tenure 24+ months, churn score 0.5+ |
| OFF-STREAM6 | 6 months streaming add-on included | retention | $27 | Fiber or 5G Home customer |
| OFF-PAYPLAN | Bill payment plan with late-fee waiver | care | $15 | Account in arrears and churn score 0.5+ |

## Guardrails

These rules are applied before any offer is ranked:

- **Cooldown:** no retention offer if the subscriber received one in the last **180 days**. Cross-sell offers are still allowed.
- **Arrears:** no discount offers (OFF-MOB15, OFF-DEVICE200, OFF-ONE-BUNDLE) when the account is more than **60 days** in arrears. Route these customers to OFF-PAYPLAN or care.
- **Cost ceiling:** offer cost must not exceed **30% of the subscriber's annual ARPU**.
- **Low risk, no incentive:** subscribers with a churn score below 0.3 get a loyalty thank-you, not an incentive.

## Expected-value ranking

For each eligible offer:

- **Acceptance probability:** retention offers use the base rate adjusted by churn score (base x (1 + 0.5 x (churn score - 0.5))); cross-sell offers are adjusted by NPS.
- **Value if accepted:** churn score x **60% save rate** x 12 months of ARPU for retention offers, plus 80% of any new monthly revenue x 12.
- **Expected value** = acceptance probability x (value if accepted - offer cost).

Lead with the highest expected value and keep the second offer as the fallback if the customer declines. When nothing has positive expected value, make no offer.

## Measurement standard

Every campaign keeps a random **10% holdout** that is never contacted.

| Metric | Definition |
|---|---|
| Read window | 30-day churn read for churn_save; 21-day conversion for cross-sell; 30-day port-in for win-back |
| Uplift (pp) | control churn % - treatment churn % (or treatment conversion % - control conversion %) |
| Incremental saves or conversions | uplift x treatment targeted |
| Significance | two-proportion z-test, p below 0.05 |
| Total cost | offer cost x accepted + contact cost x reached + fixed cost |
| 12-month value | incremental x ARPU x 12 x survival factor |
| ROI | (value - cost) / cost |
| Cost per incremental | total cost / incremental |
| Accepted per incremental | accepted offers / incremental outcomes |

ARPU used for value: **fiber $72, mobile $58, 5G Home $50** per month. Survival factor: **0.85** for churn_save, **0.8** for cross-sell, **0.7** for win-back.

## Decision thresholds

- Target **cost per incremental save of $250 or less**.
- **Accepted per incremental above 5** is a subsidy warning: the offer mostly goes to customers who would have stayed or bought anyway. Re-target with an uplift model instead of churn score alone.
- Results that are **not significant at 95%**: extend the read or enlarge the holdout before scaling.
- **Early reads** (campaigns still in flight) are reported but never used to scale a campaign.
- Negative ROI on 12-month value: stop or redesign the offer.

## Segment analysis

Always break uplift down by segment (Young digital, Families, Price-sensitive, Small business, Rural fiber, Premium). A campaign with small overall uplift may work well in one segment; the recommendation should name where to keep the offer and where to stop it.

# V2 public-opportunity and cost-power audit: development result

Date: 2026-08-11.

## Outcome

The frozen v2 candidate achieves **development GO** on the three authorized old
datasets. All public-selected routes pass safety, availability, unsafe-rate,
and 5pp excess-time gates. The only dataset on which v2 elects to make an
efficiency intervention has 885 common-safe pairs and reduces genuine union
time by 45.13%.

This is not external confirmation. It authorizes one fresh, untouched dataset
under the frozen v2 policy.

## What changed from v1

### Public opportunity gate

V1 routed on cost CV alone. V2 additionally compares the public risk/time
frontiers of risk-per-second and score-time. It selects risk-per-second only
when:

- cost CV >= 0.50; and
- the minimum public risk-equivalent time saving across six positive budgets is
  at least 40%.

Otherwise v2 uses score-time and explicitly abstains from an efficiency claim.

The 40% gate is not numerically knife-edge on the old datasets: CIFAR-100N's
minimum opportunity is 47.68%, StoryLines-main's is 36.23%, and CIFAR-10N's is
18.79%.

### Public cost-power sentinel planner

V2 plans the uniform sentinel size from the strictest target, alpha, population
size, and public capacity limits. With relative target width 0.12, the formula
selects:

- 750 records for CIFAR-100N and CIFAR-10N;
- 1,500 records for StoryLines-main.

The normal approximation is used only for pre-outcome power planning. Every
issued certificate remains an exact hypergeometric certificate.

## Complete 100-repetition result

| Dataset | Public CV | Minimum opportunity | Public route | Sentinel | Safety | Availability | Unsafe issued | Mean excess | Efficiency result |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| CIFAR-100N | 0.688 | 47.68% | risk/second | 750 | 97.67% | 100% | 0.89% | 2.60pp | 45.13% / 885 pairs |
| CIFAR-10N | 0.317 | 18.79% | score-time | 750 | 99.33% | 99.89% | 0.44% | 3.19pp | abstained |
| StoryLines-main | 0.774 | 36.23% | score-time | 1,500 | 100% | 71.33% | 0% | 3.36pp | abstained |

Decision:

- all three selected routes pass: **YES**;
- at least one efficiency route selected: **YES**;
- selected-efficiency paired reduction >=25%: **YES, 45.13%**;
- v2 development: **GO**.

## Why a fixed sentinel was rejected

The six-count screen showed an irreducible fixed-count trade-off on
StoryLines-main:

| Sentinel | RPS excess | RPS paired saving | RPS strict pass |
|---:|---:|---:|:---:|
| 250 | 9.94pp | 21.76% | NO |
| 500 | 7.77pp | 18.18% | NO |
| 750 | 5.22pp | 13.81% | NO |
| 1,000 | 3.47pp | 13.31% | NO |
| 1,250 | 1.47pp | 10.73% | NO |
| 1,500 | 1.73pp | 6.15% | NO |

Increasing sentinel power fixes certificate excess but erases the efficiency
gain. V2 therefore combines power planning with public efficiency abstention;
it does not claim that a larger sentinel improves risk-per-second everywhere.

## Evidence boundary and paper status

- Development data: old CIFAR-100N, CIFAR-10N, StoryLines-main only.
- Locked and unused in v2 tuning: NYT Topical Relevance, ImageNet-16H,
  CIFAR-10H record-level, Collab-CXR, and StoryLines pilot.
- Dopanim remains closed.
- No WGA, group audit, retraining, repair utility, or downstream test metric is
  introduced.

V2 is now strong enough to justify a KBS method-paper continuation, but not yet
submission-ready. The central claim must remain conditional: the system makes
an efficiency intervention only when public frontier geometry supports it,
while exact certification governs every issued recommendation.

## Required next step

Freeze `V2_CANDIDATE_PROTOCOL.md`, `src/v2_policy.py`, target grids, alpha,
time budgets, and pass thresholds. Then evaluate one genuinely fresh dataset
with public per-record or per-batch review time, a public risk input, and
untouched independent truth. No further old-data threshold adjustment is
authorized after that evaluation begins.

Artifacts:

- `outputs/v2_sentinel_screen/summary.json`
- `outputs/v2_sentinel_screen/sentinel_grid_summary.csv`
- `outputs/v2_candidate_development/summary.json`
- `outputs/v2_candidate_development/recommendations.csv`

All seven project tests pass.

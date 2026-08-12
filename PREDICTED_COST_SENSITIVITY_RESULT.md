# Predicted-cost and gate-sensitivity result

This is an old-data development robustness study.  It is not a fresh external
confirmation and does not alter any Infection Inspection lock or result.

## Protocol

- Dataset: CIFAR-100N rank-invariant development rerun, three score seeds.
- Forecast: five-fold leave-fold-out worker empirical-Bayes prediction of
  log-duration, with prior strength 5; each held-out batch excludes its own
  recorded duration.
- Forecast diagnostics: 519 workers, 10,000 batches, log RMSE 0.46243, median
  absolute percentage error 29.68%, and cost-rank Spearman correlation 0.71370.
- Factual logged duration is used only after the public forecast has fixed the
  route, order, and nominal prefix, to charge realized workload and replay the
  exact simultaneous-v3 certificate.
- Sensitivity: multiplicative log-cost noise sigma in {0.25, 0.50, 0.75};
  Gaussian rank displacement in {0.01, 0.05, 0.10, 0.20}; 100 repetitions for
  the main scenarios and 10 perturbations x 10 repetitions for sensitivities.
- Gate thresholds remain CV >= 0.50, minimum opportunity >= 0.40, and mean
  excess budget <= 5 percentage points.

## Main results

| Public cost/order | Mean paired reduction vs score-time | Safety | Availability | Unsafe-issued | Mean excess budget | Router status |
|---|---:|---:|---:|---:|---:|---|
| Recorded-cost oracle RPS | 45.295% | 99.667% | 100% | 0.111% | 3.088 pp | PASS (upper reference) |
| OOF predicted-cost RPS | 28.093% | 100% | 100% | 0% | 5.665 pp | fallback: CV/opportunity and excess fail |
| OOF predicted-cost soft-RPS (gamma=0.5) | 26.503% | 100% | 100% | 0% | 5.707 pp | diagnostic baseline; not selected |
| OOF predicted-cost clipped-RPS (q=0.95) | 28.093% | 100% | 100% | 0% | 5.665 pp | diagnostic baseline; same order as RPS |
| OOF predicted-cost cost-ascending | 12.793% | 100% | 86.222% | 0% | 6.068 pp | negative baseline |
| OOF predicted-cost random | -81.906% | 99.667% | 44.778% | 0.248% | 10.040 pp | negative baseline |

The OOF forecast has CV 0.420 and minimum public opportunity about 0.253 for
each of the three score seeds.  The frozen router therefore selects score-time
for all three seeds.  The 28.093% figure is a forced-RPS diagnostic, not a
selected-route efficiency GO.

## Error sensitivity

Using the OOF forecast as the public cost estimate, mean paired realized
union-time reduction was 23.413%, 17.409%, and 4.942% under log-cost noise
sigma 0.25, 0.50, and 0.75.  Under rank displacement of 1%, 5%, 10%, and 20%,
the corresponding reductions were 28.442%, 25.361%, 20.573%, and 10.957%.
Safety remained the stable part of the replay; efficiency and realized budget
control degraded first.

## Gate-structure ablation

The complete public route-structure comparison is:

- always score-time;
- always risk-per-second;
- CV-only;
- opportunity-only;
- CV plus opportunity (registered gate).

On the OOF C100N forecast all three seeds fail both default public thresholds,
so CV-only, opportunity-only, and combined gating all correctly fall back to
score-time.  The cross-dataset public audit identifies StoryLines-main as the
decisive CV-only counterexample: CV=0.774 passes the CV gate, but minimum
opportunity is only 33.06%, so CV-only selects RPS whereas opportunity-only and
combined gating select score-time.  No available dataset has CV<0.50 and
minimum opportunity >=0.40, so the independent empirical necessity of the CV
gate is not identified; it remains a conservative admissibility check rather
than a separately proven causal component.

## Evidence boundary

The complete machine-readable output is in
`outputs/predicted_cost_v3_sensitivity_final/summary.json`, with detailed
recommendations, scenario metadata, threshold ablation, and gate-structure
ablation in the same directory.  These results are development robustness
evidence only.

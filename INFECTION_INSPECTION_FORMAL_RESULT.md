# Infection Inspection fresh simultaneous-v3 formal result

Date: 2026-08-12. Decision: **fresh external efficiency GO**.

## Locked design and alignment

The complete public route, population, targets, sentinel plan, seeds, outcome
parser, simultaneous certificate and gates were hash-locked before any
`expected_response` value was decoded. The formal population contains 841,126
binary volunteer classifications for 49,697 repeated subjects.

Private opening achieved exact alignment:

- matched formal records: 841,126 / 841,126;
- matched formal subjects: 49,697 / 49,697;
- missing records or subjects: 0;
- ambiguous subject truths: 0;
- invalid expected responses within formal subjects: 0.

The observed record-level error rate was 32.9814% (277,415 errors). This value
was not available when the route, targets or thresholds were chosen.

## Primary simultaneous-v3 result

The public router selected `risk_per_second`. Across 100 sentinel repetitions,
three targets `{0.25,0.35,0.45}`, two methods, and the seven-budget simultaneous
curve, all 600 recommendations were issued and safe.

| Method | Draw-family safety | Availability | Unsafe issued | Mean excess budget | Operating gate |
|---|---:|---:|---:|---:|---|
| risk-per-second | 100% | 100% | 0% | 0.208 pp | Pass |
| score-time | 100% | 100% | 0% | 4.263 pp | Pass |

Across all 300 common-safe target/repetition comparisons, the frozen primary
mean union-time reduction was 48.316%, above the 25% gate. The selected route
therefore passes both the safety/availability gates and the paired efficiency
gate.

## Target-level interpretation

The pooled reduction must not be described as uniform across targets:

| Target | Common-safe pairs | Mean reduction | Median reduction | Positive pairs | Interpretation |
|---|---:|---:|---:|---:|---|
| 0.25 | 100 | 93.36% | 94.74% | 100% | strong review-time saving |
| 0.35 | 100 | 51.59% | 71.81% | 79% | positive on average, heterogeneous across sentinels |
| 0.45 | 100 | 0.00% | 0.00% | 0% | both methods certify at zero review budget |

For the selected route, every target separately has 100% draw safety, 100%
availability, 0% unsafe issued decisions and mean excess budget below 0.5 pp.
Thus the method is not using the easy 0.45 target to hide a safety or excess
failure; it only dilutes the efficiency average with genuine zero differences.

## Post-unlock cost robustness

The primary result uses the frozen raw `finished_at - started_at` duration with
no trimming. Because the maximum elapsed session is about 14 days, two
explicitly post-unlock cost-cap analyses were run and cannot replace the fresh
primary result:

| Cost scenario | CV | Common-safe pairs | Mean paired reduction | Selected-route gate |
|---|---:|---:|---:|---|
| cap at 99th percentile, 138.919 s | 2.566 | 284 | 37.0% | GO |
| cap at 95th percentile, 19.523 s | 1.017 | 291 | 27.4% | GO |

Both scenarios retain 100% selected-route draw safety and availability, with
mean excess time near 2 pp. The 95th-percentile result is close to, but remains
above, the frozen 25% efficiency gate. This supports robustness while making
clear that raw long-session heterogeneity amplifies the primary effect size.

## Claim boundary and limitations

This is the first eligible fresh simultaneous-v3 confirmation in the current
research chain. It can replace the earlier documentation statement that no fresh v3
confirmation exists. It does not erase the corrected/post-unlock status of
WhichDog, SATBench or Dopanim.

The released source is treated under CC-BY-NC-4.0. The binary formal population
excludes nonbinary/invalid volunteer responses and singleton subjects. The main
cost is browser-session elapsed time and may include inactivity; the capped
sensitivity should therefore accompany the primary raw-time estimate. The
release also documents training-subject metadata that was deliberately not
used in the locked parser; any training-only exclusion would now be a
post-unlock subgroup analysis, not part of the fresh claim.

Primary artifacts:

- `outputs/infection_inspection_formal_confirmation/design_pre_private.json`;
- `outputs/infection_inspection_formal_confirmation/method_lock_manifest.json`;
- `outputs/infection_inspection_formal_confirmation/summary.json`;
- `outputs/infection_inspection_formal_confirmation/recommendations.csv`;
- `outputs/infection_inspection_formal_confirmation/paired_time_comparison.csv`.

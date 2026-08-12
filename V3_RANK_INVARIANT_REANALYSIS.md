# Rank-invariant v3 reanalysis

Date: 2026-08-12. This is an old-data reanalysis; it is not an external
confirmation and it does not unlock any new truth field.

## Method corrections

- The public score is converted to a descending mid-rank priority before
  division by review-cost estimate. Strictly increasing score transformations
  therefore produce the same priority and RPS order.
- Public opportunity uses the realized cost of the score-time prefix in the
  denominator, not the nominal budget fraction.
- The archived v2 SATBench confirmation and CrowdTruth screen are retained as
  historical artifacts. The rank-invariant reanalysis does not claim a fresh
  RPS-positive confirmation.

## Development rerun

The same three authorized old datasets, targets, sentinel counts, 100
repetitions, and base seed were used. The revised public route audit and
selected-route results were:

| Dataset | CV | Minimum opportunity | Route | Safety | Availability | Unsafe | Excess | RPS paired reduction |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| CIFAR-100N | 0.6878 | 45.69% | RPS | 98.00% | 100.00% | 0.78% | 2.62pp | 45.58% / 885 |
| CIFAR-10N | 0.3174 | 15.49% | ST | 99.33% | 99.89% | 0.44% | 3.19pp | abstain |
| StoryLines-main | 0.7736 | 33.06% | ST | 100.00% | 71.33% | 0.00% | 3.36pp | abstain |

The route decision and qualitative development conclusion are unchanged.

## Auxiliary baselines

On a separate public-only C100N rerun (seed 20260812), cost-ascending and a
fixed random order were evaluated with the same certificate and sentinel plan.
They are exploratory baselines, not registered efficiency estimands.

| Route | Safety | Availability | Unsafe | Excess | Common-safe pairs vs ST | Paired reduction vs ST |
|---|---:|---:|---:|---:|---:|---:|
| RPS | 98.67% | 100.00% | 0.56% | 2.47pp | 887 | 46.00% |
| ST | 98.67% | 99.56% | 0.56% | 3.45pp | -- | -- |
| Cost-ascending | 100.00% | 100.00% | 0.00% | 5.77pp | 891 | 18.55% |
| Random order | 99.00% | 49.44% | 0.67% | 8.01pp | 439 | -80.29% |

## Cluster bootstrap intervals

Intervals are 95% percentile bootstrap intervals over sentinel-draw clusters
(seed and repetition), with 5,000 resamples and seed 20260812. They are
descriptive uncertainty intervals, not replacement for the exact certificate.

- CIFAR-100N RPS: draw-family safety 98.00% [96.33%, 99.33%], availability
  100.00% [100.00%, 100.00%], unsafe-issued rate 0.78% [0.22%, 1.44%],
  excess 2.62pp [2.37, 2.87].
- CIFAR-100N paired reduction: 45.58% [44.52%, 46.67%] over 885 cells.
- CIFAR-10N ST: safety 99.33% [98.33%, 100.00%], availability 99.89%
  [99.67%, 100.00%], unsafe 0.44% [0.00%, 1.11%], excess 3.19pp [2.90, 3.50].
- StoryLines-main ST: safety 100.00% [100.00%, 100.00%], availability 71.33%
  [69.33%, 73.67%], unsafe 0.00% [0.00%, 0.00%], excess 3.36pp [2.90, 3.85].
- Archived SATBench ST confirmation: safety and availability 100.00%, unsafe
  0.00%, excess 4.25pp [3.88, 4.58].

## Scope boundary

These corrections do not create an untouched intervention-positive external
confirmation. In addition, logged durations are oracle replay costs rather
than prospective duration predictions. Any submission claim must retain both
boundaries.

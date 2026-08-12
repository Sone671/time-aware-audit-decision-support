# Frozen independent bundle-closure validation: Emotion Categorization

Date frozen: 2026-08-12, before decoding target valence on the eligible
population.

## Source and reuse

- Zenodo DOI: `10.5281/zenodo.1239758`.
- License: CC BY 4.0.
- Experiment 1 SHA-256:
  `146e6b4720ee305254f95cb35f7425a794b253acf8f957e4df5bc9fe568377b8`.
- Experiment 2 SHA-256:
  `4b4c552982a1215527e8d3b8db25cce1a07a630e57a60c62b416f38f34b2772e`.

## Isolation and deviation

The earlier public screen decoded only response time, opaque target ID, and
pressed response. It did not access target valence or correctness.

During the present candidate audit, six example data rows were inadvertently
rendered before this protocol was frozen. Their complete bundles are excluded
from every public and formal calculation:

- experiment 1 photo IDs `49`, `58`, and `59`;
- experiment 2 word IDs `10`, `11`, and `12`.

No other target-valence or correctness values may be decoded before the method
lock. The closed-column XLSX projector reads only declared worksheet columns
and resolves only shared-string entries referenced by those columns.

The first public lock attempt retained only experiment 2 because the XLSX
projector mishandled self-closing empty cells in experiment 1. It produced no
truth-based result and was superseded before truth opening. The corrected
projector excludes self-closing cells from paired start/end matching; public
integrity requires both experiments, 90 eligible bundles, 16,919 records, and
an 18-record reference plan before the lock is accepted.

## Population, action, loss, and cost

- Inferential unit: one retained participant response record.
- Action unit: one experiment-specific target stimulus bundle.
- One truth opening reveals the target valence and corrects every linked
  response error in that bundle.
- Record loss: normalized negative/positive response differs from target
  valence.
- Experiments are pooled only after prefixing target IDs with experiment; no
  cross-experiment bundle is created.
- Historical bundle workload proxy: median positive trial response time in
  seconds. It is not expert adjudication time.

## Public score and predicted cost

- Bundle priority: mean leave-one-record-out binary response disagreement.
- Five deterministic folds use stable eligible-bundle index modulo five.
- Cross-fitted log-linear OLS predicts median bundle RT from an intercept,
  public bundle priority, response-balance distance from 0.5, and
  `log(1 + record_count)`.
- Route selection uses the frozen rank-invariant CV/opportunity gate.

## Certificate and experiment

- Record reference sample: uniform without replacement.
- Reference count: the existing record planner at target 0.10, capped at 20%
  of eligible bundle count. Expected frozen value: 18.
- Reference-triggered bundle openings are deduplicated and charged once.
- Targets: `{0.10, 0.20, 0.30}`.
- Time prefixes: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`.
- Familywise beta: `0.05`, allocated over seven prefixes.
- Repetitions: 100.
- Base seed: `20260905`.
- Primary route: the public selected route.
- Comparator: sampled-record-only correction from the identical reference
  sample and pre-opening hypergeometric curve.

## Frozen decision rule

The independent usefulness validation passes only if all conditions hold on
the selected route:

1. exact target-valence coverage for every eligible bundle;
2. issue-free rate 100% and unsafe-issued rate 0% for bundle closure;
3. bundle-closure availability is no lower than sampled-record-only;
4. at least one strict planned-prefix improvement or one safe recommendation
   available only under bundle closure;
5. mean relative union-workload reduction is strictly positive over
   common-safe cells.

Failure of a usefulness condition is retained as a valid negative independent
result. No target, exclusion, route, cost model, reference count, or decision
threshold may change after truth opening.

## Evidence tier

This is an independent pre-truth historical validation of the correction-aware
bundle-closure transform. It is not a live prospective expert-timing study.

# Frozen screen for a fresh v2 efficiency confirmation dataset

Date: 2026-08-11 (Asia/Shanghai). This screen begins after the SATBench
fallback-safety confirmation. It cannot change or reinterpret that result.

## Objective

Identify one genuinely fresh public dataset on which the already-frozen v2
policy selects `risk_per_second`, then prepare an outcome-blind external
efficiency confirmation. Dataset screening is public-only; private correctness
must remain unopened until a candidate passes every public admission rule.

## Required data structure

A candidate must provide:

- repeated human decisions on identifiable items or item-condition cells;
- positive, finite, genuine per-decision response/review time;
- an observed human response usable as the audit label;
- an independent reference answer that can be isolated and kept unopened;
- at least two valid public responses in every cell used for leave-one-out risk;
- a fixed, reproducible public source and file hash.

Development data and all previously opened or locked datasets are ineligible:
StoryLines pilot/main, NYT Topical Relevance, ImageNet-16H, CIFAR-10H
record-level, CIFAR-10N, CIFAR-100N, Collab-CXR, Dopanim, and SATBench.
Supplementary SATBench files are also ineligible because the main archive has
already been opened for formal truth evaluation.

## Frozen public construction

- audit unit: one valid human decision;
- cost: released raw response/review time converted to seconds, with no
  trimming or winsorization;
- public risk: within the same dataset, item, and public experimental condition,
  `1 - (same-response count - 1) / (valid cell size - 1)`;
- score-time order: descending public risk, then frozen record order;
- risk-per-second order: descending public risk/cost, then descending risk,
  then frozen record order;
- opportunity budgets: `{0.5%, 1%, 2%, 5%, 10%, 20%}` of total time.

If a source has no repeated decisions after its documented validity filters, it
is structurally ineligible. No model trained with reference labels may be used
to manufacture a public risk score.

## Frozen public admission

The candidate is intervention-positive only when all conditions hold:

1. complete-public cost CV is at least 0.50;
2. minimum risk-equivalent time saving across all six positive budgets is at
   least 40%;
3. all public risk cells have at least two valid responses;
4. parsing and item/trial alignment are deterministic and hashable;
5. independent truth values have not been decoded during the screen.

Failure is recorded as public NO-GO and its truth remains unopened. Candidates
may be screened sequentially, but every attempted source and outcome must be
logged. Thresholds cannot be changed between candidates.

## Post-admission lock

For the first candidate that passes, freeze before truth opening:

- eligible files and exclusions;
- target grid selected without truth;
- sentinel count from the existing v2 public planner;
- alpha `0.05/3`, time grid `{0, .5%, 1%, 2%, 5%, 10%, 20%}`;
- 100 sentinel repetitions and base seed;
- the four existing operating gates: safety at least 90%, availability at
  least 30%, unsafe-issued rate at most 10%, mean excess time at most 5pp;
- the efficiency requirement: at least one common-safe comparison and mean
  paired union-time reduction at least 25% against score-time.

Any method revision after a private opening requires another untouched dataset.

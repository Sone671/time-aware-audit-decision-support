# WhichDog v2 formal efficiency confirmation protocol

Lock date: 2026-08-12 (Asia/Shanghai). Status before lock generation:
**ground-truth `class` values unopened**.

## Fixed population and source

The confirmatory population is the 61,152 public-valid annotations over 400
images and 800 exact response-space cells from Zenodo
`10.5281/zenodo.7100698`, CC BY 4.0. The archive SHA-256 is
`f74dde0f15867c2532ac028a98b0c27c41d18dc6063fc4fb51b397d57cbae150`.
The frozen record-sequence SHA-256 is
`80f7a4729f479144d7a2d6ce896a60d74cd82893b87ed8c664ee05628e9361c5`.

Public and private data occupy the same positional CSV. The public loader
clears field 9 in every record before decoding. After explicit unlock only,
the private loader may decode field 1 (`image_id`) and field 9 (`class`) from
the fixed archive. It may not alter any public exclusion or response.

## Frozen public construction

- record: one direct full-label or candidate-set annotation;
- cost: positive finite released `time` milliseconds divided by 1000, no
  trimming or winsorization;
- cell: exact `(image_id, is_candidate, canonical options set)`;
- risk: leave-one-labeler-out exact complete-answer-set disagreement in cell;
- score-time: descending risk, then frozen row order;
- risk-per-second: descending risk/cost, then risk, then row order;
- route: `risk_per_second`, frozen at cost CV `2.7346103742` and minimum public
  opportunity `0.8417539603`.

## Frozen private truth and loss

`class` is the independent Stanford Dogs class and must be an integral label in
`[0,31]`. Every image must have exactly one class across all released rows, and
the class must occur in every record's exact displayed options. Any missing,
ambiguous, or out-of-options class causes structural invalidation before method
episodes.

The binary error rule is task-aware and fixed before truth opening:

- full label (`is_candidate=0`): error unless the singleton answer equals
  `{class}`;
- candidate label (`is_candidate=1`): error iff `class` is absent from the
  selected candidate set.

This evaluates the direct response under the released task semantics. No
majority vote, aggregate label, inferred label, partial option pooling, class
repair, or post-hoc task reweighting is allowed.

## Frozen confirmation design

- time grid: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`;
- quality targets: `{35%,45%,55%}` residual error per full population;
- familywise alpha: `0.05`, allocated as `0.05/3` per target;
- uniform sentinel: 750 records from the unchanged public planner;
- sentinel repetitions: 100, base seed `20260815`;
- methods: `score_time` and `risk_per_second`;
- certificate: unchanged exact one-sided hypergeometric upper bound;
- union cost: planned-review time plus nonoverlapping sentinel time.

The selected route must have episode safety at least 90%, availability at least
30%, unsafe-issued rate at most 10%, and mean excess time at most 5 percentage
points. Efficiency additionally requires at least one common-safe pair and mean
paired union-time reduction of at least 25% against score-time. Passing all
conditions is `v2 external efficiency GO`; otherwise it is
`v2 external efficiency NO-GO`. Structural failure is reported separately.

No source, schema, unit, exclusion, cell, score, loss, target, sentinel count,
seed, alpha, time grid, method, or threshold may change after locking.

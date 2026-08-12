# Number-Adaptation public-screen protocol (superseded/ineligible)

Date written: 2026-08-12 (Asia/Shanghai). Status: **superseded before any route
screen and permanently ineligible for a fresh-confirmation claim**. The
exploratory exporter subsequently loaded stimulus fields whose relation
determines the physical answer. See
`NUMBER_ADAPTATION_CONFIRMATION_INVALIDATION.md`. This file documents the
intended isolation design; it is not an active or outcome-blind protocol.

## Fixed source and scope

- dataset: *Adaptation to number*, Zenodo DOI `10.5281/zenodo.15615038`;
- release date: 2025-06-07;
- license: CC-BY-4.0;
- source file: `data_full.mat`, 70,898 bytes, upstream MD5
  `afc146c44de0e3debd481b8bf92241cf`;
- documented population: 30 participants and single-trial rows;
- documented columns, in order: `reference_n`, `test_n`, `adapter_n`,
  `response`, `confidence`, `RT`;
- paper: Benedetto et al., *Adaptation acts directly on the sensory
  representation of numerosity*, DOI `10.1038/s41598-026-35068-6`.

The task is a two-alternative forced choice between a fixed 12-dot reference
and a variable-numerosity test. `RT` is the response latency in seconds from
stimulus onset. The source paper states that dot patterns were procedurally
regenerated on each trial; consequently, the public disagreement cell is the
documented stimulus condition rather than an unreleased bitmap identity.

## Frozen closed-column export

The MATLAB exporter is frozen before the public screen. It verifies all 30
tables, the schema-only observed row-count vector
`{240,270,240,270,270,270,320,400,400,350,400,400,400,400,400,400,400,400,400,400,480,120,480,480,480,480,480,480,480,480}`,
and the exact six-column schema. This vector was recorded after the first
export attempt stopped on participant 2 before a complete public file or any
route statistic existed. It reads stimulus fields inside one
closed transformation and writes only:

- stable row order;
- anonymous participant index;
- opaque task identifier assigned to the exact
  `(reference_n, test_n, adapter_n)` triple in first-occurrence order;
- documented binary response;
- raw positive finite `RT` seconds.

No numerosity value, correctness value, confidence value, or physical-answer
value is printed or exported. Trials where test and reference numerosities are
equal are excluded inside the transformation because the frozen later loss has
no unique physical correct answer. The exporter reports only their aggregate
count. It does not report which rows or task identifiers were excluded.

Source constraints are fixed from the public codebook and paper:

- `reference_n == 12`;
- integer `test_n` in `[5, 200]`;
- `adapter_n` in `{0, 6, 24}`;
- response in `{0, 1}`;
- raw `RT` is positive and finite.

Unlike the source paper's descriptive RT analysis, the public screen performs
no 3.5-second trimming, winsorization, replacement, or participant-wise
correction. The full positive raw RT is the prospective review cost.

## Frozen public score and routing rule

One exported trial is one audit unit. The public comparison cell is the opaque
stimulus-condition identifier. Every eligible cell must contain at least two
distinct participants. Public risk is the leave-one-participant-out response
disagreement:

`1 - (same-response count - 1) / (valid cell size - 1)`.

Multiple trials by one participant in one condition are retained as separate
audit units, because the released population is explicitly trial-level and
each row has its own measured cost. For risk construction, peer counts exclude
all focal-participant trials from that condition; the denominator is the
number of trials supplied by other participants. A cell is ineligible if it
has no other-participant trial.

The score-time order is descending public risk, then frozen row order. The
risk-per-second order uses the existing rank-priority-per-second rule, with
the same tie-break. Public opportunity is evaluated at total-time fractions
`{0.5%, 1%, 2%, 5%, 10%, 20%}`.

The unchanged router selects `risk_per_second` only if complete-public cost CV
is at least 0.50 and minimum risk-equivalent time saving is at least 40%.
Otherwise it freezes to `score_time`. A public pass alone never authorizes
opening or deriving row-level physical truth.

## Required formal lock before truth construction

If the public intervention route passes, a separate executable lock must fix:

- the exact mapping between opaque task IDs and source conditions;
- the response coding direction using source methods/code rather than observed
  accuracy;
- singleton physical truth for every non-equality task;
- record-level binary loss;
- targets `{0.15, 0.20, 0.25}` unless a public-only feasibility rule freezes a
  different grid before truth construction;
- 750 uniform sentinels, 100 repetitions, and base seed `20260819`;
- budgets `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`;
- `beta=0.05` and `alpha_cert=0.05/7`;
- methods `score_time` and `risk_per_second`;
- operating gates already stated in the simultaneous-v3 protocol.

Only after that lock is hashed may the source stimulus columns be transformed
into physical truth. No post-truth parser repair, response-code reversal, task
redefinition, target revision, seed revision, or route revision is permitted.

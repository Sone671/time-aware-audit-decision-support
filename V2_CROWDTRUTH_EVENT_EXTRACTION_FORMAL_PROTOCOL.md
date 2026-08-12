# CrowdTruth Event-Extraction v2 formal confirmation — invalidated

**Invalidation notice (2026-08-11):** after the valid public screen but before
an executable method lock was complete, an inspection command decoded the
header and first data row of `TE3-Gold_events.csv`, including one `Is Event`
value. Under this protocol's untouched-truth rule, the candidate is permanently
ineligible for formal confirmation. No further expert rows may be opened and
no method episode may be run. The design below is retained only as an audit
record and must not be used as a live lock.

Lock date: 2026-08-11 (Asia/Shanghai). Status: **invalidated before formal
confirmation**.

## Confirmatory scope

The sole candidate is the main event-annotation file from commit
`3d7596547944a3eec281676732eed2a22b412526`, archive SHA-256
`53c31eb8fba3520e9bba956ff9daa0c686852f2b380385ca1986f08f9db58e3c`.
Only the 63,030 public rows that pass the frozen structural parser are
eligible. They cover 4,202 sentence cells, with 3,929 Gold-task and 273
Platinum-task cells; every cell remains represented and has 3–15 distinct
workers. No time-expression file, aggregate result file, or development
dataset is eligible.

The repository has no SPDX license declaration. This is a hard blocker: no
private opening, formal evaluation, or redistribution may occur until reuse
terms are clarified by an authorized source.

## Frozen public construction

- audit record: one valid timed worker event-span-set response;
- cost: raw `_created_at - _started_at` in seconds, positive and finite, with
  no trimming or winsorization;
- response: exact set of lower-cased `(token, start offset, end offset)` keys;
  `no_event` is the empty set;
- cell: one CrowdFlower `_unit_id` and its one-to-one `(doc_id, sentence_id)`
  task key;
- risk: `1 - (same response count - 1) / (cell size - 1)`;
- score-time ranking: descending risk, then original retained row order;
- risk-per-second ranking: descending risk/cost, then descending risk, then
  original retained row order.

The public parser clears all non-whitelisted fields at byte level before CSV
decoding. The only expert fields permitted at this stage are
`Doc Id`, `Sentence Id`, `Lowercase Token`, `Start Offset`, and `End Offset`.
`Is Event` and all other expert values remain unopened. A worker row with an
invalid response, malformed span, or span not exactly present in the expert
token key set is excluded; no fuzzy matching, span splitting, or label-based
repair is allowed.

The frozen public intervention screen passed: cost CV `2.0784364535` and
minimum risk-equivalent time saving `0.7414448355` across budgets
`{0.5%, 1%, 2%, 5%, 10%, 20%}`. The selected route is therefore
`risk_per_second`; these are public properties, not truth-based results.

## Frozen confirmation design

- time grid: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`;
- quality targets: `{35%, 45%, 55%}` residual error per full population;
- familywise alpha: `0.05`, allocated as `0.05/3` per target;
- sentinel planner: unchanged v2 public normal-width rule;
- planned uniform sentinel: 750 records (1.2718% of the eligible population);
- sentinel repetitions: 100, base seed `20260813`;
- methods: `score_time` and `risk_per_second`;
- certificate: unchanged exact one-sided hypergeometric upper bound;
- union cost: planned-review time plus nonoverlapping sentinel time.

Targets are selected before private truth opening from the public disagreement
distribution and are not estimates of private error.

## Private truth rule (not authorized in this lock)

If and only if licensing is clarified and a separate explicit unlock is
provided, read only the six token-key columns above plus `Is Event` from the
two token files. For each task, the expert-positive set is the exact set of
token keys whose `Is Event` value is one. A worker is erroneous exactly when
its frozen response set differs from that expert-positive set. Any missing or
ambiguous key invalidates the confirmation structurally.

## Frozen decisions

The selected risk-per-second route must satisfy safety at least 90%,
availability at least 30%, unsafe-issued rate at most 10%, and mean excess
time at most 5 percentage points. Efficiency additionally requires at least
one common-safe comparison and mean paired union-time reduction at least 25%
versus score-time. If all conditions hold, the result is
`v2 external efficiency GO`; otherwise it is `v2 external efficiency NO-GO`.

No target, sentinel count, alpha, time grid, score, cost, mapping, exclusion,
license interpretation, or decision threshold may change after this lock.

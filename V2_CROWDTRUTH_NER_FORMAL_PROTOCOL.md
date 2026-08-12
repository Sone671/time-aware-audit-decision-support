# CrowdTruth OKE v2 efficiency confirmation — locked pre-private

Lock date: 2026-08-11 (Asia/Shanghai). Status: **expert Gold unopened**.

## Scope and provenance

The sole candidate is commit `b40b46bdf86a71a0054cab2768f7ffe0c4474cb3`
of the public CrowdTruth `Crowdsourcing-NamedEntities-GoldStandard` repository.
The locked archive SHA256 is
`7B29E656C4A5A114218B3A07F2C5DBA2D840A4BE80B61188546D40AA3F8C42EB`.

All five OKE2015 and both OKE2016 raw CrowdFlower result files are pooled. The
population contains 4,545 valid worker judgments on 303 units, exactly 15
distinct workers per unit. No duplicate unit-worker record remains. Aggregate
OKE expert files are the only eligible truth source and have not been opened.

The repository has no detected SPDX license. The project will not redistribute
its data; it records source commit and hashes and cites the originating dataset
and paper. Any publication package must use download instructions rather than
bundled source data.

## Frozen public construction

- unit: one worker's named-entity span-set judgment;
- cost: `_created_at - _started_at` in seconds, positive and finite, with no
  trimming or winsorization;
- response: canonical exact set from `entity_selection`;
- item: hash of OKE year and CrowdFlower unit ID;
- public risk: leave-one-worker-out exact-set disagreement within the unit;
- score-time ranking: descending public risk, then frozen record order;
- risk-per-second ranking: descending risk/cost, then risk, then record order.

Only timestamps, unit/worker IDs, `identifier`, candidate `alternative1` through
`alternative12`, and `entity_selection` are decoded publicly. Every other raw
field, including all `*_gold` columns, is byte-redacted before CSV decoding.
All 8,363 selected span tokens match a public candidate value exactly.

Public cost CV is 1.954893. Minimum risk-equivalent time saving across budgets
`{0.5%, 1%, 2%, 5%, 10%, 20%}` is 74.5132%; OKE2015 and OKE2016 separately
also exceed 73%. The frozen route is **risk-per-second**.

## Frozen confirmation design

- pooled population size: 4,545;
- time grid: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`;
- targets: `{35%, 45%, 55%}` residual exact-set error per full population;
- alpha: `0.05/3` per target with unchanged MFSC fixed sequence;
- sentinel: 750 uniformly sampled judgments, planned by the existing v2 rule;
- repetitions: 100, base seed 20260812;
- methods evaluated: score-time and risk-per-second;
- certificates: unchanged exact one-sided hypergeometric bounds;
- union cost: planned-review time plus nonoverlapping sentinel time.

Targets were chosen before Gold opening from the public disagreement
distribution (mean 59.95%, median 57.14%). They are not private-error estimates.

## Private truth and alignment

After explicit unlock, read only `Identifier`, `NamedEntity`, and expert `Gold`
from the two aggregate `*_MultiNER_and_Crowd_eval.csv` files. For each raw unit,
intersect expert-positive entity hashes with that unit's frozen public candidate
set. A worker judgment is erroneous exactly when its selected span-hash set is
not equal to this expert-positive set.

Every selected span and every candidate must align to the aggregate file. Any
missing or ambiguous alignment invalidates the confirmation structurally; it
does not authorize repair, remapping, or a new truth definition.

## Frozen decisions

The selected risk-per-second route must satisfy:

- episode safety at least 90%;
- availability at least 30%;
- unsafe-issued rate at most 10%;
- mean excess time at most 5 percentage points.

Efficiency confirmation additionally requires at least one common-safe pair and
mean paired union-time reduction of at least 25% versus score-time. If all
conditions hold, the result is `v2 external efficiency GO`; otherwise it is
`v2 external efficiency NO-GO`. No threshold, target, score, cost, sentinel,
mapping, exclusion, or interpretation may change after this lock.

# Frozen public protocol: Corn Tassels bundle validation

Date frozen: 2026-08-12 (Asia/Shanghai).  Status at freeze: the Figshare
record metadata, archive member names, CSV headers, and public archive-level
description have been inspected.  No CSV data row, expert box coordinate,
released precision/recall value, processed performance table, or
easy/hard assignment has been decoded.

## Purpose and evidence tier

This candidate is an independent third-domain, bundle-level historical
validation.  It is not a live prospective audit because the source contains
participant annotation time rather than newly collected expert adjudication
time.  The expert boxes remain isolated until the public construction, route,
loss, targets, code, and formal guard are locked.

## Fixed source

- study: Zhou et al., *Crowdsourcing image analysis for plant phenomics to
  generate ground truth data for machine learning*;
- Figshare DOI: `10.6084/m9.figshare.6360236.v2`;
- Figshare license: CC BY 4.0;
- file: `supplementaryData.zip`, 11,399,572 bytes;
- SHA-256:
  `2edd566397fb3ce5076d2674a46690ff0767aed47d19b229f18dc0859731dd82`;
- official analysis-code commit:
  `129ce10f1fcf1528feeba4e9b8f9f4a3b98fca44`.

Only the three `rawData/*_qualtrics_survey_responses.csv` members are eligible.
Processed data, BLUPs, easy/hard assignments, ML results, and image pixels are
not used in routing, cost prediction, target choice, or certification.

## Truth-isolating projection

Before CSV decoding, a byte-level RFC-4180 projector must retain only:

- `survey batch`, `image name`, `question ID`, `user id`;
- `user question total`, `question ordinal`, `user boxes`;
- `user start datetime`, `user end datetime`, `question elapsed`;
- `user x`, `user y`, `user x2`, `user y2`.

It must discard without decoding `ground truth boxes`, `unmatched gt boxes`,
`unmatched user boxes`, all `truth_*` and `intersection_*` coordinates, and
`precision`/`recall`.  A complete user has `user question total = 80`.  User
identity is the survey-batch/user pair.  Exact duplicate coordinate rows are
collapsed within user and image.  A public structural run found 19 degenerate
zero-area user-coordinate rows among 60,089 rows from complete users; these
rows are excluded before forming box sets.  This amendment was made before the
pre-private lock and before any expert coordinate was decoded.  Every retained
user-image action must still have a nonempty finite box set and one positive
finite `question elapsed` value; an action emptied by this rule invalidates the
candidate.

## Atomic bundle, priority, and public consensus

One image is one atomic verification action.  Opening its expert truth once
reveals the complete minimum-bounding-box set and resolves all linked user
annotations.

For two nonempty box sets, match boxes one-to-one to maximize the number of
pairs with intersection-over-union at least 0.50.  If the maximum matching has
size `m`, public box-set similarity is `2m/(|A|+|B|)` and disagreement is one
minus this value.  Image priority is the mean disagreement over all unordered
pairs of complete users.  The frozen crowd consensus is the user box set with
the smallest mean disagreement to peers; ties use the hashed user identifier.

## Cross-fitted cost and route

Recorded bundle workload is the median positive `question elapsed` across
complete users for one image.  It is a historical proxy, not expert audit
time.  Sort images by exact UTF-8 image name and assign fold `index mod 5`.
For each held-out fold, fit by ordinary least squares on the other four folds:

`log(median elapsed) = a + b1*log(1 + median user-box count) + b2*priority`.

The exponentiated held-out predictions form the pre-truth cost vector.  The
score-time order is decreasing image priority then image hash.  The candidate
RPS order uses rank-normalized priority divided by predicted cost.  The frozen
router selects RPS only if predicted-cost CV is at least 0.50 and minimum
score-mass-equivalent opportunity over `{0.5%,1%,2%,5%,10%,20%}` is at least
40%; otherwise it retains score-time.

## Formal design fixed before expert coordinates

- bundle loss: one if the frozen crowd-medoid box set has object-F1 below 0.80
  against the expert set under the same IoU>=0.50 maximum matching;
- targets: `{0.20, 0.35, 0.50}`;
- time grid: `{0,0.5%,1%,2%,5%,10%,20%}`;
- familywise beta: `0.05`, with `0.05/7` per fixed prefix;
- uniform sentinel size: the unchanged public planner evaluated at target
  `0.20` and the final eligible bundle count;
- 100 sentinel repetitions; base seed `20260827`;
- operating gates: issue-free draw families at least 90%, availability at
  least 30%, unsafe-issued rate at most 10%, mean excess at most 5 percentage
  points;
- efficiency diagnostic: at least one common-safe pair and mean paired
  realized-proxy reduction at least 25% relative to score-time.

Every public bundle must map to one nonempty, internally consistent expert box
set.  Missing/ambiguous alignment or any surviving truth value before the
formal lock causes structural invalidation.  Aggregate paper results may be
reported after unlock, but per-image expert coordinates are not redistributed.

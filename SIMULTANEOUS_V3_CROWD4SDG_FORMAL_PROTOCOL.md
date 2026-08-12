# Crowd4SDG simultaneous-v3 fresh external confirmation protocol

Lock date: 2026-08-12 (Asia/Shanghai). Status before executable lock:
**expert answer file absent and unopened**.

## Fixed source and population

The confirmation population is the 9,070 public-valid Amazon Mechanical Turk
judgments over exactly 907 Albanian-earthquake image tasks, with exactly ten
distinct workers per task. Source: Zenodo `10.5281/zenodo.5535744`, CC-BY-4.0.

Fixed files are:

- MTurk judgments: `albania_earthquake2019-mturk10.csv`, MD5
  `6deb3b0c61a7c8a0464ee09a73ddab76`;
- task table: `albania_earthquake2019-twitter_task.csv`, MD5
  `755b570f4c9d48c111450ae32ae7cc9b`;
- expert answers, still absent: `albania_earthquake2019-expertanswers.csv`,
  257,368 bytes, MD5 `6ef270bf06b3a3ddf88b2ce36a4e7332`.

The frozen public record-sequence SHA-256 is
`cad7dd7153594ecc630a480264ddf7d76afa527a8e0916ae560f43d0d5573f15`.
The public score, cost, and score-time ranking hashes are respectively
`720542eeacc7692470027a6d11125b1ad15c020fd537a9b7cae2fac5bf84b0a7`,
`5356273dcc92dd6e8f8629704e19ba68dff492fbf140cafde0050b0d5dc429cc`,
and `a881ca41dc8be8cc779d85e3c963b4bcec82f3d52322e5c59e79e4e98e20998a`.

## Frozen public construction

- unit: one MTurk assignment;
- cost: raw positive finite `WorkTimeInSeconds`, with no trimming;
- cell: exact `Input.info_media_0` URL;
- response: the documented five-class direct label, with the fixed raw alias
  `Not Relevant -> irrelevant`;
- risk: leave-one-worker-out exact-label disagreement within image;
- score-time: descending risk, then frozen row order;
- risk-per-second: descending risk/cost, then risk, then row order;
- selected route: `risk_per_second`, frozen at cost CV
  `0.7170299791934599` and minimum six-budget public opportunity
  `0.5106425542130111`.

## Frozen public-to-expert alignment

The released `twitter_task` table contains 907 rows with strictly increasing
creation time. The non-expert Crowd4EMS answer file contains every integer
`task_id` from 382795 through 383701 exactly as one contiguous task range.
Before expert opening, the unique alignment is frozen as:

`task_id -> twitter_task row (task_id - 382795) -> info_media_0 URL`.

As a public-only sanity check, 55 incomplete Crowd4EMS responses marked
relevant but lacking a severity tag are excluded and counted. The uniquely
determined Crowd4EMS plurality and MTurk plurality then agree for 68.421% of
798 non-tied tasks under this mapping;
four fixed circular shifts give only 46.541%--48.618%. These values are not
used for routing, target choice, certification, or formal truth.

## Frozen expert truth and loss

After explicit unlock, the expert CSV must expose `task_id`,
`info_answer_0_relevant`, and `info_answer_0_tags`, matching the public
Crowd4EMS platform schema. `False` relevance maps to `irrelevant`; `True`
relevance requires exactly one of `severe-damage`, `moderate-damage`,
`minimal-damage`, or `no-damage`. Labels are canonicalized to the same five
MTurk classes.

For each of the 907 exact task IDs, the expert responses must have a strict
majority label (more than half of valid expert responses). The expert task set
must be exactly 382795--383701. Missing tasks, extra tasks, invalid fields,
invalid labels, lack of strict majority, duplicate alignment, or failure of
the URL-set equality causes structural invalidation before any method episode.

The binary loss for every MTurk judgment is one iff its direct five-class label
differs from the singleton aligned expert label. No Crowd4EMS consensus,
MTurk majority, automated Twitter label, model output, task dropping, class
merging, or post-unlock reweighting is allowed.

## Frozen simultaneous-v3 design

- time grid: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`;
- targets: `{35%, 45%, 55%}` residual error per full population;
- simultaneous familywise bound: `beta=0.05` over seven fixed prefixes;
- local certificate level: `alpha_cert=0.05/7`;
- one shared upper-bound curve for all three targets;
- uniform sentinel: 750 records from the unchanged public planner;
- repetitions: 100; base seed: `20260818`;
- methods: `score_time` and `risk_per_second`;
- exact one-sided hypergeometric upper bound;
- union cost: planned-prefix time plus nonoverlapping sentinel time.

For each method, draw-family safety must be at least 90%, availability at
least 30%, unsafe-issued rate at most 10%, and mean safe excess time at most
5 percentage points. An efficiency GO additionally requires at least one
common-safe pair and at least 25% mean paired union-time reduction of the
selected `risk_per_second` route against `score_time`.

Passing is `simultaneous-v3 fresh external efficiency GO`; otherwise it is
`simultaneous-v3 fresh external efficiency NO-GO`. Structural failure is
reported separately. No source, parser, mapping, unit, score, loss, target,
sentinel, seed, bound, method, or gate may change after this lock.

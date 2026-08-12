# Infection Inspection fresh simultaneous-v3 formal protocol

Date frozen: 2026-08-12 (Asia/Shanghai). Status: **pre-truth lock; no private
outcome value may be opened before the executable lock manifest exists**.

## Fixed public population

The sole formal population is the 841,126 public classifications retained by
`outputs/infection_inspection_public_screen/public_screen_corrected_pretruth.json`.
It excludes invalid/nonbinary responses, nonpositive durations, repeated
subject-user submissions after the first, and all 418 singleton subjects.

Frozen public quantities:

- route: `risk_per_second`;
- score: leave-one-user-out exact binary disagreement within subject;
- cost: raw positive `finished_at - started_at` seconds, no trimming;
- score-time order: decreasing score, then source sequence;
- risk-per-second order: existing rank-priority-per-second rule;
- budgets: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`.

The 95th/99th percentile cost caps are public sensitivity diagnostics only and
must not replace raw costs in formal episodes.

## Frozen private truth and alignment

The only private source is top-level `expected_response` in the same fixed
`1_Metadata.csv` archive member. The response space is exactly
`{Sensitive, Resistant}`. After public-record reconstruction, the private
parser may decode only `classification_id`, `subject_ids`, and
`expected_response`; MIC, treatment concentration, user call/correctness,
strain, image ID, dataset split, subject data, annotations, and all other
values remain unused.

For each formal subject:

1. every eligible classification row must map to exactly the same subject ID
   used in the public parser;
2. all nonempty expected-response values must canonicalize to the binary
   vocabulary;
3. expected response must be unique and constant across all rows for that
   subject;
4. every formal subject must have exactly one such singleton truth;
5. no additional subject, nearest-key repair, MIC-based recomputation, or
   `user_call` reconstruction is allowed.

The audit loss is direct record-level inequality between the volunteer
classification and the subject's frozen `expected_response`. If any formal
subject lacks a unique exact truth, the candidate is structurally invalidated
and no method episode runs.

## Frozen targets and power plan

Targets are `{0.25, 0.35, 0.45}`. They span the public disagreement mean
0.3338 without using truth. The uniform sentinel planner is the unchanged
public v2 rule. At population 841,126 and minimum target 0.25 it returns 1,000
sentinels. This normal-width calculation is a power/cost heuristic only.

Formal constants:

- uniform sentinel count: 1,000;
- sentinel repetitions: 100;
- base seed: `20260820`;
- methods: `score_time`, `risk_per_second`;
- familywise beta: `0.05`;
- simultaneous budget count: 7;
- per-prefix certificate alpha: `0.05 / 7 = 0.007142857142857143`;
- all three targets share one sentinel and one simultaneous upper-bound curve
  within method and repetition.

## Frozen operating decision

For the public-selected `risk_per_second` route, require:

- draw-family safety at least 90%;
- recommendation availability at least 30%;
- unsafe-issued rate at most 10%;
- mean excess time budget at most 5 percentage points;
- at least one common-safe paired comparison against score-time;
- mean paired union-time reduction at least 25%.

Passing all gates yields a fresh external efficiency GO. Failure yields a
formal NO-GO with no threshold, target, cost, seed, or parser revision.

## License and claim boundary

The source is reused noncommercially under CC-BY-NC-4.0, as stated by the
Oxford University Research Archive and consistent with the bundled Readme.
Zenodo's broader record-level CC-BY-4.0 label is not used to relax source-file
terms. Reuse attribution must identify Farrar, Feehily, Kapanidis and the
Infection Inspection Zooniverse volunteers.

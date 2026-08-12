# Crowd4SDG outcome-blind simultaneous-v3 public-screen protocol

Date frozen: 2026-08-12 (Asia/Shanghai). Status: public screen only. No expert
answer file has been downloaded, decoded, or previewed in this project.

## Fixed source and evidence boundary

- dataset: Crowd4SDG crowdsourced image classification and damage assessment;
- Zenodo DOI: `10.5281/zenodo.5535744`;
- license: CC-BY-4.0;
- public file: `albania_earthquake2019-mturk10.csv`, 6,516,000 bytes;
- upstream MD5: `6deb3b0c61a7c8a0464ee09a73ddab76`;
- SHA-256: `3eb872460194857c51effbd8a39212ed851fde4814f36a58fcec1315e37c345a`;
- private file: `albania_earthquake2019-expertanswers.csv`, upstream MD5
  `6ef270bf06b3a3ddf88b2ce36a4e7332d`.

Only the MTurk file may be parsed for this public screen. The expert file must
be absent. The separately released Crowd4EMS consensus and automated Twitter
task files are not truth and are not used in scoring, routing, target choice,
or formal evaluation.

## Frozen public parser

The MTurk CSV header has been checked without decoding a data record. The
parser uses only:

- `AssignmentId`: record identity;
- `WorkerId`: pseudonymous annotator identity;
- `Input.info_media_0`: exact image/task key;
- `Answer.image-contains.label`: observed human response;
- `WorkTimeInSeconds`: genuine assignment completion time in seconds.

All other columns are ignored. Every identity and task key must be nonempty.
Time must be positive and finite and is used raw, without trimming,
winsorization, clipping, or status-dependent exclusion. Response strings are
normalized with Unicode NFKC, lowercase, outer whitespace removal, and
replacement of each non-alphanumeric run by one space. The only accepted
canonical responses are `severe damage`, `moderate damage`, `minimal damage`,
`no damage`, and `irrelevant`, matching the five categories documented by the
depositors. The raw MTurk export spells the documented `irrelevant` category
as `Not Relevant`; after normalization, the single fixed alias
`not relevant -> irrelevant` is applied. This parser correction was frozen
after the first public pass exposed the raw category vocabulary and before any
expert file was downloaded. A row failing these public checks is excluded and
counted.

Repeated submissions from the same worker for the same exact task key retain
the earliest raw CSV row. No worker, task, response, or assignment identifier
is written in clear text to derived artifacts.

## Frozen public score and route

One retained MTurk assignment is one audit unit. The public comparison cell is
the exact `Input.info_media_0` task key. Every eligible cell must retain at
least two distinct workers. Public risk is the leave-one-worker-out fraction
of peer labels that differ from the focal response:

`1 - (same-label count - 1) / (valid cell size - 1)`.

The score-time order is descending public risk, then frozen row order. The
risk-per-second order is descending public risk divided by raw work seconds,
then descending risk, then frozen row order. Public opportunity is evaluated
at total-time fractions `{0.5%, 1%, 2%, 5%, 10%, 20%}`.

The unchanged gate selects `risk_per_second` only when:

1. complete-public cost CV is at least 0.50;
2. minimum risk-equivalent time saving over all six budgets is at least 40%;
3. every retained cell has at least two distinct workers;
4. no duplicate worker remains within a cell;
5. file length and hashes match the fixed source.

Otherwise the route freezes to `score_time` and no efficiency-confirmation
claim is attempted. A public pass does not authorize truth opening.

## Required lock before expert opening

If the public route passes, a separate executable formal protocol must freeze
the expert-file parser and exact task-key alignment before the expert file is
downloaded. The direct loss is worker label unequal to the singleton aligned
expert label. Any missing, duplicate, ambiguous, or out-of-vocabulary expert
answer causes structural invalidation before episodes.

The formal lock must also freeze targets `{0.35, 0.45, 0.55}`, the unchanged
public sentinel planner, 100 sentinel repetitions, base seed, methods,
seven-budget grid, simultaneous familywise `beta=0.05` with
`alpha_cert=0.05/7`, the four operating gates, the 25% paired-time efficiency
gate, file hashes, method hashes, and a synthetic dry run. Only a later
explicit one-use unlock may authorize downloading and decoding the expert
file.

# Crowd4SDG simultaneous-v3 confirmation invalidation

Date: 2026-08-12 (Asia/Shanghai).

## Decision

`STRUCTURAL_INVALIDATION`. No simultaneous-v3 method episode was run.

The outcome-blind public screen passed on the frozen MTurk file:

- 9,070 valid assignments over 907 image tasks;
- ten distinct workers per task, with no unresolved duplicate;
- cost CV `0.7170299791934599`;
- minimum six-budget public opportunity `0.5106425542130111`;
- selected public route `risk_per_second`.

The pre-private design, parser, mapping, targets, sentinel count, seed,
simultaneous bound, and method hashes were locked before the expert file was
downloaded. The downloaded expert file matched its Zenodo size and MD5.

## Failure cause

The frozen public-to-expert join required the Crowd4EMS `task_id` range
`382795`--`383701` to map to the 907 `twitter_task` media URLs. The expert file
contains 2,725 rows whose `task_id` values are in a different range beginning
at `763xxx`; its `media_url` column is empty. Thus all 907 public task keys are
unmatched and the expert task set is not the predeclared key space.

The formal loader reported:

- raw expert rows: 2,725;
- expert rows in the frozen public task range: 0;
- strict-majority aligned tasks: 0/907;
- invalid/unmatched rows: 2,725;
- method episodes: 0.

No row-order, timestamp, majority, or URL inference was attempted. The
expert table is therefore permanently ineligible for this confirmation claim.
The public pass may be retained only as an outcome-blind structural result;
it is not evidence of certified efficiency.

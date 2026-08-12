# Independent Emotion bundle-closure validation result

## Status

The frozen usefulness decision passed. This is an independent pre-truth
historical validation after a documented full-bundle exclusion. It is not a
live prospective expert-timing experiment, and the private-truth stage has
already been opened.

## Source and action definition

- Source: Emotion Categorization, Zenodo DOI `10.5281/zenodo.1239758`.
- License: CC BY 4.0.
- Experiments: word-prime/face-target and face-prime/word-target.
- Inferential unit: one retained participant response record.
- Action unit: one experiment-specific target stimulus bundle.
- Truth opening: decode the target valence once and correct every linked
  response in that bundle.
- Cost proxy: median positive participant response time per bundle; this is
  historical workload, not expert adjudication time.

## Isolation record

The public projector read only response time, opaque target ID, and response.
During candidate screening, six example rows exposed target truth. Their six
complete bundles were permanently excluded:

- experiment 1 target IDs `49`, `58`, and `59`;
- experiment 2 target IDs `10`, `11`, and `12`.

An initial truth-free lock retained only 45 bundles because self-closing XLSX
cells were parsed incorrectly. The integrity guard detected the missing
experiment before truth opening. The projector was fixed, a regression test
was added, and the incomplete lock was superseded. The final public integrity
requirements were 90 bundles, 16,919 records, and an 18-record reference plan.

## Frozen design

- Five-fold deterministic cross-fitted log-linear bundle-cost model.
- Predicted-cost CV: `0.21284865`.
- Minimum opportunity: `-0.72414920`.
- Selected route: score-time.
- Targets: `{0.10, 0.20, 0.30}`.
- Time budgets: `{0, .005, .01, .02, .05, .10, .20}`.
- Familywise beta: `0.05` over seven fixed prefixes.
- Repetitions: `100`; base seed: `20260905`.
- Protocol, projector, public module, certificate, formal runner, exclusions,
  arrays, and method manifest were hash-locked before truth opening.

The frozen design is stored in
`outputs/emotion_bundle_closure_confirmation/design_pre_private.json`; code
hashes are in `method_lock_manifest.json`.

## Formal result

- Exact truth coverage: 90/90 eligible bundles.
- Record errors: 1,182/16,919 (`6.986%`).
- Sampled-record-only: 100% issue-free, 16.33% availability, 0% unsafe issued.
- Bundle closure: 100% issue-free, 20.33% availability, 0% unsafe issued.
- Common-safe cells: 49.
- Strictly smaller planned prefix: 7 common-safe cells.
- Bundle-closure-only safe recommendations: 12.
- Primary paired mean relative union-workload reduction: `3.60056%`.
- Mean sampled errors / spillover-corrected errors: `1.124 / 194.319`.
- Positive-spillover fraction: 100% of evaluated cells.

The unpaired issued-cell mean union workloads are 23.543% for sampled-only and
24.558% for bundle closure. They average different sets of issued cells and
must not be subtracted. The 3.60056% common-safe paired reduction is the primary
workload comparison.

All pre-specified usefulness conditions passed. The smaller independent gain,
relative to the 10.3--26.7% post-outcome development range, is reported without
retuning. The machine-readable result is
`outputs/emotion_bundle_closure_confirmation/summary.json`.

## Reproduction boundary

The public truth-free construction can be inspected with
`src/run_emotion_bundle_closure_public.py`. The guarded formal runner is
`src/run_emotion_bundle_closure_formal.py`, but its one-shot truth stage has
already run. Any later execution is reproduction on opened outcomes and must
not be described as a fresh independent validation.

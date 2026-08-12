# StoryLines cross-modal development protocol

Date: 2026-08-11.  This dataset has undergone aggregate feasibility inspection
and is development-only, not confirmatory.

Source: CrowdTruth Crowdsourcing StoryLines v2.0, Zenodo DOI
`10.5281/zenodo.1478508` (CC-compatible open release).

Each of the 7,778 candidate event pairs is one finite-population record.  The
public crowd score is `event-event_pair_only_final_score`; threshold 0.50 gives
the deployed crowd label, and `1 - abs(2p - 1)` is its fixed uncertainty/risk
score.  `Experts_Pair` is private evaluation truth.

The genuine task duration is amortized over all candidate pairs sharing the
same CrowdFlower unit: `duration / pair_count_in_unit`.  The public CV gate is
applied unchanged.  Time budgets are `{0, .5%, 1%, 2%, 5%, 10%, 20%}`, the
uniform sentinel contains 500 records, exact alpha is `0.05/3`, and targets are
`{15%, 20%, 25%}` to bracket this task's public crowd-label quality regime.

Ten sentinel repetitions constitute the smoke.  No risk transform, cost
transform, target, or threshold is changed after running it.

# Fresh efficiency screen — annotation-log round

Date: 2026-08-11. Expert truth remains unopened.

## CrowdTruth Medical Relation Extraction

The complete RelEx source contains 50,962 raw judgments on 3,397 units. Seven
duplicate unit-worker submissions were removed by the public rule that retains
the earliest completion. Public task duration has CV 0.737.

An initial exact-full-response screen had minimum public opportunity 58.42%, but
that score was not eligible for confirmation because the independent expert
files cover only the `CAUSES` and `TREATS` relations. Before truth opening, the
worker response was projected to that same two-relation scope. The aligned
minimum opportunity became 29.80%; cause-only and treat-only screens reached
18.15% and 20.88%. All routes therefore freeze to `score_time`, and no expert
file was opened.

This is a useful guardrail result: a public opportunity claim based on a broader
answer space cannot be combined with narrower truth merely because it passes.

## CrowdTruth OKE Named-Entity Gold Standard

The pooled OKE2015/OKE2016 span-selection task contains 4,545 judgments on 303
units, exactly 15 distinct workers per unit. All 8,363 worker-selected span
tokens match a released candidate span exactly. Aggregate expert Gold files
remain unopened.

Public results:

| Scope | Records | Cost CV | Minimum opportunity | Route |
|---|---:|---:|---:|---|
| Pooled | 4,545 | 1.955 | 74.51% | risk-per-second |
| OKE2015 | 3,030 | 1.910 | 74.48% | risk-per-second |
| OKE2016 | 1,515 | 2.010 | 73.71% | risk-per-second |

This is an intervention-positive public GO with a large margin on both frozen
gates. The formal design is locked at targets 35%/45%/55%, 750 uniform
sentinels, 100 repetitions, alpha 0.05/3, and the unchanged seven-point time
grid. Formal efficiency GO requires the selected route to pass all four
operating gates and achieve at least 25% common-safe paired union-time reduction
against score-time.

The source repository does not expose an SPDX license. Source data will not be
redistributed; only download instructions, commit/hash provenance, and derived
aggregate results may be packaged with the paper.

Artifacts:

- `outputs/crowdtruth_medical_public_screen/public_screen.json`;
- `outputs/crowdtruth_named_entity_public_screen/public_screen.json`;
- `V2_CROWDTRUTH_NER_FORMAL_PROTOCOL.md`;
- `outputs/crowdtruth_ner_formal_confirmation/design_pre_private.json`;
- `outputs/crowdtruth_ner_formal_confirmation/method_lock_manifest.json`.

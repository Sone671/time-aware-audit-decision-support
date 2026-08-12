# CrowdTruth OKE formal confirmation result

Date: 2026-08-11. Status: **structurally invalid before method evaluation**.

## Outcome

The pre-private lock and all 12 method hashes passed. Expert aggregate files
were then opened using only `Identifier`, `NamedEntity`, and `Gold`. The frozen
alignment rule required every public candidate span for a unit to appear among
the aggregate `NamedEntity` values before an expert-positive set could be
constructed.

That requirement failed for every unit:

- 303 of 303 units have incomplete candidate coverage;
- 202 affected units are OKE2015 and 101 are OKE2016;
- all 4,545 worker records belong to affected units;
- 968 public candidate-span hashes are absent from the corresponding aggregate
  `NamedEntity` collections;
- zero complete units remain.

The aggregate files therefore do not encode a complete expert judgment over
the exact candidate sets shown to workers. Switching after truth opening to
`MainAlternativeSpan`, `CrowdGold`, platform `*_gold` columns, or a partial-set
comparison would be a new truth definition and is prohibited by the locked
protocol.

## Formal interpretation

No score-time or risk-per-second episode was run. No recommendation, safety
metric, paired comparison, or efficiency estimate was produced. The result is
neither `v2 external efficiency GO` nor `v2 external efficiency NO-GO`; it is a
candidate-level structural invalidation.

The public intervention screen remains a valid outcome-blind observation, but
this dataset can no longer be reused for confirmatory v2 evaluation because its
expert files have been opened. It may be used only for explicitly exploratory
truth-mapping research.

The required next confirmatory step is a different untouched annotation-log
dataset with a complete independent truth label for exactly the response space
presented to workers.

Artifacts:

- `V2_CROWDTRUTH_NER_FORMAL_PROTOCOL.md`;
- `outputs/crowdtruth_ner_formal_confirmation/design_pre_private.json`;
- `outputs/crowdtruth_ner_formal_confirmation/method_lock_manifest.json`;
- `outputs/crowdtruth_ner_formal_confirmation/structural_invalidation.json`.

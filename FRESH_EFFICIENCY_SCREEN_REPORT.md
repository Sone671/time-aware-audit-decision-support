# Fresh v2 efficiency-candidate screen

Date: 2026-08-11. Frozen gates: complete-public cost CV at least 0.50 and
minimum public opportunity across `{0.5%, 1%, 2%, 5%, 10%, 20%}` at least 40%.
No candidate truth was used for a route decision.

## Outcome

No intervention-positive candidate was found in this screen. The result is not
a method failure or a formal NO-GO: the frozen v2 policy abstained before truth
opening whenever its public efficiency premise was unsupported.

| Candidate | Public structure | Cost CV | Min opportunity | Decision | Truth status |
|---|---|---:|---:|---|---|
| model-vs-human, all 17 experiments | 84,523 singleton item cells | 0.262 | not evaluable | structural NO-GO | category unopened |
| English Lexicon Project | RT and correctness but no released observed response | not evaluated | not evaluable | structural NO-GO | lexicality/accuracy unopened |
| Schmid2023 categorization | mouse decisions, outside frozen human scope | not evaluated | not evaluated | domain NO-GO | outcome unopened |
| Zenodo emotion categorization, pooled | 18,047 records, 96 repeated items | 1.117 | 22.63% | score-time | truth columns not accessed |
| emotion experiment 1 | 9,408 records | 1.040 | 13.98% | score-time | truth columns not accessed |
| emotion experiment 2 | 8,639 records | 1.207 | 31.58% | score-time | truth columns not accessed |
| OpenNeuro ds008099 food-word | 3,099 records, 105 repeated cells | 0.359 | 4.87% | score-time | four private fields byte-redacted |

## Interpretation

The screen isolates two recurring obstacles. Many released psychophysics data
either lack repeated exact stimuli or omit the observed response. Datasets that
do expose complete human decisions have raw reaction times correlated with the
difficult/minority decisions; risk-per-second therefore loses its public
advantage at the 10% or 20% budget even when cost CV is high.

The evidence supports keeping the v2 abstention gate. It does not support
weakening the 40% threshold after seeing these public curves. A further search
should prioritize genuine annotation or adjudication logs with heterogeneous
batch/work times, rather than laboratory reaction-time tasks.

## Evidence boundary

- model-vs-human `category` values were byte-redacted before CSV decoding.
- ELP trial values were not parsed after the public format showed no observed
  response field.
- Schmid2023 HDF5 values were not read; only dataset names, shapes, and dtypes
  were inspected before the mouse-domain exclusion.
- Emotion workbooks were projected to three declared public columns per
  experiment; no correctness, valence, congruency, or prime values were
  returned to the analysis.
- OpenNeuro `stim_name`, `stim_category`, `stim_class`, and `accuracy` were
  byte-redacted before TSV decoding.

Machine-readable screens:

- `outputs/model_vs_human_public_screen/public_screen.json`;
- `outputs/emotion_categorization_public_screen/public_screen.json`;
- `outputs/openneuro_ds008099_public_screen/public_screen.json`.

# Correction-aware bundle-closure result

## Decision

The proposed extension is retained. It is mathematically valid under the
declared assumptions and empirically useful on all four evaluated record-loss
layers. It is a post-outcome methodological analysis, not a fresh independent
validation or a live expert-timing result.

## Relationship to prior theory

Anthony and Salehzadeh Nobari (2026, Corollary 18) supply the base exact
finite-corpus shared-reference certificate for a pre-specified prefix family.
The present result does not claim that inversion, reference reuse,
simultaneous-prefix validity, or post-certificate prefix choice as new.

The extension treats reference labels as operational corrections. Records are
partitioned into pre-declared subject/image bundles. A uniform record sample
can trigger one truth opening for every unique bundle it encounters. If the
opening corrects every linked erroneous record, all such corrected errors can
be subtracted from the same pre-opening error-count upper bound.

For suffix error count `K`, exact upper bound `U`, and the realised set `C` of
erroneous records corrected by sampled bundle openings, the coverage event
`K <= U` implies pointwise

`K - |C| <= max(0, U - |C|)`.

Bonferroni allocation over the seven frozen time prefixes gives the same
simultaneous statement. The reference sample remains a simple random sample of
records; bundle mapping occurs only after the reference IDs are drawn.

## Required assumptions

1. The record population, bundle partition, record loss, routes, prefixes, and
   reference rule are fixed independently of reference outcomes.
2. The reference sample is uniform without replacement from records.
3. One truth opening reveals valid truth for every linked record.
4. Only errors actually corrected by an opened bundle are included in `C`.
5. Workload charges every unique planned or reference-opened bundle once.

## Verification

- Exhaustive fixed-prefix check: all 64 binary error populations and all 15
  size-two reference samples in a six-record, three-bundle corpus.
- Exhaustive simultaneous check: the same populations and samples over two
  fixed prefixes at familywise level 0.20. Worst exact failure frequency was
  0.0667.
- Repository tests: `tests/test_bundle_expanded_certificate.py`.
- Full test suite after integration: 76 passed.

## Post-outcome experiment

All routes are the preserved score-time routes. SRO corrects sampled records
only; BC applies complete bundle closure. Gain is paired relative union-workload
reduction on common-safe cells.

| Dataset/loss | Records | Reference records | SRO availability | BC availability | New safe BC cells | Paired gain |
|---|---:|---:|---:|---:|---:|---:|
| Infection response | 201,494 | 1,000 | 66.7% | 66.7% | 0 | 10.3% |
| WhichDog full label | 9,158 | 24 | 22.7% | 39.3% | 50 | 21.8% |
| WhichDog candidate coverage | 9,122 | 24 | 41.0% | 52.0% | 33 | 16.1% |
| Wisdom decision | 13,600 | 160 | 30.0% | 37.3% | 22 | 26.7% |

Both variants had 100% issue-free rate and 0% unsafe-issued rate in every loss
layer. WhichDog full-label and candidate-coverage losses were never pooled.

## Evidence boundary

The analysis uses already opened historical outcomes and recorded workload
proxies. It demonstrates internal usefulness of bundle closure but does not
establish prospective expert-time savings. A confirmatory study must freeze the
record-to-bundle mapping and linked-correction rule before collection and log
actual bundle opening, submission, completion, and correction events.

# Code package manifest

This repository contains the implementation, protocols, tests, and compact
reproducibility artifacts for time-aware audit decision support. It does not
redistribute downloaded datasets, private truth, or source archives.

## Included

- `src/`: routing, finite-population certification, public-field projectors,
  cost models, bundle accounting, runners, and guards.
- `tests/`: unit tests and protocol guard tests.
- `outputs/**/summary.json`: compact machine-readable results.
- `outputs/**/design*.json` and `method_lock_manifest.json`: selected frozen
  designs and code hashes.
- Root-level protocol and result reports: assumptions, deviations, evidence
  timing, structural exclusions, and interpretation boundaries.

## Bundle-level artifacts

- `src/run_bundle_heldout_forecast.py`: 70/30 public-feature cost forecast,
  held-out routing, and recorded-workload accounting.
- `outputs/bundle_heldout_forecast/summary.json`: coefficients, array digests,
  route geometry, diagnostics, and paired comparisons.
- `PROSPECTIVE_BUNDLE_AUDIT_PROTOCOL.md`: action definitions, timestamps, cost
  model, and analysis requirements for live bundle timing.
- `src/bundle_expanded_certificate.py`: correction-aware record-sample
  certificate whose sampled records trigger unique bundle corrections.
- `src/run_bundle_expanded_record_audit.py`: bundle-closure evaluation for
  Infection Inspection, separate WhichDog loss definitions, and Wisdom of
  Crowds.
- `outputs/bundle_expanded_record_audit/summary.json`: operating results,
  spillover corrections, safety diagnostics, and paired workload gains.
- `BUNDLE_CLOSURE_THEORY_RESULT.md`: assumptions, theorem relationship,
  exhaustive finite-corpus check, results, and scope.

## Public-field isolation and validation artifacts

- `src/mat_v5_cell_projection.py`: MATLAB-v5 cell projector that skips declared
  truth payloads during public parsing.
- `src/run_wisdom_crowds_bundle_public.py`: public construction, cross-fitted
  cost prediction, route selection, and method lock for 800 image bundles.
- `src/run_wisdom_crowds_bundle_formal.py`: guarded truth-opening runner.
- `outputs/wisdom_crowds_bundle_validation/`: locked design, method hashes, and
  compact result.
- `src/xlsx_closed_column.py`: XLSX projector that resolves only declared cells
  and the shared strings referenced by those cells.
- `src/run_emotion_bundle_closure_public.py`: public construction, cost forecast,
  routing, exclusions, and method lock for Emotion Categorization.
- `src/run_emotion_bundle_closure_formal.py`: guarded target-valence opening and
  bundle-closure evaluation.
- `EMOTION_BUNDLE_CLOSURE_CONFIRMATION_PROTOCOL.md`: population, six-bundle
  exclusion, truth-free parser revision, design, and decision rule.
- `EMOTION_BUNDLE_CLOSURE_RESULT.md`: aggregate result and interpretation.
- `outputs/emotion_bundle_closure_confirmation/`: locked design, code hashes,
  and machine-readable result.
- `CORN_TASSELS_STRUCTURAL_RESULT.md`: structural invalidation after complete
  truth-coordinate coverage failed for three image bundles.

## Excluded

- `external_candidates/`, `formal_confirmation_candidates/`, and downloaded
  archives, which may be large or contain restricted fields.
- Per-record recommendations, raw truth arrays, rendered QA images, caches,
  bytecode, and local build logs.
- Local writing and presentation directories matching `paper_*`.

## External data configuration

```powershell
$env:LATENT_GROUP_VERIFICATION_ROOT = 'D:\data\latent_group_verification_mvp'
$env:COST_AWARE_CERTIFICATION_ROOT = 'D:\data\cost_aware_certification_2026-08-11'
```

The workstation paths in `src/paths.py` are compatibility defaults. Set the
environment variables for portable use.

## One-shot truth stages

The Infection Inspection, Wisdom-of-Crowds, and Emotion-Categorization formal
truth stages have already run. A later execution is reproduction on opened
outcomes and cannot restore the original evidence timing. The Emotion result
also permanently retains the six-bundle exclusion and truth-free parser
revision.

## Reproduction

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -q
python src/run_predicted_cost_sensitivity.py `
  --output-root outputs/predicted_cost_v3_sensitivity_final `
  --replicates 100 --perturbations 10 --replicates-per-perturbation 10
```

The full sensitivity replay uses development data and is not part of the quick
test suite.

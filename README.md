# Time-Aware Audit Decision Support

Reference implementation and reproducibility package for cost-aware label
verification with exact finite-population residual-error control.

The package provides:

- score-time and rank-priority-per-second routing;
- a cost-heterogeneity and frontier-opportunity gate;
- shared-reference certificates over a fixed review-budget grid;
- held-out and cross-fitted bundle-cost evaluation;
- correction-aware bundle closure, where one truth opening can correct every
  linked record error;
- public/private field-isolation guards, method locks, tests, and compact result
  summaries.

Downloaded datasets and private truth are not redistributed. See
[CODE_PACKAGE_MANIFEST.md](CODE_PACKAGE_MANIFEST.md) for the included artifacts
and data-access boundary.

## Action units and workload

The action unit must match the verification workflow. A logged response can be
treated as an atomic action only when reviewing it reveals no information about
other responses. If one truth opening resolves several responses, those records
must be grouped into a subject, image, or stimulus bundle before routing and
workload accounting.

Logged response times are historical workload proxies. They do not measure the
time required by a new expert-adjudication interface. The live bundle-timing
design is specified in [PROSPECTIVE_BUNDLE_AUDIT_PROTOCOL.md](PROSPECTIVE_BUNDLE_AUDIT_PROTOCOL.md).

## Install and test

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -q
```

The test suite covers public-field projectors, truth-isolation guards, exact
finite-population calculations, realized-cost accounting, and bundle-closure
logic.

## Main reproducibility entry points

### Simultaneous record-level analysis

```powershell
python src/run_simultaneous_v3.py
```

Compact outputs are stored under `outputs/simultaneous_v3_reanalysis/`.

### Predicted-cost robustness

```powershell
python src/run_predicted_cost_sensitivity.py `
  --output-root outputs/predicted_cost_v3_sensitivity_final `
  --replicates 100 --perturbations 10 --replicates-per-perturbation 10
```

This analysis uses development data and can take several minutes.

### Held-out bundle-cost evaluation

```powershell
python src/run_bundle_heldout_forecast.py
```

The runner fits cost models on the first 70% of stable subject/image bundles,
sets the held-out route and prefixes from predicted costs, and then evaluates
recorded workload. Results are in
`outputs/bundle_heldout_forecast/summary.json`.

### Correction-aware bundle closure

```powershell
python src/run_bundle_expanded_record_audit.py
```

A uniform record sample triggers unique bundle openings. The sampled-record-only
comparator credits sampled errors, while bundle closure credits all linked
errors corrected by the same openings. Results are in
`outputs/bundle_expanded_record_audit/summary.json`.

### Wisdom-of-Crowds bundle validation

```powershell
python src/run_wisdom_crowds_bundle_public.py
```

The public stage uses a MATLAB-v5 projector that skips truth and correctness
payloads. The preserved result covers 800 image bundles and is stored in
`outputs/wisdom_crowds_bundle_validation/summary.json`. Its truth-opening stage
has already run; rerunning it is reproduction on opened outcomes.

### Emotion-Categorization bundle-closure validation

```powershell
python src/run_emotion_bundle_closure_public.py
```

The public stage uses a closed-column XLSX projector. Six bundles exposed during
candidate screening are excluded in full. The final design contains 90 stimulus
bundles and 16,919 records. Bundle closure increased availability from 16.33%
to 20.33%, added 12 safe recommendations, and reduced paired union workload by
3.60% over 49 common-safe cells. See
[EMOTION_BUNDLE_CLOSURE_RESULT.md](EMOTION_BUNDLE_CLOSURE_RESULT.md) and
`outputs/emotion_bundle_closure_confirmation/summary.json`.

The private truth stage has already run. The documented six-bundle exclusion
and the truth-free parser revision remain part of every reproduction.

## Structural and governance checks

- Corn Tassels was invalidated because three image bundles lacked complete
  recoverable expert-box coordinates. No incomplete-truth efficiency result is
  reported. See [CORN_TASSELS_STRUCTURAL_RESULT.md](CORN_TASSELS_STRUCTURAL_RESULT.md).
- FrameNet was excluded after exact truth alignment failed for two required
  keys.
- CrowdTruth Event Extraction was excluded after outcome isolation and source
  reuse checks failed.
- Dopanim remains excluded from reuse.

## External data configuration

Old-data development runners use these optional environment variables:

```powershell
$env:LATENT_GROUP_VERIFICATION_ROOT = 'D:\data\latent_group_verification_mvp'
$env:COST_AWARE_CERTIFICATION_ROOT = 'D:\data\cost_aware_certification_2026-08-11'
```

Compatibility defaults may exist in `src/paths.py`; portable deployments should
set the environment variables explicitly.

## One-shot result boundary

Formal truth-opening stages are guarded because their evidence timing cannot be
recreated after truth has been accessed. Infection Inspection, Wisdom of Crowds,
and Emotion Categorization therefore retain their original locked summaries and
method hashes. Later executions are reproductions, not new unopened-outcome
evaluations.

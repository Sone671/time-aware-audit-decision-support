# Code package manifest

This repository is the reproducibility package for the KBS time-aware audit
decision-support manuscript.  It intentionally does not redistribute downloaded
datasets, private truth, or source archives.

## Included

- `src/`: public screens, simultaneous-v3 implementation, cost planning,
  predicted-cost robustness, vendored finite-population utilities, and guards.
- `tests/`: unit and protocol guard tests.
- `outputs/**/summary.json` and selected design/protocol manifests: compact,
  machine-readable results and hashes.
- Root-level protocol and result reports documenting evidence tiers.

## Action-unit interpretation

The manuscript's formal population is a declared population of atomic
verification actions.  The current crowd-data replays use one logged response
as one action and charge its logged duration as a replay cost proxy.  A
deployment that shares a truth, adjudication, or setup cost across records must
bundle those records before applying the router and certificate; the supplied
record-level results must not be interpreted as subject-level or image-level
workload estimates.

## Excluded

- `external_candidates/`, `formal_confirmation_candidates/`, and downloaded
  archives.  These are large and may include licensing-restricted or private
  truth fields.
- Per-record recommendation CSVs, rendered page PNGs, caches, bytecode, and
  local LaTeX logs.
- The full `paper_kbs_v2/` manuscript directory, including source, references,
  compiled PDF, and build artifacts.

## External data configuration

For old-data development replays, set:

```powershell
$env:LATENT_GROUP_VERIFICATION_ROOT = 'D:\data\latent_group_verification_mvp'
$env:COST_AWARE_CERTIFICATION_ROOT = 'D:\data\cost_aware_certification_2026-08-11'
```

The current workstation paths are retained only as compatibility defaults in
`src/paths.py`.  The Infection Inspection formal unlock is one-shot; do not
rerun its prepare/unlock command after the private truth has been opened.

## Reproduction

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python src/run_predicted_cost_sensitivity.py `
  --output-root outputs/predicted_cost_v3_sensitivity_final `
  --replicates 100 --perturbations 10 --replicates-per-perturbation 10
```

The full sensitivity replay is development-only and takes several minutes.
Fresh confirmation results are preserved as locked artifacts; they are not
recomputed by the package smoke test.

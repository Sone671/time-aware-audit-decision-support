# Time-Aware Audit Decision Support

Reproducibility package for the study
``Time-Aware Audit Decision Support for Budgeted Label Verification``.

The repository contains the public decision layer, simultaneous-v3 certificate,
development robustness experiments, protocol reports, and tests. Downloaded
datasets, private truth, and manuscript files are deliberately kept outside
Git; see [CODE_PACKAGE_MANIFEST.md](CODE_PACKAGE_MANIFEST.md).

The manuscript treats each logged response as an atomic record-level replay
action.  If a deployment shares one truth or setup cost across several raw
records, those records must be bundled first and the public score, cost, and
loss recomputed at bundle level.  Logged durations are replay cost proxies;
they do not by themselves validate prospective auditor-time prediction.

Development package for cost-heterogeneity-gated, exact finite-population
review planning with genuine annotation time.

Key artifacts:

- `PROTOCOL.md`: CIFAR-N time-aware method;
- `GATED_PROTOCOL.md`: public CV router;
- `outputs/gated_portfolio/DEVELOPMENT_REPORT.md`: positive two-dataset result;
- `STORYLINES_DEVELOPMENT_PROTOCOL.md`: cross-modal stress test;
- `STORYLINES_DECISION.md`: mechanism-positive near miss;
- `STORYLINES_PILOT_CONFIRMATION_DECISION.md`: held-out confirmation NO-GO;
- `PHASE_RESULT.md`: current paper-level evidence boundary.

Run tests with:

```powershell
python -m pytest tests -q
```

Install the lightweight dependencies with:

```powershell
python -m pip install -r requirements.txt
```

The main development robustness replay is:

```powershell
python src/run_predicted_cost_sensitivity.py `
  --output-root outputs/predicted_cost_v3_sensitivity_final `
  --replicates 100 --perturbations 10 --replicates-per-perturbation 10
```

It requires the separately stored CIFAR-100N public/truth development bundle.
Configure its location with `LATENT_GROUP_VERIFICATION_ROOT`; do not rerun the
one-shot Infection Inspection unlock.

No artifact in this package authorizes Dopanim reuse or a confirmatory claim.

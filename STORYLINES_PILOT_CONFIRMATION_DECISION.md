# StoryLines pilot held-out confirmation decision

## Decision

NO-GO for the current confirmatory configuration.  The public gate selected
`risk_per_second` before `Experts_Pair` was read because cost CV was 1.007.

| Metric | Result | Gate |
|---|---:|:---:|
| Issued safety | 100% | PASS |
| Availability | 100% | PASS |
| Unsafe issued | 0% | PASS |
| Mean excess time budget | 1.52pp | PASS |
| Paired union-time reduction | 1.92% | FAIL (>=25%) |

All 300 target/replicate pairs were common safe certificates.  The risk-aware
route was statistically safe and more efficient relative to its truth oracle,
but the fixed 500-record sentinel dominated total annotation time in this
smaller pilot population.  Reordering the deterministic review set could not
remove that fixed cost.

No sentinel count, alpha, target, budget grid, score transform, cost mapping,
or CV gate is changed after this result.  The confirmation failure prevents a
standalone claim that the current method reduces end-to-end review time across
population scales.

The valid remaining claim is narrower: public cost heterogeneity can improve
the deterministic review component on sufficiently large high-heterogeneity
populations, but exact random certification imposes a scale-dependent cost
floor.

# Frozen v2 old-data development candidate

Date: 2026-08-11. Frozen after the sentinel grid screen and before the complete
three-dataset rerun. This is development evidence, not external confirmation.

## Public opportunity route

Use risk-per-second only when both conditions hold:

- complete public cost CV >= 0.50;
- the minimum public risk-equivalent time saving over budgets
  `{.5%, 1%, 2%, 5%, 10%, 20%}` is >= 40%.

Otherwise use score-time and abstain from an efficiency claim for that dataset.
Safety certification remains mandatory on both routes.

## Public cost-power sentinel planner

Let `t` be the strictest quality target, `alpha = 0.05/3`, `z` the normal
quantile at `1-alpha`, and relative target width `rho = 0.12`. Compute

```text
raw_m = z^2 (1 - t) / (rho^2 t)
```

Round upward to a multiple of 250, require at least 250 when capacity permits,
and cap at 1,500 records, 20% of the population, and the population size. This
normal approximation plans power only; issued certificates remain exact
one-sided hypergeometric bounds.

The formula yields 750 sentinels for both CIFAR-N datasets and 1,500 for
StoryLines-main.

## Unchanged components

- frozen dataset-specific public error-risk scores;
- risk-per-second and score-time ordering definitions;
- time grid `{0, .5%, 1%, 2%, 5%, 10%, 20%}`;
- dataset target grids;
- alpha `0.05/3` and MFSC fixed sequence;
- safety >= 90%, availability >= 30%, unsafe-issued rate <= 10%, and mean
  excess time <= 5pp.

Development requires every public-gated route to pass the four operating gates
and at least one opportunity-selected dataset to achieve >=25% pooled paired
union-time reduction. Fallback datasets are safety controls and are excluded
from the efficiency estimand because v2 explicitly abstains there.

No locked external confirmation dataset may be loaded by the candidate runner.

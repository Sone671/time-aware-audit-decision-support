# SATBench v2 formal confirmation protocol — locked pre-private

Lock date: 2026-08-11 (Asia/Shanghai). Status: **truth unopened**.

## Confirmatory scope

The sole fresh dataset is the three SATBench main experiments in the archive
whose SHA256 is
`3D38CC39F426B415CE426A33E9767C76F87F269BEEA35FE6515ADEB77E463D39`:

- `human-data/main/color-blur.txt`;
- `human-data/main/color-gray.txt`;
- `human-data/main/gray-noise.txt`.

The pooled population contains 97,118 valid timed human decisions from 148
observers. Tutorial events, empty responses, and nonpositive/nonfinite durations
are excluded. No supplementary experiment is eligible. No development or
previously locked dataset may be loaded.

The public audit passed: all 3,150 `(experiment, stimulus, deadline)` cells have
at least two valid responses (minimum 11). The filename is used only to compute
SHA256 and is never retained. Before private unlock, all fields outside the
public whitelist are byte-redacted before JSON decoding. In particular, values
of `category`, `correct`, and `correctResponse` have not been decoded.

## Frozen public score and cost

One audit record is one valid timed human classification decision.

- cost: raw `duration / 1000` seconds, with no trimming or winsorization;
- observed label: normalized nonempty `response`;
- stimulus identifier: `SHA256(filename)` with no filename parsing;
- deadline: the `TimedX` value belonging to the longest parent `sender_id`
  prefix;
- risk: `1 - (n_same_response - 1) / (n_cell - 1)`, where the cell is the same
  experiment, stimulus hash, and deadline;
- score-time ranking: descending risk, then frozen record order;
- risk-per-second ranking: descending risk/cost, then descending risk, then
  frozen record order.

The complete-public cost CV is 0.313491 and the minimum risk-equivalent time
saving over positive budgets `{0.5%, 1%, 2%, 5%, 10%, 20%}` is 27.6514%.
Both fail the frozen v2 intervention gates (CV at least 0.50 and minimum saving
at least 40%). The confirmatory route is therefore **score-time**, and SATBench
is excluded from the efficiency estimand. The unselected risk-per-second route
will not be evaluated against truth.

## Frozen confirmation design

- time grid: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}` of total review seconds;
- quality targets: `{35%, 45%, 55%}` residual error per full population;
- familywise alpha: `0.05`, allocated as `0.05 / 3` per target;
- sequential decision: the unchanged MFSC fixed sequence;
- sentinel planner: the frozen v2 public normal-width rule with strictest
  target 35%, relative width 0.12, 250-record rounding, minimum 250, maximum
  1,500, population cap 20%;
- planned uniform sentinel: 750 records (0.7723% of the population);
- sentinel repetitions: 100, base seed 20260811;
- certificate: exact one-sided hypergeometric upper bound; the normal
  approximation is used only for public sample-size planning;
- union cost: planned-review time plus nonoverlapping sentinel time.

Targets were selected before truth opening as a broad operational grid spanning
the public disagreement distribution. They are not estimates of private error.

## Frozen outcomes and decisions

For the selected score-time route:

- episode safety: at least 90% of repetitions have no unsafe issued target;
- availability: at least 30% of target/repetition recommendations are issued;
- unsafe-issued rate: at most 10%;
- mean excess time over the first truth-feasible grid point: at most 5
  percentage points, calculated only for safe issued recommendations with a
  feasible oracle.

If all four gates pass, the result is `SATBench fallback-safety GO`. If any gate
fails, the result is `SATBench formal NO-GO`. Because the public route abstained,
neither outcome may be called an external efficiency confirmation. A full v2
efficiency confirmation remains untested until a separate fresh dataset passes
both public intervention gates under these already-frozen thresholds.

No target, sentinel count, alpha, time grid, risk definition, route gate, pass
threshold, exclusion, or interpretation may change after this lock. Any parser
or method hash mismatch invalidates the run rather than triggering repair.

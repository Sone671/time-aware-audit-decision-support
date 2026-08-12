# Frozen external confirmation protocol: Collab-CXR expert decisions

Frozen on 2026-08-11 before loading `gt_binary_simple_us`.  The public audit
used only task identifiers, `group_ground_truth`, `probability`, `active_time`,
and the published data dictionary.

## Population and roles

- Dataset: Collab-CXR from the official OSF project `https://osf.io/z7apq/`.
- Exclude the five diagnostic-standard radiologists via the public
  `group_ground_truth` flag.
- Exclude case reads with missing or nonpositive `active_time` telemetry.
- The resulting 227 experimental radiologists produced 22,886 complete case
  reads.  Every read has exactly 104 unique pathology assessments, yielding
  2,380,144 finite-population audit records.
- Public noisy label: `probability >= 0.50` for a radiologist-case-pathology
  assessment.
- Private confirmation truth: `gt_binary_simple_us`, the simple binary
  diagnostic standard aggregated from the independent US ground-truth
  radiologists.  It is loaded only after `design_pre_private.json` is written.
- Genuine per-record cost: case `active_time / 104`.  This amortization makes
  the 104 pathology records sum exactly to their observed case-reading time;
  no positive time is clipped or winsorized.

## Frozen public risk and route

For elicited pathology probability `p`, public threshold-margin risk is
`1 - abs(2p - 1)`.  Score-time ranks by this risk and probability; risk per
second ranks by risk divided by amortized active seconds.  Public cost CV is
1.0016296597, so the frozen CV>=0.50 gate selects risk-per-second before the
diagnostic-standard column is opened.

## Frozen certification design

- Time budgets: `{0, .5%, 1%, 2%, 5%, 10%, 20%}` of total observed active time.
- Uniform sentinel: 500 pathology records without replacement.
- High-stakes targets: `{1%, 2.5%, 5%}` remaining record error.
- Exact one-sided hypergeometric bound, alpha `0.05 / 3`, and MFSC fixed
  sequence.
- 100 sentinel repetitions.
- Baseline has identical public risk, sentinel, targets, certificates, and time
  grid; only its ordering is score-time.

## Decision rule

The preselected route must have episode safety at least 90%, availability at
least 30%, unsafe-issued rate at most 10%, mean excess time at most 5pp, and at
least 25% mean paired union-time reduction versus score-time on common-safe
episodes.  No result may alter the population, cost amortization, probability
threshold, risk score, gate, sentinel, targets, alpha, time grid, or ordering.

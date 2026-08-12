# Frozen external confirmation protocol: CIFAR-10H record-level audit

Frozen on 2026-08-11 before loading `true_label` from the raw trial file.  The
public audit used only the README, `is_attn_check`, the published image index,
`chosen_label`, `reaction_time`, and `cifar10h-probs.npy`.

## Population and roles

- Dataset: CIFAR-10H, official repository
  `https://github.com/jcpeterson/cifar-10h`.
- Audit record: one cleaned normal human decision for one CIFAR-10 test image;
  repeated decisions are retained as separate finite-population records.
- Public noisy label: `chosen_label`.
- Public image-level human distribution: the repository's `cifar10h-probs.npy`.
- Private confirmation truth: the raw trial's `true_label`, loaded only after
  `design_pre_private.json` is written.
- Genuine record cost: the logged positive `reaction_time` in seconds.  The
  twelve nonpositive normal-trial values are excluded as invalid telemetry;
  all positive values, including long waits, are retained without clipping or
  winsorization.

The released CSV calls the image index `cifar10_test_test_idx`, although the
README calls it `cifar10_test_set_idx`; the actual CSV field is used and the
mapping is checked against all 10,000 image indices.

## Frozen public risk and route

For record `i` with chosen class `c_i`, let `p_i` be the human probability of
that class in the image-level soft-label matrix.  Public risk is
`1 - p_i`; high risk means the individual choice is rare among human raters.
Score-time ranks by risk.  Risk-per-second ranks by risk divided by the logged
positive response time.  The public cost CV is 6.0040870446, so the frozen gate
selects risk-per-second before `true_label` is loaded.

## Frozen certification design

- Time budgets: `{0, .5%, 1%, 2%, 5%, 10%, 20%}` of total logged seconds.
- Uniform sentinel: 500 records, sampled without replacement.
- Targets: `{5%, 7.5%, 10%}` remaining record error.
- Exact one-sided hypergeometric bound with alpha `0.05 / 3` and MFSC fixed
  sequence.
- 100 sentinel repetitions.
- Baseline uses the same public risk, sentinel, certificate, targets, and time
  grid, changing only the ordering to score-time.

## Decision rule

The preselected public route must have episode safety at least 90%, availability
at least 30%, unsafe-issued rate at most 10%, mean excess time at most 5pp, and
at least 25% mean paired union-time reduction over score-time on common-safe
episodes.  No outcome may alter the cleaned population, cost treatment, risk
definition, gate, sentinel, targets, alpha, prefix grid, or ordering.

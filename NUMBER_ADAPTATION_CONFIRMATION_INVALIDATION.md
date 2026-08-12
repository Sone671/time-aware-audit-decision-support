# Number-Adaptation fresh-confirmation invalidation

Date: 2026-08-12. Status: **exploratory structural probe only; not eligible for
fresh simultaneous-v3 confirmation**.

## Why the candidate was promising

Zenodo `10.5281/zenodo.15615038` is openly licensed under CC-BY-4.0 and
contains 30 participants, trial-level binary responses, and trial-level RT in
seconds. The source tables use a stable six-column schema. A closed-column
export probe found 11,470 raw trials, 1,206 equality trials, 10,264 retained
non-equality rows, and 85 exact stimulus-condition keys. These figures are
structural observations only; they are not confirmation results.

## Invalidation event

Before a complete public-only lock was frozen, the exploratory MATLAB exporter
loaded and used `reference_n`, `test_n`, and `adapter_n` to:

1. construct opaque condition IDs; and
2. exclude trials with `test_n == reference_n`.

The reference/test numerosity relation directly determines the physical
correct direction of the two-alternative judgment. Therefore these fields are
not merely harmless identifiers under the untouched-truth rule. This is a
pre-lock truth/design exposure.

The generated `public_trials.csv` is kept only as a development artifact. Its
route, disagreement, cost, and any later truth-based evaluation must not be
reported as fresh external confirmation. No simultaneous-v3 method episodes
were run on it.

## Retained value

The candidate remains a strong design lead if a future collection or a new
release provides a genuinely pre-locked redaction. The required redaction
would have to be created without exposing the physical stimulus relation to
the screening process, for example by a depositor-supplied opaque trial key
plus response and RT table, with a separately held condition-to-truth map.

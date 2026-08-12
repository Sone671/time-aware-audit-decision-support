# Frozen external confirmation protocol: ImageNet-16H human decisions

Frozen on 2026-08-11 before loading `image_category_int` or `correct` from the
behavioral CSV.  The public audit used only record/image identifiers,
`participant_classification_int`, `confidence_int`, `classification_time`, and
the OSF metadata.

## Population and roles

- Dataset: ImageNet-16H behavioral data from the official OSF project
  `https://osf.io/2ntrf/`.
- Population: all 28,997 uniquely identified human classification decisions
  covering 4,800 noisy ImageNet stimuli and 145 participants.
- Public noisy label: `participant_classification_int`.
- Private confirmation truth: `image_category_int`, loaded only after the
  pre-private design artifact is written.  The redundant `correct` field is not
  loaded or used.
- Genuine review cost: positive `classification_time / 1000` seconds.  The
  separate confidence-reporting time is excluded because the audit action is
  label classification; no positive classification time is clipped or
  winsorized.

## Frozen public risk and route

The experiment records three self-confidence levels, `confidence_int` in
`{1, 2, 3}`.  Public error risk is

```text
1 - (confidence_int - 1) / 2
```

so low, medium, and high confidence map to risks 1, 0.5, and 0.  Score-time
ranks by this risk with original record order as the deterministic tie break;
risk-per-second ranks by risk divided by classification seconds.  The public
cost CV is 4.6950014906, so the frozen gate selects risk-per-second before
image truth is loaded.

## Frozen certification design

- Time budgets: `{0, .5%, 1%, 2%, 5%, 10%, 20%}` of total classification time.
- Uniform sentinel: 500 records without replacement.
- Targets: `{15%, 20%, 25%}` remaining record error.
- Exact one-sided hypergeometric bound, alpha `0.05 / 3`, and MFSC fixed
  sequence.
- 100 sentinel repetitions.
- Baseline uses the identical public risk, sentinel, certificates, targets, and
  time grid; only its ordering is score-time.

## Decision rule

The preselected route passes only with episode safety at least 90%, availability
at least 30%, unsafe-issued rate at most 10%, mean excess time at most 5pp, and
at least 25% mean paired union-time reduction versus score-time on common-safe
episodes.  No outcome may change the population, cost field, risk mapping, CV
gate, sentinel, target grid, alpha, time grid, or ordering.

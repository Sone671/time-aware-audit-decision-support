# Dopanim outcome-blind simultaneous-v3 public-screen protocol

Date frozen: 2026-08-12 (Asia/Shanghai). Status: public screen only. Dopanim
was explicitly kept closed in the earlier project artifacts. This protocol
does not authorize downloading, decoding, previewing, or inferring any
per-image ground-truth class.

## Fixed source and evidence boundary

- dataset: Dopanim, Zenodo concept DOI `10.5281/zenodo.11479589`;
- fixed version: `10.5281/zenodo.14016659` (2024-10-31 release);
- record license: CC-BY-NC-SA-4.0;
- annotation-file license stated by the depositors: CC-BY-NC-4.0;
- public file: `annotation_data.json`, 40,944,116 bytes, upstream MD5
  `c0218a3a1a33b6ec29fdd78158ba6270`;
- private file: `task_data.json`, 17,768,520 bytes, upstream MD5
  `a6c2d62a3bf1e4fe3d410f8d1572322d`.

Only `annotation_data.json` may be downloaded for the public screen. The
private file, image archives, image-directory class names, and API previews of
those files must remain unopened. The public dataset description and paper
report only aggregate accuracy (about 67%); that aggregate is not used to
construct a score or route. No per-image truth value has been decoded in this
project.

## Frozen public parser

The official datasheet and loader declare the annotation file as a JSON object
indexed by annotation identifier. Each accepted annotation must expose exactly
the public quantities needed here:

- `observation_id`: image/task identifier;
- `annotator_id`: pseudonymous annotator identifier;
- `likelihoods`: a mapping over the documented 15 animal classes;
- `annotation_time`: genuine per-image annotation time in seconds.

Additional fields are ignored only if their names do not contain any of
`truth`, `true`, `gold`, `target`, `taxon`, `class`, `label`, or `split`.
Encountering a forbidden field name aborts before its value is accessed. All
15 likelihood keys must match the class vocabulary published in the official
loader. Likelihood values must be finite and nonnegative, with a positive
maximum. Time must be positive and finite. No trimming, replacement,
winsorization, or annotator-wise outlier correction is allowed, even though
the official model loader applies a 95th-percentile replacement for a separate
benchmarking purpose.

The observed human decision is the canonical sorted set of every class tied at
the maximum likelihood. This preserves ties without a random or
truth-dependent tie-break. Repeated submissions by the same annotator for the
same observation retain the earliest JSON insertion order; subsequent repeats
are excluded before risk construction.

## Frozen public score and routing rule

One retained annotation is one audit unit. The public comparison cell is
`observation_id`. Each eligible observation must contain at least two distinct
annotators after deduplication. Public risk is the leave-one-annotator-out
fraction of peer maximum-label sets that differ from the focal response:

`1 - (same-response count - 1) / (valid cell size - 1)`.

The score-time order is descending public risk, then frozen JSON order. The
risk-per-second order is descending risk divided by raw annotation seconds,
then descending risk, then frozen JSON order. Public opportunity is evaluated
at total-time fractions `{0.5%, 1%, 2%, 5%, 10%, 20%}`.

The unchanged intervention gate selects `risk_per_second` only when:

1. complete-public cost CV is at least 0.50;
2. minimum risk-equivalent time saving across all six budgets is at least 40%;
3. every retained cell has at least two distinct annotators;
4. no forbidden field, invalid response, invalid duration, or unresolved
   duplicate remains;
5. file length and hashes match the fixed source.

Otherwise the route freezes to `score_time`, and Dopanim is not used for an
efficiency-confirmation claim. A public pass does not authorize truth opening.

## Post-public lock required before any truth access

If the public route passes, a separate executable formal protocol must freeze
the parser for `task_data.json`, exact observation alignment, response-versus-
singleton-truth loss, source hashes, targets `{0.35, 0.45, 0.55}`, 750 uniform
sentinels, 100 repetitions, base seed, the seven-budget simultaneous bound
`beta=0.05` with `alpha_cert=0.05/7`, and the existing four operating gates.
The formal runner must also prove that the private file was absent during this
public screen. Only then may an explicit, one-use unlock authorize downloading
and decoding the private file.

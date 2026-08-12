# Frozen external confirmation protocol: NYT topical relevance

Frozen on 2026-08-11 before loading `nist_rel_binary` from either main-result
table.  The public design audit used only file names, headers, row identifiers,
`duration`, `max_relevance_score`, and `crowd_rel_binary`.

The first pre-private validation attempt stopped before writing a design or
loading NIST truth: the released Bin2 `crowd_rel_binary` disagrees with the
repository notebook's published `max_relevance_score >= 0.40` rule on 560 of
3,093 records (Bin1 has zero disagreements).  This corrected pre-private freeze
therefore recomputes the deployed label from the published rule and treats the
inconsistent derived column as release metadata only.  It is not used by the
method or evaluation.

## Population and roles

- Dataset: CrowdTruth NYT Topical Relevance, Zenodo DOI
  `10.5281/zenodo.1478495`.
- Population: the disjoint union of Main Bin1 and Main Bin2 NIST-assessed
  query-document pairs (2,853 + 3,093 = 5,946 records).
- Deployed public label: `max_relevance_score >= 0.40`, as specified in both
  main-experiment notebooks.
- Private confirmation truth: `nist_rel_binary`, loaded only after the
  pre-private design artifact is written.
- Genuine public review cost: the authors' CrowdTruth aggregate `duration` in
  seconds for each query-document pair.  No clipping, winsorization, or
  outcome-dependent cost transformation is permitted.

## Frozen risk and route

Let `p = max_relevance_score` and let the published crowd decision threshold be
`t = 0.40`.  The public threshold-margin risk is

```text
p / t                    if p < t
(1 - p) / (1 - t)        otherwise
```

This is the threshold-general form of `1 - abs(2p - 1)` used when `t = 0.50`.
Score-time ranks by this risk; risk-per-second ranks by risk divided by genuine
seconds.  The public route is risk-per-second iff the population cost CV is at
least 0.50, otherwise score-time.  The audited public CV is 0.5917902050, so
risk-per-second is selected before NIST truth is loaded.

## Frozen certification design

- Time budgets: `{0, .5%, 1%, 2%, 5%, 10%, 20%}` of total genuine seconds.
- Uniform sentinel: 500 records, sampled without replacement.
- Targets: `{15%, 20%, 25%}` remaining population error.
- Exact one-sided hypergeometric bound with alpha `0.05 / 3`.
- MFSC fixed sequence and 100 sentinel repetitions.
- Baseline: identical score, sentinel, certificates, targets, and time grid;
  only the ordering is score-time rather than risk-per-second.

## Decision rule

Confirmation passes only if the preselected public route has:

- episode safety at least 90%;
- availability at least 30%;
- unsafe-issued rate at most 10%;
- mean excess time budget at most 5 percentage points; and
- at least one common-safe paired episode with mean union-time reduction of at
  least 25% versus score-time.

No outcome may change the population, threshold, score, cost rule, CV gate,
sentinel size, targets, alpha allocation, time grid, or ordering rule.

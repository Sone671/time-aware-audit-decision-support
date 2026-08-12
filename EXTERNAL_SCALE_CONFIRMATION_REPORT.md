# External scale confirmation report

Date: 2026-08-11.

## Decision

The frozen v1 heterogeneity-gated risk-per-second method is **NO-GO as a
confirmed KBS method package**. Increasing the population resolves the extreme
sentinel cost floor seen in the StoryLines pilot, but population size alone is
not sufficient. None of the four additional frozen external confirmations
passes every prespecified gate on the same dataset.

The mechanism remains materially positive: all selected routes have 99--100%
episode safety, and three large datasets have high availability with nonzero
genuine-time savings. The failure modes are now localized rather than
ambiguous.

## Frozen confirmation results

| Dataset | Records | 500-sentinel share | Cost CV | Private error | Safety | Availability | Mean excess | Paired time reduction | Strict result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| StoryLines pilot | 1,477 | 33.85% | 1.007 | 20.45% | 100% | 100% | 1.52pp | 1.92% (300 pairs) | FAIL savings |
| NYT Topical Relevance | 5,946 | 8.41% | 0.592 | 38.95% | 100% | 3.33% | 0.00pp | not estimable (0 pairs) | FAIL availability |
| ImageNet-16H decisions | 28,997 | 1.72% | 4.695 | 21.63% | 99% | 97.67% | 6.01pp | 39.46% (179 pairs) | FAIL excess |
| CIFAR-10H records | 514,188 | 0.097% | 6.004 | 5.13% | 100% | 100% | 1.00pp | 19.21% (300 pairs) | FAIL savings |
| Collab-CXR pathology records | 2,380,144 | 0.021% | 1.002 | 3.27% | 100% | 69.67% | 4.70pp | 16.57% (209 pairs) | FAIL savings |

The StoryLines main experiment remains development-only: 7,778 records,
100% safety, 73.33% availability, 6.84pp excess, and 29.00% time reduction.

## What the scale test establishes

1. **The pilot diagnosis was partly correct.** A fixed 500-record sentinel
   consumes at least one third of the StoryLines pilot population, mechanically
   limiting any union-time saving. Larger populations remove this floor:
   ImageNet-16H reaches 39.46% paired time reduction.
2. **Scale is not sufficient.** Savings are not monotone in population size.
   CIFAR-10H and Collab-CXR are two to three orders of magnitude larger than the
   pilot but save only 19.21% and 16.57%.
3. **The current CV gate is incomplete.** Cost heterogeneity says that savings
   are possible, but not whether the public risk and cost frontiers are aligned.
   All three record-level datasets have high CV, yet their realized benefits
   differ sharply.
4. **The exact certificate is reliable but sometimes conservative.**
   ImageNet-16H meets safety, availability, unsafe-rate, and savings gates, but
   misses the 5pp excess gate by 1.01pp. The strict 15% target contributes the
   largest excess; this is reported diagnostically and was not removed after
   truth inspection.
5. **No safety failure is being hidden.** The worst selected-route episode
   safety is 99%, and the largest unsafe-issued rate is 0.34%.

## Data-quality observations

- The NYT release's derived `crowd_rel_binary` disagrees with the repository
  notebook's stated `max_relevance_score >= 0.40` rule on 560 of 3,093 Bin2
  records. The frozen confirmation recomputed the notebook rule before NIST
  truth was loaded and recorded the released column as unused metadata.
- The CIFAR-10H README names the image index `cifar10_test_set_idx`, while the
  released CSV uses `cifar10_test_test_idx`. Twelve nonpositive reaction times
  were excluded before truth was loaded; all positive long waits were retained.
- Collab-CXR case active time was divided across exactly 104 unique pathology
  rows, preserving total observed review time and preventing 104-fold cost
  duplication.

## Recommended next method stage

Stop adding datasets to v1. The next method should address the two identified
gaps using public information only:

1. **Public opportunity gate.** Supplement cost CV with an outcome-free
   comparison of the cumulative public-risk/time frontiers of score-time and
   risk-per-second. Use risk-per-second only when its public frontier advantage
   exceeds a frozen development threshold; otherwise abstain from the efficiency
   claim or fall back to score-time.
2. **Cost-power sentinel planner.** Choose the uniform sentinel count before
   outcomes from population size, the public cost distribution, target levels,
   alpha, and exact hypergeometric width. The goal is to avoid both the small-N
   cost floor and the large-N certificate conservatism while retaining exact
   validity.

Develop both components only on the old CIFAR-N and StoryLines-main development
sets. The four newly opened datasets in this report are locked diagnostics and
must not become tuning sets for a future confirmation claim. Dopanim remains
closed.

## Artifacts

- `TOPICAL_RELEVANCE_CONFIRMATION_PROTOCOL.md` and
  `outputs/topical_relevance_confirmation/summary.json`
- `IMAGENET16H_CONFIRMATION_PROTOCOL.md` and
  `outputs/imagenet16h_confirmation/summary.json`
- `CIFAR10H_RECORD_CONFIRMATION_PROTOCOL.md` and
  `outputs/cifar10h_record_confirmation/summary.json`
- `COLLAB_CXR_CONFIRMATION_PROTOCOL.md` and
  `outputs/collab_cxr_confirmation/summary.json`

All project tests pass. Computational caching was verified to reproduce the
pre-optimization ImageNet-16H episode rows exactly for the same repetitions.

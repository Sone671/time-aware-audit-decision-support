# Time-Aware Audit Decision Support: Stage Result

## Outcome

The new direction is viable as a KBS method-development package, but it is not
yet confirmatory.

The method keeps a frozen public error-risk score and changes only the decision
layer: when public review-time heterogeneity is high (`CV >= 0.50`), review by
risk per second; otherwise retain the original score order.  Every selected
plan is still checked by an exact finite-population certificate.

## Development evidence

| Dataset | Cost CV | Gated route | Safety | Availability | Excess time | Time reduction | Dataset gate |
|---|---:|---|---:|---:|---:|---:|:---:|
| CIFAR-100N | 0.688 | risk per second | 100% | 100% | 3.82pp | 41.89% | PASS |
| CIFAR-10N | 0.317 | score-time fallback | 100% | 97.78% | 3.99pp | 0% | PASS |
| StoryLines | 0.774 | risk per second | 100% | 73.33% | 6.84pp | 29.00% | FAIL |

The frozen two-CIFAR gated portfolio contains 132 common safe episodes and
reduces real union time by 27.93%, exceeding the 25% gate.  Adding the 14
StoryLines common safe episodes gives a descriptive pooled reduction of
28.03%; StoryLines remains a near-miss because excess time exceeds 5pp.

## Separation from the ICLR diagnostic manuscript

- no WGA, group audit, retraining, repair utility, or test performance;
- no new detector claim: NoiseScore or crowd uncertainty is a frozen input;
- the primary outcome is genuine annotator seconds, not item count;
- the contribution is a cost-heterogeneity router plus exact certification;
- the decision system may review more records while consuming less human time.

## Evidence boundary

CIFAR-100N and CIFAR-10N are old development data.  StoryLines was downloaded
from Zenodo DOI `10.5281/zenodo.1478508` and contains genuine start/end times,
but its aggregate truth was inspected during feasibility analysis.  Therefore
none of the three is an untouched confirmation for the final KBS claim.

The only authorized next empirical step is an independent public dataset with
per-task or per-batch annotation time, frozen cost mapping, and untouched
ground truth.  Dopanim remains excluded.

## Held-out pilot confirmation

The disjoint StoryLines pilot experiment was frozen before its `Experts_Pair`
column was opened and run for 100 sentinel repetitions.  Its public CV gate
selected risk per second.  Safety, availability, unsafe rate, and excess-time
gates all passed, but paired union-time reduction was only 1.92% over 300
common safe certificates.  The fixed 500-record sentinel dominated cost in the
smaller pilot population.  The current cross-scale confirmation decision is
therefore **NO-GO**; see `STORYLINES_PILOT_CONFIRMATION_DECISION.md`.

## Additional cross-scale confirmations

Four further datasets were frozen and evaluated for 100 sentinel repetitions:

| Dataset | Population | Safety | Availability | Excess | Time reduction | Result |
|---|---:|---:|---:|---:|---:|:---:|
| NYT Topical Relevance | 5,946 | 100% | 3.33% | 0.00pp | N/A | FAIL |
| ImageNet-16H | 28,997 | 99% | 97.67% | 6.01pp | 39.46% | FAIL |
| CIFAR-10H record level | 514,188 | 100% | 100% | 1.00pp | 19.21% | FAIL |
| Collab-CXR pathology level | 2,380,144 | 100% | 69.67% | 4.70pp | 16.57% | FAIL |

The pilot's small population was a real limiting factor, but not the sole
failure cause. Larger datasets reveal two further gaps: the CV-only gate does
not predict whether public risk and cost are aligned strongly enough for 25%
savings, and the fixed 500 sentinel can still make the exact certificate more
than 5pp conservative. The frozen v1 method remains NO-GO for a confirmed KBS
method paper. Full analysis and the locked-data boundary are in
`EXTERNAL_SCALE_CONFIRMATION_REPORT.md`.

## V2 development

V2 replaces the CV-only router with a public opportunity gate and replaces the
fixed 500 sentinel with a target-aware public cost-power planner. The complete
100-repetition old-data rerun selected risk-per-second only for CIFAR-100N and
used score-time fallback for CIFAR-10N and StoryLines-main.

| Dataset | Route | Sentinel | Safety | Availability | Excess | Efficiency |
|---|---|---:|---:|---:|---:|---:|
| CIFAR-100N | risk/second | 750 | 97.67% | 100% | 2.60pp | 45.13% |
| CIFAR-10N | score-time | 750 | 99.33% | 99.89% | 3.19pp | abstained |
| StoryLines-main | score-time | 1,500 | 100% | 71.33% | 3.36pp | abstained |

All selected routes pass, and the opportunity-selected efficiency route exceeds
the 25% saving gate over 885 common-safe pairs. V2 therefore receives an
old-data **development GO**. It remains non-confirmatory and requires a new
untouched external dataset; see `V2_DEVELOPMENT_REPORT.md`.

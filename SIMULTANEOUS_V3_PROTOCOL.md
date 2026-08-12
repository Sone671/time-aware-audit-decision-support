# Simultaneous-v3 corrected reanalysis protocol

Date: 2026-08-12. Status: post-unlock mathematical correction; no claim of a
fresh private confirmation.

## Scope

This protocol corrects the multi-budget coverage gap in the locked v2 method.
It does not overwrite, relabel, or modify any v2 artifact. Public scores,
rank-priority-per-second orders, route gates, target grids, time budgets,
sentinel planner, random seeds, loss definitions, and operating gates remain
unchanged.

## Simultaneous certificate

The fixed time-budget grid is
`{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`, so `L=7`. The desired familywise bound is
`beta=0.05`. Every fixed prefix uses the exact hypergeometric upper bound at
local level

`alpha_cert = beta / L = 0.007142857142857143`.

One uniform sentinel and one upper-bound curve are shared by all three targets
within a dataset, method, score seed, and sentinel repetition. Because target
selection does not create a new confidence-bound failure event, there is no
additional division by the number of targets. The largest-to-smallest fixed
sequence remains an operational choice rule, while simultaneous validity comes
from the complete budget-grid allocation.

## Planning parameter

The unchanged public v2 sentinel planner remains a power/cost heuristic only.
Its normal-tail parameter is not the certification alpha and supplies no
coverage claim. Thus the frozen counts remain 750 for WhichDog, SATBench, and
the CIFAR datasets, and 1,500 for StoryLines-main.

## Evaluation

Each selected route must retain:

- empirical draw-family safety at least 90%;
- cell availability at least 30%;
- unsafe-issued rate at most 10%;
- mean excess time at most 5 percentage points.

An intervention-positive route additionally requires at least one common-safe
score-time comparison and at least 25% mean paired union-time reduction.

The primary corrected validation datasets are WhichDog (selected
risk-per-second) and SATBench (selected score-time). CIFAR-100N, CIFAR-10N, and
StoryLines-main are old-data development reanalyses. All underlying truths were
already opened before this v3 protocol; therefore no v3 result may be described
as a fresh external confirmation.

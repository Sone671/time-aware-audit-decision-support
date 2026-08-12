# CrowdTruth StoryLines development decision

## Status

Mechanism-positive but protocol NO-GO.  StoryLines cannot be presented as a
fresh confirmation because aggregate truth feasibility was inspected before
the smoke protocol was written.

## Result

| Metric | Risk per second | Score-time baseline |
|---|---:|---:|
| Issued safety | 100% | 100% |
| Availability | 73.3% | 46.7% |
| Unsafe issued | 0% | 0% |
| Mean excess time budget | 6.84pp | 11.14pp |
| Mean union time | 18.85% | 22.20% |

On 14 common safe certificates, risk-per-second reduced real union time by
29.00%, passing the 25% cost gate.  It missed the frozen 5pp excess-time gate,
so the dataset does not pass overall.

The result nevertheless supports cross-modal plausibility: the time-saving
mechanism transfers from image-label correction to text causal-relation
crowdsourcing while preserving exact finite-population safety.  No target,
budget grid, score transform, or sentinel size is changed after this result.

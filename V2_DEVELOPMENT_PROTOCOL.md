# V2 development protocol: public opportunity and certificate power

Date: 2026-08-11. This is an explicitly non-confirmatory old-data development
stage. Only CIFAR-100N, CIFAR-10N, and StoryLines-main may be used for method
selection. The four datasets in `EXTERNAL_SCALE_CONFIRMATION_REPORT.md` are
locked and unavailable for tuning.

## Component A: public opportunity frontier

For each positive time budget in `{.5%, 1%, 2%, 5%, 10%, 20%}`:

1. measure the public risk mass captured by the score-time prefix;
2. find the minimum risk-per-second prefix time needed to capture at least that
   public risk mass;
3. record `1 - rps_time / score_time_budget`.

The opportunity score is the mean of the six savings and the conservative
opportunity score is their minimum. Both use only frozen public risk and cost.
V2 may select risk-per-second only when cost CV is at least 0.50 and the frozen
opportunity threshold is met.

## Component B: sentinel cost-power screen

Screen uniform sentinel counts `{250, 500, 750, 1000, 1250, 1500}` without
changing the exact hypergeometric certificate, alpha `0.05/3`, MFSC sequence,
time grid, targets, or ordering. Evaluate 100 repetitions on StoryLines-main and
30 repetitions over each of three CIFAR-100N seeds. CIFAR-10N is reserved for
checking the final fallback configuration.

Candidate configurations must retain:

- safety >= 90%;
- availability >= 30%;
- unsafe-issued rate <= 10%;
- mean excess time <= 5pp;
- paired union-time reduction >= 25% whenever risk-per-second is selected.

The screen may identify a public sentinel planning formula, but may not choose a
different fixed count for each dataset using private outcomes.

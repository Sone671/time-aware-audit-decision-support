# Development protocol: Heterogeneity-Gated Time-Aware Audit

Date: 2026-08-11.

This rule is constructed after the CIFAR-100N and CIFAR-10N old-development
screens and is therefore not confirmatory evidence.  Its role is to decide
whether the time-aware direction merits a genuinely fresh external dataset.

## Public gate

Compute the coefficient of variation of the complete public per-record review
cost vector before any private response is opened:

- if `CV >= 0.50`, use `risk_per_second`;
- otherwise, use the original `score_time` order.

The 0.50 boundary denotes high cost heterogeneity and is fixed for all future
datasets.  The gate uses no error label, group, WGA, retraining outcome,
certificate result, or test metric.  Once a route is selected, the sentinel,
target grid, exact hypergeometric certificate, and MFSC fixed sequence remain
unchanged from `PROTOCOL.md`.

## Development gate

Both selected dataset routes must pass safety, availability, unsafe-rate, and
5pp excess-time gates.  Across common safe episodes, the gated portfolio must
reduce union review seconds by at least 25% versus always using `score_time`.

Passing only authorizes search for an independent public annotation-time
dataset.  CIFAR-N results remain development evidence, and Dopanim remains
closed for tuning or confirmation.

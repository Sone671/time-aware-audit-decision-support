# SATBench public-only admissibility audit

Date: 2026-08-11. Truth status: **unopened**.

The byte-redacted public parser recovered 97,118 valid main-experiment timed
decisions from 148 observers. It discarded 7,400 tutorial trials, 58,267 empty
responses, and 15 invalid-duration trials. All 3,150 public risk cells contain
at least two records; sizes range from 11 to 57 (median 30). The original
filename is not retained.

The pooled raw response-time cost has mean 1.0963 seconds, population CV 0.3135,
and range 0.0075–6.6126 seconds. Leave-one-out disagreement risk has mean 0.5365
and median 0.5484.

The public risk-equivalent time savings for risk-per-second relative to
score-time are 76.39%, 72.21%, 64.47%, 52.88%, 44.58%, and 27.65% at the frozen
positive time budgets. The minimum is below 40%, and the cost CV is below 0.50.
The frozen v2 route is therefore **score-time fallback**, with no SATBench
efficiency claim.

Public admissibility is GO. This authorizes locking and preparing a fallback
safety confirmation. It does not by itself authorize calling SATBench a full
external efficiency confirmation.

Machine-readable evidence: `outputs/satbench_public_audit/public_audit.json`.

# CrowdTruth Event-Extraction formal-candidate invalidation

Date: 2026-08-11 (Asia/Shanghai).

## Decision

The CrowdTruth Event-Extraction dataset is permanently ineligible for the v2
formal efficiency confirmation. No formal method episode was run.

## Cause and timing

The public screen had already completed with `truth_loaded=false` and remains
a valid outcome-blind result. During a later inspection of an existing guard,
the same command also printed the header and first data row of
`TE3-Gold_events.csv`. That row included one `Is Event` value. This occurred
before the dataset-specific executable confirmation runner and final method
hash lock existed.

The exposure was small and did not affect the already-written public metrics,
but the protocol is deliberately stricter than an influence assessment:
opening any private truth before the complete lock invalidates the candidate.

## Consequences

- Do not decode another Gold or Platinum truth value from this repository.
- Do not regenerate the pre-private lock.
- Do not run score-time or risk-per-second episodes on its expert truth.
- Retain the public GO only as exploratory evidence of cost heterogeneity and
  public risk-per-second opportunity.
- Use a different untouched, clearly licensed dataset for formal confirmation.

The formal design and method-lock JSON files have been marked invalidated, and
the preparation script now refuses regeneration.

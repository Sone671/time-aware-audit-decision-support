# SATBench v2 formal confirmation result

Date: 2026-08-11. The user authorized the one-shot truth unlock after the
pre-private lock. Only the boolean `correct` field was loaded; `category` and
`correctResponse` were not used.

## Decision

**SATBench fallback-safety GO.** The frozen public route was `score_time`.
The public gate had already rejected risk-per-second intervention (cost CV
0.3135; minimum public opportunity 27.65%), so this run does not test or claim
efficiency.

| Metric | Frozen threshold | Result |
|---|---:|---:|
| Episode safety | >=90% | 100% |
| Availability | >=30% | 100% |
| Unsafe-issued rate | <=10% | 0% |
| Mean excess time | <=5pp | 4.25pp |
| Formal episodes | 300 | 300 |

The 300 episodes are 100 sentinel repetitions at each of the 35%, 45%, and
55% targets. Per-target mean excess was 8pp, 4pp, and 0pp respectively; the
frozen gate is the pooled mean across all target/repetition episodes, which is
4.25pp. This is reported explicitly rather than introducing an unregistered
per-target veto.

The mean recommended union-time fraction was 8.30%, and the mean union-item
fraction was 9.96%. The output contains only `score_time` recommendations;
the unselected risk-per-second route was not evaluated against truth.

## Interpretation for the research package

The result confirms the safety-controlled fallback branch on a fresh,
multi-experiment human classification benchmark. It does not establish an
external efficiency gain, because the public intervention gate correctly
abstained before truth was opened. A separate fresh dataset that passes both
public intervention gates is still required for the efficiency claim.

## Locked artifacts

- Protocol: `V2_FORMAL_CONFIRMATION_PROTOCOL.md`.
- Public audit: `outputs/satbench_public_audit/public_audit.json`.
- Pre-private design and method lock: `outputs/satbench_formal_confirmation/`.
- Formal summary: `outputs/satbench_formal_confirmation/summary.json`.
- Recommendations: `outputs/satbench_formal_confirmation/recommendations.csv`.

The pre-private lock remains recorded with `truth_loaded=false`; the post-run
`design.json` records `truth_loaded=true` and `truth_field_used=correct (boolean
only)`. No protocol, threshold, parser, or method file was changed between
lock verification and confirmation.

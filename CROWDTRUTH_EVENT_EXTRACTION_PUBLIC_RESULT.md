# CrowdTruth Event-Extraction public v2 screen result

Date: 2026-08-11 (Asia/Shanghai). Status: **public intervention GO remains
valid; formal candidate subsequently invalidated**.

## Post-screen invalidation

After this public screen had been completed, but before a complete executable
formal lock existed, an inspection command decoded the header and first data
row of `TE3-Gold_events.csv`, including one `Is Event` value. This does not
change any public metric below because the public output already existed, but
it violates the untouched-truth requirement for later confirmation. This
dataset must therefore never be used for a formal v2 efficiency decision.

## Decision

The frozen event task passes both public intervention gates and selects
`risk_per_second`:

| Metric | Frozen gate | Result |
|---|---:|---:|
| Complete-public cost CV | >= 0.50 | 2.078436 |
| Minimum six-budget opportunity | >= 40% | 74.1445% |
| Public records after blind structural filtering | — | 58,973 |
| Sentence cells | all repeated | 4,202 |
| Minimum / median / maximum workers per cell | >= 2 | 3 / 14 / 15 |
| Task-key coverage | complete | 4,202 / 4,202 |
| One-to-one unit/task mapping | required | 0 violations |

Budget-level public savings are 89.28%, 90.52%, 87.18%, 81.94%, 78.67%, and
74.14% for `{0.5%, 1%, 2%, 5%, 10%, 20%}`. The route is not a truth-based
claim; it is selected solely from worker disagreement and raw response time.

## Structural alignment and exclusions

The crowd file has 63,030 rows and 4,202 units, each initially with 15
distinct workers. The parser retained only public identifiers, timing, and
`all_events`; 19 other crowd columns were byte-redacted before decode.

Gold and Platinum token files were byte-redacted to five key columns before
decode. They contain 106,376 unique token keys across 4,226 sentence keys;
all 4,202 crowd sentence keys are covered, with no cross-split overlap or
duplicate token key. At the moment this public screen was generated, `Is Event`
and every other expert value were unopened; the post-screen invalidation above
records the later one-row exposure.

The predeclared exact-key filter excluded 2 invalid JSON rows, 4 malformed
response-span rows, and 4,051 rows containing at least one free-highlight span
not exactly equal to an expert token key. No fuzzy matching, phrase splitting,
or expert-label repair was used. All 4,202 cells remain represented after the
filter; there are no duplicate unit-worker records and no undersized cells.

## Blocking condition

The post-screen private peek permanently blocks formal confirmation, independent
of licensing. The repository also has no SPDX license declaration. The former
pre-private design is retained for audit only and is marked invalid; no safety,
availability, unsafe-rate, or paired-efficiency episode was run.

## Artifacts

- Public protocol: `V2_CROWDTRUTH_EVENT_EXTRACTION_PUBLIC_PROTOCOL.md`
- Public screen: `outputs/crowdtruth_event_extraction_public_screen/public_screen.json`
- Formal pre-private protocol: `V2_CROWDTRUTH_EVENT_EXTRACTION_FORMAL_PROTOCOL.md`
- Pre-private lock: `outputs/crowdtruth_event_extraction_formal_confirmation/`
- Outcome-blind parser: `src/crowdtruth_event_extraction_public.py`
- Public runner: `src/run_crowdtruth_event_extraction_public_screen.py`

The public result may be cited only as exploratory routing evidence. It is not
an external efficiency GO and cannot become one on this dataset.

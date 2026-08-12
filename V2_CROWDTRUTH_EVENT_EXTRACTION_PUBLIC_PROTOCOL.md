# CrowdTruth Event-Extraction public v2 screen — frozen outcome-blind protocol

Date: 2026-08-11 (Asia/Shanghai).

This candidate is screened under the unchanged gates in
`V2_FRESH_EFFICIENCY_SCREEN_PROTOCOL.md`. The screen may use expert token keys
only. It must not decode any expert event or time-expression value.

## Fixed source and task

- Repository: `https://github.com/CrowdTruth/Event-Extraction`
- Commit: `3d7596547944a3eec281676732eed2a22b412526`
- Archive SHA-256:
  `53c31eb8fba3520e9bba956ff9daa0c686852f2b380385ca1986f08f9db58e3c`
- Crowd file: `data/main_crowd_data/raw_data/all_crowd_event.csv`
- Key-only reference files: `data/TempEval3-data/TE3-Gold_tokens.csv` and
  `data/TempEval3-data/TE3-Platinum_tokens.csv`
- The event task is screened first. The time-expression task is not pooled
  with it and is not screened if the event task passes the public gates.
- No SPDX license is present in the repository. This is a mandatory blocker
  on private opening and formal use until clarified.

## Private-label firewall

Only `Doc Id`, `Sentence Id`, `Lowercase Token`, `Start Offset`, and
`End Offset` may be decoded from either expert token file. Every other field,
including `Is Event`, is cleared from each CSV record at byte level before the
record is decoded. No aggregate result file or event-only expert file may be
opened during this screen.

The public crowd parser similarly retains only identifiers, worker, timing,
task keys, taint status, and the observed `all_events` response.

## Exact structural alignment

- Cell: one CrowdFlower `_unit_id`, required to map one-to-one to the
  lower-cased `(doc_id, sentence_id)` task key.
- Response: the exact set of event spans in `all_events`.
- `no_event` is the empty set and is valid only when it occurs alone.
- A span is admissible only when its lower-cased text and integer start/end
  offsets exactly equal one expert token key in the same document and
  sentence.
- A worker row is excluded if its JSON is invalid, it mixes `no_event` with a
  span, any span is malformed, or any selected span lacks an exact key.
- There is no fuzzy text matching, offset repair, multi-token splitting, or
  use of expert labels to rescue a row.
- Missing/tainted identifiers and invalid or nonpositive durations are
  excluded. Duplicate unit-worker rows retain the earliest raw row.
- Every retained cell must contain at least two distinct workers, and all raw
  crowd task keys must remain represented after structural filtering.

## Frozen public quantities

- Cost: `_created_at - _started_at` in seconds, without trimming.
- Risk: leave-one-worker-out exact response-set disagreement within the cell.
- Tie order: original row order after deterministic filtering and
  deduplication.
- Budgets and public gates are exactly those in the parent protocol: cost CV
  at least `0.50` and minimum risk-equivalent time saving at least `40%` over
  `{0.5%, 1%, 2%, 5%, 10%, 20%}`.

If this public screen passes, a separate pre-private design lock is required.
Truth opening remains forbidden until the repository's reuse terms are
resolved.

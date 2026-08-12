# WhichDog public v2 efficiency screen protocol

Date frozen: 2026-08-12. This protocol is outcome-blind. No value from the
released `class` ground-truth column may be decoded before a complete
pre-private formal lock.

## Fixed source and byte schema

- Zenodo record: `10.5281/zenodo.7100698`;
- license: CC BY 4.0;
- archive: `whichdog.zip`, 16,249,318 bytes;
- archive SHA-256:
  `f74dde0f15867c2532ac028a98b0c27c41d18dc6063fc4fb51b397d57cbae150`;
- upstream MD5: `ec129ef90a31eb158537983c5ab0c5df`;
- annotation member: `whichdog_all_annots.csv`.

Zenodo declares the positional CSV schema as:
`image_id`, `is_candidate`, `labeler_id`, `time`, `answer`, `options`,
`assignment_id`, `sequence_point`, `class`. The ninth field is private. The
parser clears field position 9 at byte level in every CSV record, including the
first record, before decoding anything. It then recognizes a header only if
the first eight redacted fields exactly equal the declared names. A headerless
file is also safe and is parsed positionally after the same truth clearing.

## Frozen public records

One record is one direct annotation. `time` is the released positive finite
per-annotation duration in milliseconds and is divided by 1000 to obtain
seconds, without trimming or winsorization. This unit is fixed before private
opening from the public scale (median 10,525.5 and 95th percentile 59,137.7,
consistent with 10.53 and 59.14 seconds per image); constant rescaling does not
change any route statistic or ranking. `answer` is
the complete set of integer labels selected by the labeler. `options` is the
exact integer-label response space shown for that annotation. For full labels
(`is_candidate=0`), the answer must contain exactly one label. For candidate
labels (`is_candidate=1`), it may contain one or more labels. Every answer must
be a subset of its options, and all labels must lie in `[0,31]`.

The public comparison cell is the exact triple
`(image_id, is_candidate, canonical options set)`. Responses from different
option sets are never compared. Repeated submissions by the same labeler in
the same cell retain the earliest raw row. Image, labeler, assignment, cell,
option, and response identifiers are hashed in derived artifacts.

Public risk is the leave-one-labeler-out fraction of peer complete answers in
the same exact cell that differ from the focal answer. Every retained cell must
have at least two distinct labelers; singleton cells are not silently pooled or
repaired.

## Frozen decision

The unchanged gates are:

- population cost CV at least 0.50;
- minimum opportunity saving at least 40% over total-cost budgets
  `{0.5%,1%,2%,5%,10%,20%}`;
- no undersized exact response-space cell;
- no duplicate labeler remaining within a cell;
- no response-space or record parsing violation among retained records.

Passing freezes `risk_per_second`; otherwise the route is `score_time` and
truth stays closed. A public pass alone does not authorize reading `class`.
Before private opening, the executable runner, singleton truth rule, hashes,
sentinel design, seeds, targets, operating gates, and a synthetic dry run must
all be locked.

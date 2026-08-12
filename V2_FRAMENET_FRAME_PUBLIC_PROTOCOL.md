# FrameNet frame-disambiguation public v2 screen protocol

Date frozen: 2026-08-11. This protocol is outcome-blind. No FrameNet expert
label or row-level aggregate result may be decoded before the public decision
and a separate executable pre-private lock are complete.

## Fixed source

- Zenodo record: `10.5281/zenodo.1472345`;
- repository tag: `v.1.0`;
- repository commit: `67b843c541b76c14f36704acd28f2ec263267a04`;
- license: CC BY-SA 4.0;
- archive: `FrameDisambiguation-v.1.0.zip`;
- archive SHA-256:
  `a46e37a33a043f5061fd461e9d72ae8bd285f7b37b2f98039cb73d47972d12c0`;
- upstream archive MD5: `469e846309e70004ef985444e5a99b02`.

The two raw files are standard MTurk batch-result CSV exports. Repository code
at CrowdTruth-core `v2.0` loads them with `pandas.read_csv` in its default
header mode and maps `WorkerId`, `AcceptTime`, and `SubmitTime`. This evidence
was recorded before any data row was decoded. Only the confirmed header row was
then decoded. Both raw files have the same 708-byte header with SHA-256
`18494f2c66a8913b41e815e7b431dc15be3998fa94ed5847ee7701a8e8c0a67b`.

## Public record definition

One record is one completed MTurk assignment for one `Input.vid` sentence-word
unit. The direct observed response is the complete normalized set in
`Answer.FrameType`. Candidate frames come from `Input.frames`; `none` is an
additional response and must be exclusive. Any response token outside the
declared candidate set is excluded without repair.

The direct cost is positive finite `WorkTimeInSeconds`. `AcceptTime` and
`SubmitTime` are retained only for a public consistency audit and never replace
the released work-time field. Repeated submissions by the same worker for the
same unit are reduced to the earliest submitted assignment before any score is
computed. Worker, unit, assignment, and candidate strings are hashed in derived
artifacts.

Only these raw columns may be decoded:

- `AssignmentId`, `WorkerId`, `HITId`, `AssignmentStatus`;
- `AcceptTime`, `SubmitTime`, `WorkTimeInSeconds`;
- `Input.vid`, `Input.nr_frames`, `Input.frames`;
- `Input.sentence`, `Input.word_phrase`, `Input.beg`, `Input.end`;
- `Answer.FrameType`.

Every other data-row field is cleared at byte level before CSV decoding. The
released raw files do not contain the FrameNet expert label. Output aggregates,
paper example values, and any independently obtained FrameNet 1.7 expert label
are private for this screen and remain unopened.

The frozen independent-truth key is the exact UTF-8 sentence text, exact target
word text, and integral `beg`/`end` pair. `Input.vid` is used to group repeated
worker judgments but is not sufficient by itself for expert matching. Derived
artifacts retain only a SHA-256 digest of the truth key. A unit with multiple
truth-key digests is structurally invalid.

## Frozen public risk and route

For each eligible record, public risk is the leave-one-worker-out fraction of
peer responses in the same `Input.vid` unit whose complete response set differs
from that record. Exact set equality is used; no partial-credit similarity is
allowed.

The fixed public gates are unchanged:

- cost CV at least 0.50;
- minimum opportunity saving at least 40% over
  `{0.5%, 1%, 2%, 5%, 10%, 20%}` total-cost budgets;
- every retained unit has at least two distinct workers;
- no retained unit has conflicting candidate sets.

Passing freezes `risk_per_second`; otherwise the route is `score_time` and no
expert truth may be opened. A public pass alone does not authorize truth
opening. Before that, an independent FrameNet 1.7 source, exact unit alignment,
complete expert-frame coverage inside every candidate set, and a full
executable method lock must all be established without decoding expert labels.

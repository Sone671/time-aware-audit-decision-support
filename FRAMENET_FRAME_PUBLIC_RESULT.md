# FrameNet frame-disambiguation public v2 result

Date: 2026-08-12. Status: **strong public intervention GO; expert truth unopened**.

## Fixed source and structure

The source is Zenodo record `10.5281/zenodo.1472345`, repository tag `v.1.0`
at commit `67b843c541b76c14f36704acd28f2ec263267a04`, licensed CC BY-SA
4.0. The fixed archive SHA-256 is
`a46e37a33a043f5061fd461e9d72ae8bd285f7b37b2f98039cb73d47972d12c0`.

The two raw MTurk files contain 6,480 rows. Five repeated unit-worker
submissions were removed by the frozen earliest-submission rule, leaving 6,475
direct response records over 433 sentence-word units and 51 workers. There are
413 units with 15 workers and 20 with 14 workers. Every unit has one candidate
set and one exact public alignment key.

The direct response is the complete `Answer.FrameType` set. The direct cost is
the released `WorkTimeInSeconds`, without trimming or winsorization. All 6,480
raw target spans exactly satisfy the open-end convention
`Input.sentence[Input.beg:Input.end] == Input.word_phrase`.

## Frozen public decision

- cost CV: `1.5909947941`;
- minimum opportunity saving over `{0.5%,1%,2%,5%,10%,20%}`: `91.632956%`;
- mean opportunity saving: `97.138536%`;
- selected route: `risk_per_second`;
- cost gate, opportunity gate, repeated-worker gate, candidate-space gate,
  and alignment-key gate: all pass.

The six opportunity values range from 99.07% at the 0.5% budget to 91.63% at
the 20% budget. The margin over the frozen 40% gate is therefore 51.63
percentage points at the weakest budget.

## Evidence boundary

Only the 15 whitelisted public MTurk fields were decoded; 35 other data fields
were cleared at byte level first. Neither released aggregate output nor any
FrameNet expert frame value was read. The independently downloaded FrameNet
1.7 archive remains closed. A public pass does not by itself establish safety,
availability, realized efficiency, or an external method GO.

Machine-readable result:
`outputs/framenet_frame_public_screen/public_screen.json`.

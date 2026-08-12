# WhichDog public v2 result

Date: 2026-08-12. Status: **strong public intervention GO; class truth unopened**.

## Fixed structure

The source is Zenodo `10.5281/zenodo.7100698`, licensed CC BY 4.0. The fixed
archive SHA-256 is
`f74dde0f15867c2532ac028a98b0c27c41d18dc6063fc4fb51b397d57cbae150`.
Zenodo documents each of the nine positional fields. The ninth field, `class`,
was cleared at byte level in every row before even the header was decoded.

The release contains 61,227 raw annotations. Seventy-five nonpositive or
invalid public durations were excluded, leaving 61,152 records, 400 images,
1,028 labelers, 1,000 assignments, and 800 exact response-space cells. Full
and candidate tasks contribute 30,591 and 30,561 records. Every exact
`(image, task type, options)` cell is repeated by 45 to 86 distinct labelers;
the median is 80. No cell-labeler duplicate or option mapping violation
remains.

The released time is frozen as milliseconds and divided by 1000. The resulting
median is 10.526 seconds and the mean is 19.792 seconds; no trimming or
winsorization was performed.

## Frozen public decision

- pooled cost CV: `2.7346103742`;
- pooled minimum opportunity saving: `84.175396%`;
- full-task minimum opportunity: `84.357641%`;
- candidate-task minimum opportunity: `85.507473%`;
- pooled, full, and candidate routes: all `risk_per_second`;
- license, cost, opportunity, repeated-cell, and response-space gates: all pass.

The weakest pooled opportunity is still 44.18 percentage points above the
frozen 40% gate. This candidate also resolves the previous alignment problem:
the independent Stanford Dogs class is released positionally for every image
in the same annotation table, while remaining byte-redactable before the
formal lock.

## Evidence boundary

No `class` value was decoded. The result supports only the public premise and
route selection; it is not yet evidence of safety, availability, realized
savings, or an external method GO.

Machine-readable artifact:
`outputs/whichdog_public_screen/public_screen.json`.

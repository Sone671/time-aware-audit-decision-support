# Weather Sentiment formal-candidate invalidation

Date: 2026-08-11 (Asia/Shanghai). Decision:
**invalidated before public screening**.

The University of Southampton record describes a five-column CSV containing
worker ID, task ID, worker label, gold label, and time spent. During a
header-only probe, the downloaded file was found to be headerless only after
its first line had been decoded. That line therefore exposed one gold value
before any public parser, response/cost screen, or executable lock existed.

Under the frozen untouched-truth rule, the dataset is permanently ineligible
for formal v2 confirmation. No additional row may be decoded and no public or
private method metric may be produced from it in this project.

The source file itself is retained with SHA-256
`4e6e0d1753729cf96b81e17c6303fbd4922cd94ec0b7eba0b8c0d6c68035aa0e`
and repository-matching MD5 `87733b3659e031ef3408342148d6e0f6` solely as
an audit artifact. Future headerless candidates must have private column
positions cleared at byte level before the first record is decoded.

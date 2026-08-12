# VU Sound Corpus v2 structural screen

Date: 2026-08-11 (Asia/Shanghai). Decision: **structural NO-GO**.

## Source

- Repository: `https://github.com/CrowdTruth/VU-Sound-Corpus`
- Commit: `f41f96dcc23f662a510a9a53bc792adbf7616a7c`
- Archive SHA-256:
  `b2e04ad4dec48df379c6f01c45f58a3cad48cb19ba37da694abc0180a28fe297`
- License: Apache-2.0.

The 15 raw CrowdFlower CSV files contain 21,330 keyword judgments on 2,133
sound units, initially 10 judgments per sound. There are 63 rows without a
parseable response duration and 21 units with a repeated worker identifier.
The raw positive durations range from 8 to 299 seconds, with median 53 seconds.

## Structural failure

The repository does not contain an independent expert Gold judgment over the
free-keyword response space:

- `author-tags` and the raw CSV `tags` field are Freesound uploader metadata,
  not a withheld expert review of the crowd task;
- `crowd-tags` and `clarity` in `results.xml` are derived from the same crowd
  responses and therefore are not independent truth;
- `true spam` in `workers.csv` is a manual worker-quality label, not a
  per-sound answer in the keyword response space.

Consequently a worker keyword set cannot be compared with a complete,
independent expert keyword set under the frozen exact-response rule. Treating
uploader tags as complete truth, crowd aggregates as Gold, or worker spam as
response correctness would change the estimand and violate the candidate
protocol.

No truth was opened and no public intervention route was selected. The
candidate is not eligible for formal v2 confirmation, although its license and
raw timing structure are otherwise suitable.

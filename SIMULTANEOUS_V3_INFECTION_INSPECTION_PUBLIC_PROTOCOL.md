# Infection Inspection simultaneous-v3 public structure protocol

Date frozen: 2026-08-12 (Asia/Shanghai). Status: **public structure/route
screen only; private truth values unopened; formal use blocked by license
clarification and a complete pre-truth executable lock**.

## Fixed source and current license boundary

- dataset: *Infection Inspection: Classifications and images of
  ciprofloxacin-treated Escherichia coli clinical isolates*;
- Zenodo DOI: `10.5281/zenodo.11656716`;
- Zenodo record license: CC-BY-4.0;
- bundled `Read.me.txt` license statement: `CC BY-NC`, without a version;
- Oxford University Research Archive record license: CC-BY-NC-4.0;
- fixed source archive: `InfectionInspection.zip`, 733,658,476 bytes,
  upstream MD5 `368973a79c5eeba64926fc41d6f33300`;
- public metadata member: `1_Metadata.csv`, ZIP CRC32 `ee6e6963`,
  1,611,919,751 uncompressed bytes and 99,575,788 compressed bytes;
- public Readme documents 1,045,200 classification rows and 49,060 images.

The record-level and source-file statements differ. The archive and any derived
artifact are therefore governed under the more restrictive CC-BY-NC-4.0
interpretation. This permits noncommercial research reuse with attribution; no
claim of CC-BY-only reuse is made.

## Evidence separation

The Readme publicly describes the following outcome fields:

- `MIC` and `treatment_concentration`;
- `expected_response`, derived from their relation;
- `user_call`, correctness of the volunteer response.

Their row values are private for this screen. The reduced `DATA_ANON.csv` is
not used because it has only completion clock time and no genuine elapsed
duration. Image pixels, filenames, strain identifiers, concentration values,
expected responses, and correctness values are also unused.

The large ZIP is accessed only for `1_Metadata.csv`. No PNG member is
downloaded or decoded. A streaming binary CSV redactor must identify columns
from the header and pass only the frozen public fields to UTF-8/JSON decoding.
Values from every other field, particularly any column whose normalized name
contains `mic`, `concentration`, `expected`, `correct`, `call`, `truth`,
`gold`, `strain`, or `image`, must never be decoded or logged.

## Frozen public fields and parser

The only eligible top-level fields are:

- `seq_order` or its unnamed sequential-index equivalent;
- `classification_id`;
- `anon_name`;
- `metadata`;
- `subject_ids`;
- `classification`;
- `classifier`.

The parser aborts if the header does not contain the required identity, task,
response, classifier, and metadata fields described in the bundled Readme. It
may ignore additional fields only through byte replacement before text
decoding.

Only rows with `classifier == Zooniverse` are eligible. A response must
canonicalize exactly to `Sensitive` or `Resistant`. Subject, classification,
and anonymous-user IDs must be nonempty. For repeated submissions by the same
anonymous user to the same subject, retain the earliest `seq_order` and exclude
later duplicates.

`metadata` is parsed as JSON only after isolation. It must contain standard
Zooniverse timestamps `started_at` and `finished_at`. Cost is the positive
finite UTC difference `finished_at - started_at` in seconds. No clipping,
winsorization, upper cap, replacement, or worker-specific correction is
allowed. Missing, unparseable, nonpositive, or reversed durations are excluded
with aggregate counts. The screen aborts rather than substituting
`created_at`, `time_stamp`, median duration, or image-level averages.

If the actual metadata uses different elapsed-time keys, the candidate is a
public structural NO-GO. No parser repair is allowed after any outcome field is
opened.

## Frozen public risk and route

One retained volunteer classification is one audit unit. The comparison cell
is exact `subject_ids`. Every eligible cell must have at least two distinct
anonymous users. Public risk is leave-one-user-out exact binary disagreement:

`1 - (same-response count - 1) / (valid cell size - 1)`.

The score-time order is decreasing public risk, then frozen `seq_order`. The
risk-per-second order uses the existing rank-priority-per-second rule and the
same final tie-break. Opportunity is measured at total-time fractions
`{0.5%, 1%, 2%, 5%, 10%, 20%}`.

The unchanged router selects `risk_per_second` only when:

1. raw eligible cost CV is at least 0.50;
2. minimum risk-equivalent time saving across all six positive budgets is at
   least 40%;
3. every retained subject has at least two distinct users;
4. no unresolved duplicate or response vocabulary error remains.

Otherwise the route freezes to `score_time`. Regardless of route, this screen
does not authorize decoding physical truth.

## Requirements before any truth access

A public pass must be followed by all of the following before any MIC,
treatment-concentration, expected-response, or user-call value is decoded:

1. retain the CC-BY-NC-4.0 source interpretation and required attribution;
2. freeze exact source/member hashes and binary-redaction tests;
3. freeze the private truth parser and prove complete one-to-one subject
   alignment;
4. freeze targets from public score feasibility only;
5. freeze 750 sentinels, 100 repetitions, base seed `20260820`, methods
   `score_time` and `risk_per_second`, budgets
   `{0,0.5%,1%,2%,5%,10%,20%}`, `beta=0.05`, and
   `alpha_cert=0.05/7`;
6. freeze the existing operating gates, including mean excess time at most
   five percentage points.

If any alignment or licensing condition fails after the lock, the dataset is
structurally invalidated; no truth-dependent repair or alternative truth rule
is permitted.

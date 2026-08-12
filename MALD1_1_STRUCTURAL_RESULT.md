# MALD 1.1 v2 structural screen

Date: 2026-08-11 (Asia/Shanghai). Decision: **structural NO-GO**.

## Source

- Repository record: University of Alberta Scholaris item `185f7ef1-79f8-4802-882b-699eb008b609`
- DOI: `10.7939/r3-kh0r-r116`
- Rights URI: `http://creativecommons.org/licenses/by-nc/4.0/`
- The data are trial-level and the item file contains an independent-looking
  lexical-status field `IsWord`.

## Failure before public response screening

The fixed text-file headers were read only up to their first newline:

- `MALD1_1_ResponseData.txt`: `Experiment, Release, Subject, Trial, List,
  WordRunLength, ExperimentRunID, Item, RT, ACC, Session`;
- `MALD1_1_ItemData.txt`: includes `Item` and `IsWord`.

The released response table contains reaction time and accuracy but no direct
human response (`RESP`/key choice). `ACC` is already correctness relative to
the lexical-status truth, so reconstructing a response from `ACC` and `IsWord`
would leak the reference label into the public risk score. The same issue is
visible in the combined `AllData` header.

Therefore MALD 1.1 fails the frozen requirement for an observed human response
that can be used without opening truth. No data rows were decoded, no public
routing metric was calculated, and no truth value was opened.

# Infection Inspection public-screen pre-truth correction

Date: 2026-08-12. Status: **truth unopened; correction limited to protocol/code
consistency**.

The first public runner produced
`outputs/infection_inspection_public_screen/public_screen.json` with SHA-256
`1e5e6ae116a92364666bfb519b69dd6f4d182eaac704420611adf4024d87757d`.
It correctly excluded the 418 singleton-subject records from the risk/cost
population and calculated public geometry on the remaining 841,126 records,
but its `all_cells_repeated_gate` tested the unfiltered 50,115-subject source
instead of the frozen eligible population. It therefore labeled a route that
was already calculated on the eligible population as public NO-GO.

The frozen protocol states that a cell with fewer than two independent users
is **ineligible**. The correction is consequently fixed as:

1. exclude every singleton subject before score, cost, route, target planning,
   and formal population construction;
2. require every subject in the resulting eligible population to have at least
   two distinct users;
3. retain every other public quantity and threshold unchanged.

No MIC, treatment-concentration, expected-response, user-call, image, strain,
or other outcome value has been decoded. No target, sentinel, seed, or formal
method episode existed at the time of this correction. The original JSON is
retained rather than overwritten.

The source license is treated as CC-BY-NC-4.0: the Oxford University Research
Archive record explicitly states that license, consistent with the bundled
Readme's `CC BY-NC` statement. The broader Zenodo record-level CC-BY-4.0 label
is not used to relax source-file restrictions.

# Simultaneous-v3 fresh-dataset search: round 3

Date: 2026-08-12. Final outcome: **fresh confirmation dataset found after the
initial behavioral candidates failed**.

| Candidate | License | Trial response and true time | Independent repeated unit | Independent exact truth | Decision |
|---|---:|---:|---:|---:|---|
| Grasshopper visual detection, Zenodo `4956261` | CC0 | Yes | Some repeated conditions | No separable truth; target/answer coordinates and correctness share the response table | Reject |
| Adaptive visual search, Zenodo `5055078` | CC-BY-4.0 | No; participant-by-period means/counts only | Aggregate only | Not applicable | Reject |
| Confidence in incomplete visual search, Zenodo `17350966` | CC-BY-4.0 | Response yes, RT absent | Participant trials | Target presence shares table | Reject |
| Risky-prospect decisions, Zenodo `3962378` | CC0 | Yes | Repeated prospect classes | No objective same-response Gold; expected value is not a legitimate human-choice truth | Reject |
| Human-vs-AI text judgments, Zenodo `19056843` | CC-BY-4.0 | 206 participants × 30 judgments; no per-item time | Yes | Authorship is objective | Reject for missing cost |
| AI-or-NOT eye tracking, Zenodo `17867585` | CC-BY-4.0 | Sample timestamps but no human authenticity response | Repeated image viewing | Image source map exists | Reject: gaze is not an audit decision |
| Semantic category decisions, Zenodo `11162605` | CC-BY-4.0 | `Resp` and `RT` documented | Exact word pairs randomized; ordinal is not a repeated task | `Cat1/Cat2` directly determine `Same` | Reject before row-value inspection |
| Adaptation to number, Zenodo `15615038` | CC-BY-4.0 | 11,470 trial responses and raw RT | 30 participants, repeated stimulus conditions | Physical relation available | Strong design lead, but fresh status invalidated |
| Infection Inspection, Zenodo `11656716` | CC-BY-NC-4.0 source interpretation | 1,045,199 Zooniverse rows with started/finished timestamps | 841,126 eligible decisions; 49,697 repeated subjects | Separate expected-response column, opened only after complete lock | Fresh simultaneous-v3 GO |

## Number-Adaptation structural probe

The source has 30 MATLAB tables with a stable six-column schema. A closed
export probe observed 11,470 rows, 1,206 equality trials, 10,264 retained
non-equality trials, and 85 condition keys. It therefore has substantially
better scale than the earlier behavioral candidates.

However, the exploratory exporter read `reference_n`, `test_n`, and
`adapter_n` before a complete public-only lock. The reference/test relation
directly determines the physical correct response. The candidate is therefore
permanently excluded from a *fresh* v3 claim in this research chain. No route
screen and no simultaneous episode was run. See
`NUMBER_ADAPTATION_CONFIRMATION_INVALIDATION.md`.

## Final implication for the paper

The earlier statement that no fresh simultaneous-v3 confirmation exists is no
longer correct. Infection Inspection completed a full pre-truth public screen,
method lock, exact truth alignment, and 600 formal episodes. The selected route
passes every frozen gate with a 48.32% primary paired reduction. WhichDog,
SATBench and Dopanim retain their corrected/post-unlock status; the new result
does not retroactively change those evidence tiers.

The evidence package should now use:

1. WhichDog and SATBench as explicitly post-unlock/corrected validation;
2. Dopanim as corrected transfer validation only;
3. Crowd4SDG, FrameNet, and the other screened candidates as data-governance
   and exact-alignment failure cases;
4. the Number-Adaptation result only as a design lesson illustrating why
   outcome-blind public task IDs must be supplied by the dataset depositor.
5. Infection Inspection as the sole fresh simultaneous-v3 confirmation, with
   browser-session cost limitations and 95th/99th percentile post-unlock
   sensitivity disclosed.

The search succeeded precisely through the higher-value route anticipated in
the initial report: a Zooniverse export with opaque subject ID, volunteer
response, true session duration, and separable physical truth.

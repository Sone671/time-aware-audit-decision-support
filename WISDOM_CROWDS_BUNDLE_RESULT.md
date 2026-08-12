# Wisdom-of-Crowds independent image-bundle validation

Date: 2026-08-12 (Asia/Shanghai). Decision: **independent score-time branch
validation passed; no RPS efficiency claim**.

## Frozen design and action

The Figshare behavioral MAT file was screened with a dedicated MATLAB-v5 binary
projector. During the public phase it decoded only the documented response
rating (column 3) and reaction time (column 7); target truth (column 5),
correctness (column 6), and all other payloads were byte-skipped. Synthetic
tests verified that sentinel values in skipped columns never entered the
projected output.

One natural-scene target-detection image is one bundle action. One truth opening
resolves all 17 participant decisions. The finite population contains 800
bundles. Public priority is peer disagreement of the binary decisions, and the
frozen bundle decision is strict majority. Recorded bundle workload is median
participant RT and is explicitly a historical proxy, not expert adjudication
time.

The five-fold cross-fitted cost model and complete formal design were locked
before truth decoding. Predicted-cost CV was 0.2405 and minimum six-budget
opportunity was 6.4048%, so the frozen router selected `score_time`.

## Post-lock result

The explicit no-unlock invocation was rejected. After one-use unlock, all 17
copies of the binary truth agreed on all 800 trials. Majority loss was 131/800
(16.375%). Across 100 sentinel repetitions and three targets:

- score-time issue-free safety: 100%;
- score-time availability: 66.67%;
- unsafe-issued rate: 0%;
- mean excess time budget: 3.195 percentage points;
- mean union workload: 22.477% of median-RT proxy workload;
- all four frozen operating gates passed.

Forced RPS also passed the safety-side operating gates, but over 200 common-safe
target--draw cells its mean paired workload reduction was -0.7382%. It therefore
failed the 25% efficiency gate and confirms the public decision to retain
score-time.

## Evidence boundary

This is a genuinely independent pre-truth validation of the bundle action,
truth-isolation guard, router's score-time branch, and simultaneous certificate.
It is not a prospective time-saving experiment: the source records behavioral
reaction time, not a newly recruited expert's bundle opening, adjudication, and
completion timestamps. The result should strengthen external validation while
leaving the live prospective experiment as an open requirement.

Source: Saha Roy, Mazumder, and Das, Figshare DOI
`10.6084/m9.figshare.13276778.v1`, CC BY 4.0.

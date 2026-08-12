# Frozen public protocol: Wisdom-of-Crowds perceptual image bundles

Date frozen: 2026-08-12 (Asia/Shanghai).  Status at freeze: article text,
Figshare metadata and file list, README, official MATLAB analysis scripts,
MAT-file header, top-level variable directory, and compression tag have been
inspected.  No element of the `resp` variable has been loaded or decoded.

## Source and evidence tier

- study: Saha Roy, Mazumder, and Das, *Wisdom of crowds benefits perceptual
  decision making across difficulty levels*;
- Figshare DOI: `10.6084/m9.figshare.13276778.v1`;
- license: CC BY 4.0;
- behavioral file: `allsubject_behav_sorted_context.mat`, 346,322 bytes;
- upstream MD5: `6e4406cf79d956dca7b9d002add32090`;
- SHA-256:
  `7709d1fd08c34a3c870768854e4fe0993512d611f026500d2504f5d39d61cfcb`.

This is a candidate independent historical bundle validation, not a live
prospective expert-timing trial.  The source paper documents 17 retained human
participants and 800 target-detection tasks, with trial-level confidence
ratings and reaction times in seconds.

## MAT-v5 truth isolation

The behavioral file is a MATLAB-v5 file with one compressed `resp` cell array.
Calling `scipy.io.loadmat`, MATLAB `load`, or any whole-variable decoder is
forbidden during the public phase.  A dedicated binary projector may zlib-
decompress the container and parse only MAT data-element tags, array flags,
dimensions, names, and cell boundaries.  Container metadata shows that each of
the 17 participant cells has shape 800-by-10, consistent across participants.
Within each cell the projector may decode only:

- column 3: ten-point observed confidence/decision rating;
- column 7: positive finite reaction time in seconds.

The projector must byte-skip the numeric payloads of column 5 (target-present
truth), column 6 (correctness), and every other column.  Public output contains
only participant index, stable trial row index, rating, and RT.  A synthetic
guard test must place sentinel values in skipped columns and prove they do not
enter the projected output.

## Action, public score, cost prediction, and route

One natural-scene target-detection task (stable row index 0--799) is one image
bundle action.  Opening its target-present/absent truth once resolves all 17
linked participant decisions.  Ratings 1--5 map to target-present and 6--10 to
target-absent, following the official majority-rule code.  Image priority is
the mean leave-one-participant-out disagreement of these binary decisions.
The frozen crowd decision is strict majority, with an error if tied.

Recorded bundle workload is median trial RT across the 17 participants.  It is
a historical response-time proxy, not expert audit time.  Fold assignment is
stable trial index modulo 5.  For each held-out fold, ordinary least squares on
the other folds fits

`log(median RT) = a + b1*priority + b2*mean absolute rating distance from 5.5`.

Exponentiated held-out predictions form the pre-truth cost vector.  The
score-time order is decreasing priority then trial index.  The RPS order uses
rank-normalized priority divided by predicted cost.  RPS is selected only when
predicted-cost CV is at least 0.50 and minimum score-mass-equivalent opportunity
over `{0.5%,1%,2%,5%,10%,20%}` is at least 40%; otherwise score-time is frozen.

## Formal design fixed before truth decode

- binary bundle loss: frozen strict-majority decision differs from column-5
  truth; a majority tie is an error;
- targets: `{0.10,0.20,0.30}`;
- time grid: `{0,0.5%,1%,2%,5%,10%,20%}`;
- familywise beta: `0.05`, with `0.05/7` per fixed prefix;
- uniform sentinel: unchanged public planner at target 0.10;
- 100 repetitions; base seed `20260829`;
- operating gates: issue-free draw families at least 90%, availability at
  least 30%, unsafe-issued rate at most 10%, mean excess at most 5 percentage
  points;
- efficiency diagnostic: at least one common-safe pair and mean paired
  realized-proxy reduction at least 25% versus score-time.

The formal decoder must require one binary truth per trial, identical across
all 17 participant cells.  Any inconsistent/missing truth, unexpected shape,
nonpositive RT, rating outside 1--10, or lock/hash change structurally
invalidates the candidate before method episodes.

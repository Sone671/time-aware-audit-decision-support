# FrameNet frame-disambiguation v2 formal confirmation protocol

Lock date: 2026-08-12 (Asia/Shanghai). Status before lock generation:
**expert truth unopened**.

## Confirmatory population and sources

The public population is frozen to 6,475 valid MTurk assignments over 433
sentence-word units from Zenodo `10.5281/zenodo.1472345`, CC BY-SA 4.0,
archive SHA-256
`a46e37a33a043f5061fd461e9d72ae8bd285f7b37b2f98039cb73d47972d12c0`.
The record-sequence SHA-256 is
`12c550509748b5e323764009db9863d66e4ff0ddd661d97b8c0a2fb941150ec7`.

Independent expert truth is frozen to the NLTK FrameNet 1.7 package, listed by
the NLTK data index as Creative Commons Attribution 3.0 Unported. The closed
archive is 99,207,152 bytes, MD5 `aaef1cfdcf37000cf2a5c562407fbddb`,
and SHA-256
`22f6aad6fb799ba4dbed0440714e1118442ad7d7345351de37428581284f471c`.
The archive may not be listed, extracted, or parsed before the executable lock
and its synthetic dry run are complete.

## Frozen public construction

- record: one worker's complete frame-selection set for one sentence-word unit;
- cost: positive finite raw `WorkTimeInSeconds`, untrimmed;
- risk: leave-one-worker-out exact complete-set disagreement;
- score-time ranking: descending risk, then frozen record order;
- risk-per-second ranking: descending risk/cost, then descending risk, then
  frozen record order;
- route: `risk_per_second`, frozen from cost CV `1.5909947941` and minimum
  public opportunity `0.9163295600`.

## Frozen expert alignment and error

The exact key is SHA-256 over the UTF-8 sequence
`sentence`, unit-separator, `word_phrase`, unit-separator, decimal start,
unit-separator, decimal end-exclusive. The crowd key uses `Input.sentence`,
`Input.word_phrase`, `Input.beg`, and `Input.end`. For FrameNet XML, the target
layer's inclusive `start/end` is converted to `start/end+1`, and the target word
is the exact Python slice of the XML sentence. No case folding, whitespace
normalization, fuzzy matching, token repair, or candidate repair is allowed for
the key.

Lexicographic XML uses the root `lexUnit` frame; full-text XML uses the target
annotation set's `frameName`. Frame names are normalized exactly as in the
public task: trim, replace spaces by underscores, lower-case. Every public key
must map to exactly one expert frame and that frame must occur in the frozen
public candidate set. Missing, ambiguous, or out-of-candidate mappings cause a
structural invalidation before any method episode.

A worker judgment is erroneous exactly when its complete selected frame set is
not the singleton set containing the aligned expert frame. Selecting the expert
frame plus extra frames is therefore an error. `none` is never silently mapped
to an expert frame.

## Frozen confirmation design

- time grid: `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}`;
- quality targets: `{35%, 45%, 55%}` residual error per full population;
- familywise alpha: `0.05`, allocated as `0.05/3` per target;
- uniform sentinel: 750 records, selected by the unchanged public planner;
- sentinel repetitions: 100, base seed `20260814`;
- methods: `score_time` and `risk_per_second`;
- certificate: unchanged exact one-sided hypergeometric upper bound;
- union cost: planned-review time plus nonoverlapping sentinel time.

The selected route must have episode safety at least 90%, availability at least
30%, unsafe-issued rate at most 10%, and mean excess time at most 5 percentage
points. Efficiency additionally requires at least one common-safe pair and mean
paired union-time reduction of at least 25% versus score-time. Passing every
condition is `v2 external efficiency GO`; any operational or efficiency miss is
`v2 external efficiency NO-GO`. Structural failure is reported separately and
is not a method NO-GO.

No source, key, normalization, target, sentinel count, alpha, time grid, cost,
score, exclusion, seed, method, or decision threshold may change after the
pre-private lock.

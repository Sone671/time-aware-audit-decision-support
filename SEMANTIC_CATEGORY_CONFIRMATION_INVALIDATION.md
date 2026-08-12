# Semantic-category behavior fresh-confirmation invalidation

Date: 2026-08-12. Status: **metadata-level structural rejection; no trial
values opened and no method episodes run**.

## Candidate

Zenodo `10.5281/zenodo.11162605`, CC-BY-4.0, accompanying Do, James and Kim
(2024), *Choice-dependent delta-band neural trajectory during semantic category
decision making in the human brain* (DOI `10.1016/j.isci.2024.110173`). The
deposit includes a small `behavior.zip` with 19 participants and run-level
behavior files. The public description documents `Resp`, `RT`, `Same`, and
`Corr` for 200-trial blocks.

## Structural failure before download/value inspection

The paper's public methods state that each participant saw 800 trials, with two
Korean words randomly selected from 150 animate and 150 inanimate words. The
four category combinations were randomly ordered within blocks; exact word
identities were not repeated task keys. `Same` is the match/non-match answer
derived from the two category labels, and `Corr` is the resulting correctness.

Thus a valid disagreement cell would require grouping trials by the category
combination. The only released fields that identify that combination are
`Cat1`/`Cat2`, which simultaneously determine the private correct direction
(`Same`). Using them during a public route screen would expose the truth
function before the complete lock. Grouping by run/trial ordinal would not
produce repeated independent responses to the same task, because word pairs
were independently randomized.

The candidate is therefore rejected without downloading or decoding any
behavior row. Its public metadata remains a lead for a future depositor-supplied
opaque condition key, not evidence for simultaneous-v3 confirmation.

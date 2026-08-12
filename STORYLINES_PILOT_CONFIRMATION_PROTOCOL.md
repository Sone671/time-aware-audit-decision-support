# Frozen confirmation protocol: StoryLines pilot experiment

Frozen on 2026-08-11 before reading `Experts_Pair` from
`pilot_results_only_pairs.csv`.

The pilot experiment is disjoint from the previously inspected StoryLines main
experiment.  It uses the already frozen method without adjustment:

- deployed crowd label: final pair score >= 0.50;
- public risk: `1 - abs(2p - 1)`;
- genuine cost: unit duration divided by candidate-pair count;
- public route: risk per second iff cost CV >= 0.50, otherwise score-time;
- time budgets: `{0, .5%, 1%, 2%, 5%, 10%, 20%}`;
- sentinel: 500 uniform records;
- targets: `{15%, 20%, 25%}`;
- exact alpha: `0.05/3` with MFSC fixed sequence;
- repetitions: 100.

Confirmation passes when the public-gated route has issued safety >= 90%,
availability >= 30%, unsafe issued rate <= 10%, mean excess time <= 5pp, and,
when risk-per-second is selected, paired union-time reduction >= 25% versus
score-time.  No result may change any method component.

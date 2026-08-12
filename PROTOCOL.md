# Frozen old-seed protocol: Time-Aware Audit Decision Support

Date frozen: 2026-08-11.  The CIFAR-100N old-seed outcomes have been inspected
in earlier count-based work, so this is a development screen rather than a
prospective confirmation.  Dopanim is not used for design selection.

## Research question

Can a fixed public noise-risk ordering be converted into a safer and cheaper
review plan when the objective is real annotation time rather than record
count?  The method is a decision-support layer over a frozen score; it makes
no new detector, group, WGA, retraining, or test-utility claim.

## Public cost source

The official CIFAR-100N `side_info_cifar100N.csv` reports Amazon Mechanical
Turk `Work-time-in-seconds` for contiguous five-image batches.  The batch times
are mapped through the official `image_order_c100.npy` permutation and divided
equally over the five images.  This is the declared amortized per-record cost;
the raw batch time and mapping hashes are saved in the output manifest.

## Plans

Two nested plans use the same frozen public NoiseScore:

1. `score_time`: NoiseScore descending, truncated at each cumulative time
   budget;
2. `risk_per_second`: descending NoiseScore divided by amortized seconds,
   truncated at the same time budgets.

The predeclared time budgets are `{0, 0.5%, 1%, 2%, 5%, 10%, 20%}` of total
annotator time.  A 500-record uniform sentinel is drawn independently for each
replicate.  For every plan, the residual suffix is certified with the exact
hypergeometric upper count at `alpha=0.05/3`; the existing target-specific
fixed sequence chooses the smallest safe plan.  Sentinel and planned-review
time are counted once in their union.

Targets `{30%, 35%, 40%}` are evaluated as separate predeclared deployments;
the displayed target grid is not selected after private labels.

## Gates

Each method/dataset must retain the existing safety, availability, unsafe-rate,
and mean excess-budget gates.  Advancement requires at least two datasets to
pass and a mean paired union-time reduction of at least 25% for cost-aware
versus `score_time` on common safe certificates.  Item-count reduction is
secondary and may be negative; real seconds are primary.

Failure closes this cost-ordering variant without tuning score exponents, time
transformations, budget grids, sentinel size, or target thresholds on these
outcomes.  A positive old-seed screen would require a fresh public dataset with
the same time field for confirmation.

## Independent CIFAR-10N screen

CIFAR-10N is the second public dataset for the development screen.  Its
features are cached ImageNet-ResNet-18 representations.  A multiclass
LogisticRegression with `C=1`, `lbfgs`, and an 80/20 split stratified only by
the noisy label trains the public score for each of three fixed seeds.  No
clean label is used by fitting or ranking.  The historical median of the
three worker times in each ten-image batch, divided by ten, is the declared
amortized cost.  This screen uses the same sentinel, budget grid, targets, and
exact certificate as CIFAR-100N.

# WhichDog formal v2 result

Date: 2026-08-12. Status: **v2 external efficiency GO**.

## Locked confirmation

The formal lock used the fixed Zenodo CC BY 4.0 archive
`f74dde0f15867c2532ac028a98b0c27c41d18dc6063fc4fb51b397d57cbae150`, 61,152
public-valid records, 400 images, 800 exact response-space cells, the public
`risk_per_second` route, 750 uniform sentinels, 100 repetitions, targets
35/45/55%, base seed `20260815`, and the unchanged v2 certificate and gates.
The lock and synthetic dry run were verified before opening the positional
`class` field.

## Truth alignment

All 400 public images map to exactly one integral `class` value. No invalid or
ambiguous truth rows occurred, and no record had a class outside its displayed
options. The frozen task-aware loss yielded 23,444 errors out of 61,152
(38.3373%): 13,304/30,591 full-label errors (43.4899%) and 10,140/30,561
candidate-label coverage errors (33.1795%).

## Operating and efficiency results

| Method | Safety | Availability | Unsafe-issued | Mean excess | Mean union time |
|---|---:|---:|---:|---:|---:|
| score-time | 99.00% | 100.00% | 0.333% | 2.550pp | 7.021% |
| risk-per-second | **100.00%** | **100.00%** | **0.000%** | **0.065pp** | **1.465%** |

The selected route passes every operating gate. There are 299 common-safe
paired comparisons, with mean paired union-time reduction **29.6819%** versus
score-time, above the frozen 25% efficiency gate. The formal decision is
therefore `v2 external efficiency GO`.

The public opportunity screen remains outcome-blind: cost CV was 2.7346 and
the six-budget minimum opportunity was 84.1754%. The formal result is the first
new, untouched external efficiency confirmation in this development branch;
FrameNet is retained only as a structural-invalidation diagnostic and must not
be used as a tuning set.

Artifacts:

- `V2_WHICHDOG_PUBLIC_PROTOCOL.md`;
- `WHICHDOG_PUBLIC_RESULT.md`;
- `V2_WHICHDOG_FORMAL_PROTOCOL.md`;
- `outputs/whichdog_public_screen/public_screen.json`;
- `outputs/whichdog_formal_confirmation/design_pre_private.json`;
- `outputs/whichdog_formal_confirmation/method_lock_manifest.json`;
- `outputs/whichdog_formal_confirmation/design.json`;
- `outputs/whichdog_formal_confirmation/summary.json`;
- `outputs/whichdog_formal_confirmation/recommendations.csv`;
- `outputs/whichdog_formal_confirmation/paired_time_comparison.csv`.

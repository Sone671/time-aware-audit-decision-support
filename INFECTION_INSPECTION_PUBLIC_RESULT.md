# Infection Inspection simultaneous-v3 public result

Date: 2026-08-12. Status: **public intervention GO; physical truth unopened**.

After the documented pre-truth singleton correction, the eligible population
contains 841,126 volunteer classifications from 49,697 subjects with at least
two distinct users. The redacted source contains only opaque classification,
user and subject identifiers, binary volunteer response, and elapsed seconds
from Zooniverse `started_at`/`finished_at`. MIC, treatment concentration,
expected response, correctness, strain and image fields remain unopened.

The public router selects `risk_per_second`:

- raw elapsed-time CV: 70.3365;
- median / mean elapsed time: 2.729 / 47.344 s;
- minimum risk-equivalent saving over the six positive budgets: 92.4178%;
- mean saving: 95.1432%.

The route is robust to a public-only diagnostic cap that is not used in the
formal analysis:

| Public cost diagnostic | CV | Minimum saving | Route |
|---|---:|---:|---|
| raw elapsed time | 70.3365 | 92.42% | risk-per-second |
| capped at public 99th percentile (138.919 s) | 2.5657 | 70.25% | risk-per-second |
| capped at public 95th percentile (19.523 s) | 1.0174 | 53.22% | risk-per-second |

Formal confirmation is not yet authorized by this result alone. A complete
executable pre-truth design must first freeze the outcome parser, exact subject
alignment, targets, sentinels, seed, methods, simultaneous alpha, and operating
gates. The source is treated under CC-BY-NC-4.0 with attribution.

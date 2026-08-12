# Frozen prospective bundle-audit protocol

This protocol defines the experiment still required for a genuine prospective
efficiency claim. Historical response-time replay is not sufficient.

## Action and population

- Infection Inspection action: one subject bundle. Opening the subject reveals
  one expected response and resolves every linked classification.
- WhichDog action: one image bundle. Opening the image reveals one class and
  resolves every linked full-label and candidate-set response.
- Bundle loss is frozen before collection. Infection Inspection uses majority
  binary-response error with ties counted as errors. WhichDog uses majority
  full-label error and reports candidate-set coverage separately.
- The correction-aware record-burden endpoint is distinct from bundle loss.
  Freeze the record population, the subject/image partition, the record-to-bundle
  mapping, and each record loss. WhichDog full-label and candidate-coverage
  records remain separate endpoints.
- Freeze whether opening one bundle authorizes correction of every linked
  record. The interface must apply and log those corrections; unimplemented or
  ambiguous linked corrections cannot be subtracted from the certificate.

## Public cost model

Fit the cost model only on completed pilot bundles. Allowed predictors are
available before truth opening: response count, response-disagreement summary,
task type/options count, and interface metadata. No realized audit duration,
truth, correctness, or post-action field may be used.

Before the evaluation begins, archive and hash:

1. the eligible population and bundle identifiers;
2. feature construction and fitted cost-model coefficients;
3. predicted costs, public priorities, score-time and RPS orders;
4. CV/opportunity gates and selected route;
5. budget grid, targets, sentinel size, sentinel IDs, random seeds, and loss;
6. for bundle closure, record-reference IDs, record-to-bundle mapping, unique
   bundle-opening rule, and linked-correction log schema;
7. analysis code, environment lock, exclusion rules, and inactivity rule.

## Time collection

The audit interface must emit immutable UTC events for `bundle_open`,
`truth_submit`, and `bundle_complete`. Primary realized cost is
`bundle_complete - bundle_open`. A pause is flagged when the interval between
foreground events exceeds the frozen inactivity threshold; raw and pause-adjusted
costs are both retained, with the raw endpoint primary unless the protocol is
amended before collection. Reopening a bundle is logged and charged according
to the frozen retry rule.

## Evaluation

The selected route is evaluated on realized bundle time only after collection.
The same uniform-sentinel finite-population certificate and seven-prefix
Bonferroni curve are used. Report issue-free draw families, availability,
unsafe-issued rate, excess realized time, union time, and paired realized-time
reduction relative to score-time. Any post-freeze model or action change creates
a new exploratory analysis and cannot replace the frozen result.

For the record-burden endpoint, draw the reference sample uniformly without
replacement from the frozen records and map sampled records to unique bundle
openings. Compute the pre-opening hypergeometric bound on suffix record errors,
then subtract only linked errors documented as corrected by those openings.
Charge every unique planned or reference-triggered bundle once in union time.

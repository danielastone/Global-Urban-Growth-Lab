# Headline persistence coverage gate

## Problem

A forecast can be point-in-time correct and still report performance on a future-selected subset. The lower-level persistence evaluators score rows with observed outcomes; by construction they cannot score a city whose future outcome is missing. That scoring requirement must not be allowed to redefine the origin cohort or hide future attrition.

## Locked rule

Any persistence result promoted beyond retrospective or intermediate point-in-time analysis must carry an origin-defined outcome-coverage denominator.

The denominator must come from `origin_risk_set_outcome_coverage` or an equivalent table satisfying the same contract:

- one row per forecast origin;
- `origin_risk_set_rows` defined from lag and origin predictor availability only;
- `observed_outcome_rows` plus `missing_outcome_rows` exactly equals the origin risk set;
- `observed_outcome_share` agrees with those counts;
- `coverage_denominator_rule = lag_and_origin_predictors_only`;
- `future_outcome_used_for_membership = false`.

The headline-qualified functions are:

- `evaluate_headline_point_in_time_persistence` for aggregate metrics;
- `headline_point_in_time_persistence_errors` for row-level errors.

They call the existing point-in-time timing and provenance gates, then merge validated origin-risk-set coverage onto every result. They also verify that the number of scored rows cannot exceed the number of observed outcomes recorded for that origin.

## Classification

`evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` remain valid lower-level point-in-time building blocks. Their `benchmark_stage = point_in_time_persistence_only` does **not** establish that future-outcome attrition was audited.

Only results with both:

- `origin_risk_set_coverage_enforced = true`, and
- `headline_coverage_contract_enforced = true`

may be described as having passed the origin-cohort coverage gate.

Passing this gate does not mean outcome coverage is high. The actual `observed_outcome_share` must still be reported and interpreted. A low share is evidence of attrition risk, not something this gate repairs.

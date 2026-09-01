# Headline persistence coverage gate

## Problem

A forecast can be point-in-time correct and still report performance on a future-selected subset. The lower-level persistence evaluators score rows with observed outcomes; by construction they cannot score a city whose future outcome is missing. That scoring requirement must not be allowed to redefine the origin cohort or hide future attrition.

A second distinction is also required: **coverage audited** is not the same as **coverage adequate for headline use**. Reporting a 40% observed-outcome share does not by itself justify promoting the resulting forecast score as a headline result.

## Locked rule

Any persistence result promoted beyond retrospective or intermediate point-in-time analysis must carry an origin-defined outcome-coverage denominator **and must pass a registered minimum observed-outcome share for every declared forecast origin**.

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

## Registered minimum coverage policy

The repository does **not** define a universal acceptable coverage percentage. The appropriate minimum may depend on source design, geography, cohort, and the planned claim. Hard-coding an unsupported default would replace one hidden assumption with another.

Instead, every headline call must explicitly provide:

- `minimum_observed_outcome_share`: a numeric threshold in `(0, 1]`;
- `coverage_policy_reference`: a nonblank reference identifying the locked analysis rule, specification, or source-specific policy that set the threshold.

Every declared origin must meet or exceed the registered minimum. If any origin falls below it, the headline-qualified evaluator fails closed. Lower-level point-in-time results can still be produced and reported as diagnostics, together with the adverse coverage evidence.

Headline outputs record:

- `minimum_observed_outcome_share`;
- `coverage_policy_reference`;
- `coverage_policy_passed = true`;
- `headline_coverage_minimum_enforced = true`.

Changing the minimum after examining forecast performance is a specification change and must not be presented as if it were the original headline rule.

## Classification

`evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` remain valid lower-level point-in-time building blocks. Their `benchmark_stage = point_in_time_persistence_only` does **not** establish that future-outcome attrition was audited or adequate.

Only results with all of the following may be described as having passed the headline origin-cohort coverage gate:

- `origin_risk_set_coverage_enforced = true`;
- `headline_coverage_contract_enforced = true`;
- `headline_coverage_minimum_enforced = true`;
- `coverage_policy_passed = true`.

The actual `observed_outcome_share` must still be reported. Passing the registered minimum does not make missing outcomes irrelevant; it only establishes that the result met the prespecified minimum evidence standard for headline use.

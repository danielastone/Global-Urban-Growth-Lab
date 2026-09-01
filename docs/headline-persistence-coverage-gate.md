# Headline persistence coverage gate

## Problem

A forecast can be point-in-time correct and still report performance on a future-selected subset. The lower-level persistence evaluators score rows with observed outcomes; by construction they cannot score a city whose future outcome is missing. That scoring requirement must not be allowed to redefine the origin cohort or hide future attrition.

A second distinction is also required: **coverage audited** is not the same as **coverage adequate for headline use**. Reporting a low observed-outcome share does not by itself justify promoting the resulting forecast score as a headline result.

A third constraint is necessary: the minimum itself cannot be a runtime tuning parameter. If an analyst can lower the cutoff after inspecting results, a nominally "registered" threshold does not prevent specification search.

## Locked rule

Any persistence result promoted beyond retrospective or intermediate point-in-time analysis must carry an origin-defined outcome-coverage denominator and must pass a **repository-registered minimum observed-outcome share** for every declared forecast origin.

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

They call the existing point-in-time timing and provenance gates, merge validated origin-risk-set coverage onto every result, and verify that the number of scored rows cannot exceed the number of observed outcomes recorded for that origin.

## Versioned coverage policy registry

Headline callers provide only `coverage_policy_id`. They do **not** supply the numerical threshold or free-text reference at runtime.

`src/urban_growth/coverage_policy.py` is the repository-controlled policy registry. Each entry contains:

- a stable `policy_id`;
- `minimum_observed_outcome_share` in `(0, 1]`;
- a nonblank policy reference.

Changing a threshold therefore requires a versioned repository change and review rather than a function-call adjustment. Outputs retain the policy ID, minimum, reference, and `coverage_policy_registry_enforced = true` so a result can be traced back to the exact policy in Git history.

The production registry is deliberately empty until the project adopts a substantively justified threshold. This is fail-closed: no headline-qualified persistence result can be produced merely by inventing a cutoff during analysis. Synthetic unit tests inject test-only entries and do not establish a substantive project policy.

When a real policy is adopted, it should be added through a reviewed PR with its rationale, intended source/cohort scope, and relationship to the claim being qualified.

Every declared origin must meet or exceed the registered minimum. If any origin falls below it, the headline-qualified evaluator fails closed. Lower-level point-in-time results can still be produced and reported as diagnostics together with the adverse coverage evidence.

## Classification

`evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` remain valid lower-level point-in-time building blocks. Their `benchmark_stage = point_in_time_persistence_only` does **not** establish that future-outcome attrition was audited or adequate.

Only results with all of the following may be described as having passed the headline origin-cohort coverage gate:

- `origin_risk_set_coverage_enforced = true`;
- `headline_coverage_contract_enforced = true`;
- `headline_coverage_minimum_enforced = true`;
- `coverage_policy_registry_enforced = true`;
- `coverage_policy_passed = true`.

The actual `observed_outcome_share` must still be reported. Passing the registered minimum does not make missing outcomes irrelevant; it only establishes that the result met the versioned minimum evidence standard for headline use.

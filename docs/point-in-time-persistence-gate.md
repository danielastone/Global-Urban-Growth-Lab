# Point-in-time persistence evaluation gate

A persistence benchmark can be out-of-sample in reference-year terms while still using evidence that was not actually available at the forecast origin. Point-in-time evaluation therefore distinguishes test-row deployability at its own origin from training-row availability at the current evaluation origin.

Deployable persistence evaluation requires all of the following:

- the source-specific City Data Fitness eligibility flag (normally `growth_eligible`);
- raw `forecast_origin_date`, predictor availability, concordance availability, and supporting source references;
- the raw registered forecast-origin rule in `forecast_origin_registration`;
- `point_in_time_available = true` for test rows at the origin being scored;
- verified predictor and concordance availability provenance;
- `forecast_origin_registration_verified = true` for every row entering the point-in-time persistence path;
- explicit predictor, concordance, and outcome availability dates for candidate training rows; and
- nonblank provenance supporting those availability dates.

## Recompute derived point-in-time flags before headline use

Derived booleans are not primary evidence. A caller could otherwise copy or manually set `point_in_time_available`, `availability_provenance_verified`, or `forecast_origin_registration_verified` to `true` without having passed the availability constructor that produced them.

`recompute_point_in_time_evidence` therefore reruns `apply_forecast_availability_gate` from the raw dates, source references, and registered origin rule. It then reconciles the recomputed values against all three supplied derived flags. Missing raw evidence, an invalid origin calendar rule, or any disagreement between a supplied flag and the recomputed value fails closed.

Headline persistence uses `evaluate_verified_point_in_time_persistence_baselines` and `verified_point_in_time_persistence_errors`, not the lower-level persistence evaluator directly. Qualified outputs record:

- `point_in_time_evidence_recomputed = true`;
- `derived_point_in_time_flags_reconciled = true`; and
- `headline_point_in_time_integrity_enforced = true`.

The lower-level `evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` remain useful intermediate diagnostics, but their derived booleans are not independently sufficient evidence for a headline deployability claim.

## Test rows versus training rows

The test sample for origin `t` is evaluated exactly as-of its own registered forecast date. A test row whose predictor or concordance was not available at that date cannot be scored at `t`.

Historical training rows use a different rule. They are **not** required to have been deployable at their own earlier forecast origin. For each current evaluation origin, a historical row may enter training if all evidence needed by the persistence benchmark is available by the current origin's as-of date:

- the row's reference interval ended by the current origin;
- `predictor_available_date <= current forecast_origin_date`;
- `concordance_available_date <= current forecast_origin_date`; and
- `outcome_available_date <= current forecast_origin_date`.

This matters because a row can legitimately be unavailable in real time at, for example, its 2000 origin but become fully observable before a 2010 forecast. Permanently excluding it because `point_in_time_available` was false in 2000 would understate the information set available in 2010 and could distort comparisons across models or origins.

The training gate therefore evaluates availability **as of the current origin**, not the historical row's own origin. The implementation reports `training_uses_current_origin_as_of = true`, along with `training_predictor_availability_enforced`, `training_concordance_availability_enforced`, and `training_outcome_availability_enforced`.

Reference years, enumeration dates, endpoint years, current download dates, or analyst-entered assumptions are not sufficient provenance for availability dates. Evidence should point to the relevant statistical release, archived publication, geography release, metadata record, or equivalent source establishing when the information became observable.

The original `evaluate_fitness_gated_persistence_baselines` remains available for retrospective sensitivity analysis and must not by itself be described as real-time or deployable-at-origin performance.

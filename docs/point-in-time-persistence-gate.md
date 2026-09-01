# Point-in-time persistence evaluation gate

A persistence benchmark can be out-of-sample in reference-year terms while still using evidence that was not actually available at the forecast origin. Point-in-time evaluation therefore distinguishes test-row deployability at its own origin from training-row availability at the current evaluation origin.

Deployable persistence evaluation requires all of the following:

- the source-specific City Data Fitness eligibility flag (normally `growth_eligible`);
- `point_in_time_available = true` for test rows at the origin being scored;
- verified predictor and concordance availability provenance;
- `forecast_origin_registration_verified = true` for every row entering the point-in-time persistence path;
- explicit predictor, concordance, and outcome availability dates for candidate training rows; and
- nonblank provenance supporting those availability dates.

## Test rows versus training rows

The test sample for origin `t` is evaluated exactly as-of its own registered forecast date. A test row whose predictor or concordance was not available at that date cannot be scored at `t`.

Historical training rows use a different rule. They are **not** required to have been deployable at their own earlier forecast origin. For each current evaluation origin, a historical row may enter training if all evidence needed by the persistence benchmark is available by the current origin's as-of date:

- the row's reference interval ended by the current origin;
- `predictor_available_date <= current forecast_origin_date`;
- `concordance_available_date <= current forecast_origin_date`; and
- `outcome_available_date <= current forecast_origin_date`.

This matters because a row can legitimately be unavailable in real time at, for example, its 2000 origin but become fully observable before a 2010 forecast. Permanently excluding it because `point_in_time_available` was false in 2000 would understate the information set available in 2010 and could distort comparisons across models or origins.

The training gate therefore evaluates availability **as of the current origin**, not the historical row's own origin. The implementation reports `training_uses_current_origin_as_of = true`, along with `training_predictor_availability_enforced`, `training_concordance_availability_enforced`, and `training_outcome_availability_enforced`.

The downstream evaluator still independently requires verified origin registration and availability provenance; it does not trust a caller-supplied `point_in_time_available` boolean as sufficient evidence.

Reference years, enumeration dates, endpoint years, current download dates, or analyst-entered assumptions are not sufficient provenance for availability dates. Evidence should point to the relevant statistical release, archived publication, geography release, metadata record, or equivalent source establishing when the information became observable.

The original `evaluate_fitness_gated_persistence_baselines` remains available for retrospective sensitivity analysis and must not by itself be described as real-time or deployable-at-origin performance.

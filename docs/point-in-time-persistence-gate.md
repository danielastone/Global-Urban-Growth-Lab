# Point-in-time persistence evaluation gate

A persistence benchmark can be out-of-sample in reference-year terms while still using evidence that was not actually available at the forecast origin. Point-in-time evaluation therefore distinguishes test-row predictor availability, the registered forecast-origin rule, and training-outcome availability.

Deployable persistence evaluation requires all of the following:

- the source-specific City Data Fitness eligibility flag (normally `growth_eligible`);
- `point_in_time_available = true` for eligible forecast rows, produced from explicit predictor and concordance availability dates with verified availability provenance;
- `forecast_origin_registration_verified = true` for every row entering the point-in-time persistence path, establishing that the as-of dates passed the registered rolling-origin calendar rule;
- an explicit `outcome_available_date` for every candidate training row; and
- a nonblank `outcome_available_reference` identifying the evidence supporting that first-availability date.

The downstream persistence evaluator must not trust `point_in_time_available` by itself. That boolean can be copied, reconstructed, or supplied by a caller after the original availability gate. `point_in_time_fitness_gated_forecast_panel` therefore independently requires the origin-registration verification flag as well as the availability-provenance flag. Missing, nonboolean, or false origin-registration verification fails closed. Aggregate and row-level point-in-time outputs record `forecast_origin_registration_gate_enforced = true`.

For each forecast origin, `evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` resolve that origin's explicit `forecast_origin_date` and retain only historical rows whose outcomes were published on or before that date. A training interval whose reference period ended by the origin but whose statistical release occurred later is not valid training evidence for that origin. The same historical interval can become eligible training evidence at a later origin once its release date has passed.

The deployable path reports both `candidate_training_rows` and `available_training_rows`, sets `training_outcome_availability_enforced = true`, `training_outcome_provenance_enforced = true`, and `forecast_origin_registration_gate_enforced = true`. Missing release dates, missing or blank outcome-release provenance, unverified origin registration, ambiguous forecast-origin dates, or fewer than two origins with published training outcomes fail closed.

Reference years, enumeration dates, endpoint years, current download dates, or analyst-entered assumptions are not sufficient provenance for `outcome_available_date`. The reference must point to the release notice, archived publication, metadata record, or equivalent evidence establishing when the outcome became observable.

The original `evaluate_fitness_gated_persistence_baselines` remains available for retrospective sensitivity analysis and must not by itself be described as real-time or deployable-at-origin performance.

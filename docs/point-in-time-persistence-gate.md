# Point-in-time persistence evaluation gate

A persistence benchmark can be out-of-sample in reference-year terms while still using evidence that was not actually available at the forecast origin. Point-in-time evaluation therefore distinguishes test-row predictor availability from training-outcome availability.

Deployable persistence evaluation requires all of the following:

- the source-specific City Data Fitness eligibility flag (normally `growth_eligible`);
- `point_in_time_available = true` for eligible forecast rows, produced from explicit predictor and concordance availability dates with verified availability provenance;
- an explicit `outcome_available_date` for every candidate training row; and
- a nonblank `outcome_available_reference` identifying the evidence supporting that first-availability date.

For each forecast origin, `evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` resolve that origin's explicit `forecast_origin_date` and retain only historical rows whose outcomes were published on or before that date. A training interval whose reference period ended by the origin but whose statistical release occurred later is not valid training evidence for that origin. The same historical interval can become eligible training evidence at a later origin once its release date has passed.

The deployable path reports both `candidate_training_rows` and `available_training_rows`, sets `training_outcome_availability_enforced = true`, and sets `training_outcome_provenance_enforced = true`. Missing release dates, missing or blank outcome-release provenance, ambiguous forecast-origin dates, or fewer than two origins with published training outcomes fail closed.

Reference years, enumeration dates, endpoint years, current download dates, or analyst-entered assumptions are not sufficient provenance for `outcome_available_date`. The reference must point to the release notice, archived publication, metadata record, or equivalent evidence establishing when the outcome became observable.

The original `evaluate_fitness_gated_persistence_baselines` remains available for retrospective sensitivity analysis and must not by itself be described as real-time or deployable-at-origin performance.

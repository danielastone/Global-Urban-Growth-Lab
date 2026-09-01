# Point-in-time persistence evaluation gate

A persistence benchmark can be out-of-sample in reference-year terms while still using evidence that was not actually available at the forecast origin. Point-in-time evaluation therefore distinguishes test-row predictor availability from training-outcome availability.

Deployable persistence evaluation requires all of the following:

- the source-specific City Data Fitness eligibility flag (normally `growth_eligible`);
- `point_in_time_available = true` for eligible forecast rows, produced from explicit predictor and concordance availability dates; and
- an explicit `outcome_available_date` for every candidate training row.

For each forecast origin, `evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` resolve that origin's explicit `forecast_origin_date` and retain only historical rows whose outcomes were published on or before that date. A training interval whose reference period ended by the origin but whose statistical release occurred later is not valid training evidence for that origin. The same historical interval can become eligible training evidence at a later origin once its release date has passed.

The deployable path reports both `candidate_training_rows` and `available_training_rows` and sets `training_outcome_availability_enforced = true`. Missing release dates, ambiguous forecast-origin dates, or fewer than two origins with published training outcomes fail closed.

The original `evaluate_fitness_gated_persistence_baselines` remains available for retrospective sensitivity analysis and must not by itself be described as real-time or deployable-at-origin performance.

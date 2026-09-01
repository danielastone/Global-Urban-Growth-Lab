# Point-in-time persistence evaluation gate

A persistence benchmark can be out-of-sample in reference-year terms while still using predictor or concordance evidence that was not actually available at the forecast origin. The existing fitness-gated persistence evaluator is therefore classified as a retrospective benchmark unless a separate point-in-time availability gate is enforced.

Deployable persistence evaluation requires both:

- the source-specific City Data Fitness eligibility flag (normally `growth_eligible`); and
- `point_in_time_available = true`, produced by the forecast availability gate using an explicit forecast-origin date.

`evaluate_point_in_time_persistence_baselines` and `point_in_time_persistence_errors` enforce both conditions before constructing rolling-origin train/test samples. Missing or non-boolean point-in-time evidence fails closed.

The original `evaluate_fitness_gated_persistence_baselines` remains available for retrospective sensitivity analysis and must not by itself be described as real-time or deployable-at-origin performance.

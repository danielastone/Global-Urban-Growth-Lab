# Forecast data availability and publication-lag rule

## Problem

A reference year is not a data-availability date. A census, population count, geographic concordance, boundary relationship file, or revised historical series may be published after the date it describes. Treating the reference date as if the evidence were already observable creates look-ahead leakage and overstates real-time forecast performance.

This issue is independent of geographic comparability, threshold truncation, survivorship, and model overfitting. A row can pass all of those checks and still be unavailable to an analyst at the claimed forecast origin.

The repository's core rolling-forecast panels use integer years in `period_start` and `period_end`. Those fields are reference-period identifiers, not timestamps. In particular, passing an integer year such as `2000` to generic datetime coercion does not mean January 1, 2000 and must never be used to establish historical availability.

## Locked rule

Any result described as **deployable at origin**, **real-time**, or a point-in-time forecast must record:

- `forecast_origin_date`: the actual as-of date at which the forecast is claimed to have been formed;
- `predictor_available_date`: first date the population/statistical information needed for the predictor was available to the analyst;
- `predictor_availability_source`: auditable source evidence supporting that first-availability date;
- `concordance_available_date`: first date the geography/crosswalk evidence needed to construct the comparable predictor was available;
- `concordance_availability_source`: auditable source evidence supporting that concordance first-availability date.

Both evidence dates must be on or before `forecast_origin_date`. Missing origin or availability dates fail closed. Missing or blank availability-source provenance also fails closed. Reference year, enumeration date, `period_start`, period end, file vintage, current download date, and an unsupported analyst-entered date are not substitutes for first availability.

`src/urban_growth/forecast_availability.py` implements this rule and produces `point_in_time_available`, `availability_provenance_verified`, and explicit exclusion reasons. The default origin field is `forecast_origin_date`; callers may override the column name only when they supply another explicit date field with the same semantics.

A downstream persistence evaluator must not trust a manually supplied `point_in_time_available` flag by itself. The deployable persistence path also requires `availability_provenance_verified = true`, which is produced only after the availability gate validates the required provenance fields.

## Consequences

Retrospective analyses may still use later-released evidence when clearly labeled retrospective. They must not be promoted to deployable-at-origin evidence.

For rolling persistence tests, an outcome observed through an origin year is not automatically training information at that origin. If its required source release occurred after the origin, it cannot enter the real-time training set until a later origin. The deployable persistence evaluator therefore separately requires an explicit `outcome_available_date` for training outcomes.

For Mexico, this means census/count reference dates and locality-equivalence evidence require actual release/availability dates **and source evidence for those dates** before the multiwave panel can be called deployable. The existing year-only `evidence_reference_year <= endpoint_year` concordance check prevents future-reference geography but does not by itself establish point-in-time availability.

For revised international products such as current-vintage WUP, WPP, or retrospective GHSL histories, the same distinction applies: current-vintage historical observations can support retrospective sensitivity analysis without constituting historical real-time information.

## Result classification

- `point_in_time_available = true`: required predictor and concordance evidence existed by the explicit forecast-origin date and the first-availability claims have recorded provenance.
- `point_in_time_available = false`: retrospective-only for that origin.
- unknown evidence availability, missing forecast-origin date, or missing availability provenance: fail closed; do not infer availability from the reference period.

This gate is orthogonal to the City Data Fitness Standard and should be applied in addition to source-specific growth/headline eligibility before a forecast is described as deployable.

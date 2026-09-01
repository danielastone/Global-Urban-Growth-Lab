# Forecast data availability and publication-lag rule

## Problem

A reference year is not a data-availability date. A census, population count, geographic concordance, boundary relationship file, or revised historical series may be published after the date it describes. Treating the reference date as if the evidence were already observable creates look-ahead leakage and overstates real-time forecast performance.

This issue is independent of geographic comparability, threshold truncation, survivorship, and model overfitting. A row can pass all of those checks and still be unavailable to an analyst at the claimed forecast origin.

## Locked rule

Any result described as **deployable at origin**, **real-time**, or a point-in-time forecast must record:

- `predictor_available_date`: first date the population/statistical information needed for the predictor was available to the analyst;
- `concordance_available_date`: first date the geography/crosswalk evidence needed to construct the comparable predictor was available;
- a forecast-origin date precise enough to compare with those availability dates.

Both evidence dates must be on or before the forecast origin. Missing availability dates fail closed. Reference year, enumeration date, period end, file vintage, and current download date are not substitutes for first availability.

`src/urban_growth/forecast_availability.py` implements this rule and produces `point_in_time_available` plus explicit exclusion reasons.

## Consequences

Retrospective analyses may still use later-released evidence when clearly labeled retrospective. They must not be promoted to deployable-at-origin evidence.

For rolling persistence tests, an outcome observed through an origin year is not automatically training information at that origin. If its required source release occurred after the origin, it cannot enter the real-time training set until a later origin.

For Mexico, this means census/count reference dates and locality-equivalence evidence require actual release/availability dates before the multiwave panel can be called deployable. The existing year-only `evidence_reference_year <= endpoint_year` concordance check prevents future-reference geography but does not by itself establish point-in-time availability.

For revised international products such as current-vintage WUP, WPP, or retrospective GHSL histories, the same distinction applies: current-vintage historical observations can support retrospective sensitivity analysis without constituting historical real-time information.

## Result classification

- `point_in_time_available = true`: required predictor and concordance evidence existed by the origin.
- `point_in_time_available = false`: retrospective-only for that origin.
- unknown evidence availability: fail closed; do not infer availability from the reference period.

This gate is orthogonal to the City Data Fitness Standard and should be applied in addition to source-specific growth/headline eligibility before a forecast is described as deployable.
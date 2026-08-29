# Analytical panel contract

## Unit of observation

One stable urban unit over one non-overlapping observation interval. Administrative cities and consistently defined agglomerations must not be pooled without a definition flag and sensitivity analysis.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `city_id` | string | Stable project identifier, never a city name alone |
| `country_code` | string | Stable country identifier for the period |
| `period_start` | integer | First population year |
| `period_end` | integer | Last population year |
| `population_start` | positive number | Population at `period_start` |
| `population_end` | positive number | Population at `period_end` |

## Recommended fields

`city_name`, `urban_definition`, `boundary_version`, `boundary_reference_year`, `boundary_temporally_fixed`, `boundary_history_uses_future_reference`, `cross_stream_reconciled`, `latitude`, `longitude`, `source_id`, `observation_type`, `national_population_growth`, `urban_share_change`, `city_rank_start`, and measurement-quality flags.

## Invariants

- `(city_id, period_start, period_end)` is unique.
- `period_end > period_start`.
- Start and end populations are positive.
- Predictors are timestamped and available by the forecast origin.
- Boundary changes, interpolations, and modeled observations are explicit.
- Dropped records receive machine-readable exclusion reasons.

## Identifier namespaces and crosswalks

`WUP City_Code` and `GHSL ID_UC_G0` are source-specific identifiers. Their numeric values are not interchangeable and must never be joined directly. A project `city_id` must include its namespace or be assigned only after an evidence-bearing crosswalk is accepted.

A WUP–GHSL crosswalk requires `wup_city_id`, `ghsl_city_id`, `match_status`, `match_method`, and `evidence`. Accepted matches must be unique on the WUP side. Multiple WUP cities may occupy one GHSL polygon; downstream code must select an explicit aggregation rule rather than duplicating GHSL attributes across WUP rows unnoticed.

## Leakage control

The outcome is future annualized log growth. Lagged growth must end at or before `period_start`. Random row splits are prohibited because they leak adjacent periods and common shocks. Forecast evaluation uses chronological rolling origins, with country-aware diagnostics.

## WUP assembled panel

The WUP city-year assembly is strictly internal to the WUP `City_Code` namespace. It joins F21 population, F25 land area, F30 built-up area per capita, and F34 population density only after exact city-year coverage and the F21/F25/F34 density identity pass validation.

Because F29 is not retrievable, built-up area is derived as F21 population in persons multiplied by F30 square metres per capita. This provenance is recorded as `derived_f21_times_f30`; it must not be represented as a direct F29 observation. F30 publisher zeros are converted to a missing derived area with `publisher_zero_excluded`, while the raw per-capita value remains available for audit.

## Forecast interval contract

One forecast row represents a city at a declared forecast origin and horizon. `period_start` is the forecast origin, while `outcome_start_year` is the first year of the scored outcome. For adjacent designs these years are equal; gapped diagnostics deliberately make `outcome_start_year` later. `recent_growth` must end at the origin, and origin covariates are selected from the origin row only. The interval builder requires exact lag, origin, outcome-start and outcome-end years and records `coverage_selection = complete_lag_origin_outcome_start_end`. Its default outcome universe is estimates; projection outcomes require an explicit caller override.

The optional WUP F01 comparator is `national_city_category_recent_growth`: annualized
log growth in the national harmonized Cities category from `period_start - 5` through
`period_start`. Required country-year endpoints must be positive and complete. The
fields `national_baseline_revision_semantics = WUP_2025_revised_history` and
`national_baseline_uses_future_value = false` prevent this comparator from being
misrepresented as a vintage-real-time national forecast.

WUP aggregation baselines use the F01 country-to-subregion-to-region hierarchy.
Global, region, subregion, and country historical means are computed only from
training outcomes. Their leave-city-out versions subtract every prior outcome for
the focal city before scoring, preventing the aggregation ladder from inheriting a
mechanical city-history advantage.


## Cross-revision forecast-error decomposition

A WUP 2018 projected growth rate scored against WUP 2025 estimated growth is not
identified as pure forecast error. The executable vintage workflow decomposes the
reported growth discrepancy exactly into a target log gap minus an origin log gap.
The target log gap remains an inseparable mixture of true forecast error, target
revision and urban-definition change; the origin log gap contains origin revision
and definition change. The identity residual must be numerically zero.

Only the published 2018 projection and persistence calculated from WUP 2018 are
eligible for a like-for-like 2018 predictor ranking. Persistence recalculated from
WUP 2025 is labeled revised_2025_hindsight and is retained only to measure the
advantage conferred by later revision. No output may label the cross-revision score
as clean real-time forecast accuracy.

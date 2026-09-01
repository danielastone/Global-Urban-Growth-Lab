# Forecast horizon comparability

Annualizing population growth does not make forecast errors from different horizons directly comparable. A five-year forecast and a ten-year forecast have different information sets, shock exposure, and error variance even when both targets are expressed as annualized log growth.

## Locked rule

Persistence benchmark evaluation must use one forecast horizon at a time. Every eligible row must carry a positive `forecast_horizon_years` value, either supplied explicitly by the source-specific builder or deterministically derived from `period_end - period_start` when the forecast interval itself defines the target horizon.

If more than one horizon is present after fitness and point-in-time gates are applied, the common persistence evaluator fails closed. Callers must stratify the panel to a single horizon before computing aggregate metrics or row-level errors.

For Mexico locality histories, `build_mexico_multiwave_history` records `forecast_horizon_years = endpoint_year - origin_year`. This is necessary because the planned event sequence contains both five-year and ten-year transitions. Those intervals may be analyzed separately, but they must not be pooled into one persistence-performance estimate merely because `future_growth` is annualized.

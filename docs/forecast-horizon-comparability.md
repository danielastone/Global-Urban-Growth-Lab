# Forecast horizon comparability

Annualizing population growth does not make forecast errors from different horizons directly comparable. A five-year forecast and a ten-year forecast have different information sets, shock exposure, and error variance even when both targets are expressed as annualized log growth.

## Locked rule

Persistence benchmark evaluation must use one forecast horizon at a time. Every eligible row must carry a positive `forecast_horizon_years` value, either supplied explicitly by the source-specific builder or deterministically derived from the declared outcome interval.

When an outcome gap exists, the forecast horizon is `period_end - outcome_start_year`, not `period_end - period_start`. If only `outcome_gap_years` is recorded, the equivalent derivation is `period_end - (period_start + outcome_gap_years)`. The pre-outcome gap is therefore never counted as target forecast horizon. If an explicit `forecast_horizon_years` value is present alongside derived interval fields, the values must agree or the common fitness gate fails closed.

For simple contiguous intervals with no separate outcome-start or gap field, `period_end - period_start` remains the deterministic fallback.

If more than one horizon is present after fitness and point-in-time gates are applied, the common persistence evaluator fails closed. Callers must stratify the panel to a single horizon before computing aggregate metrics or row-level errors.

For Mexico locality histories, `build_mexico_multiwave_history` records `forecast_horizon_years = endpoint_year - origin_year`. This is necessary because the planned event sequence contains both five-year and ten-year transitions. Those intervals may be analyzed separately, but they must not be pooled into one persistence-performance estimate merely because `future_growth` is annualized.

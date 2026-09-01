"""Origin-defined forecast risk-set coverage diagnostics.

Forecast scoring necessarily uses observed outcomes, but the population of cities
eligible at a forecast origin must not be defined by whether a future outcome is
observed. This module preserves the origin risk-set denominator and makes future
outcome observability an explicit, separately auditable property.
"""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def origin_risk_set_outcome_coverage(
    city_year_panel: pd.DataFrame,
    origins: list[int],
    *,
    lookback_years: int = 5,
    horizon_years: int = 5,
    outcome_gap_years: int = 0,
    allowed_outcome_types: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return row-level and origin-level future-outcome coverage for an origin risk set.

    Risk-set membership uses only lag/origin information. Future endpoint presence
    and allowed outcome type are measured after membership is fixed. Cities with
    missing or disallowed future outcomes therefore remain in the denominator.
    """
    required = {"city_id", "year", "population", "observation_type"}
    require_columns(city_year_panel, required, source_name="forecast coverage source")
    reject_duplicate_keys(
        city_year_panel, ["city_id", "year"], source_name="forecast coverage source"
    )
    if lookback_years <= 0 or horizon_years <= 0 or outcome_gap_years < 0:
        raise SourceSchemaError("Forecast lookback/horizon must be positive and gap non-negative")
    if not origins or any(not isinstance(year, int) for year in origins):
        raise SourceSchemaError("Forecast origins must be a non-empty list of integer years")
    allowed = {"estimate"} if allowed_outcome_types is None else allowed_outcome_types
    if not allowed:
        raise SourceSchemaError("At least one outcome observation type must be allowed")

    source = city_year_panel.set_index(["city_id", "year"])
    city_ids = source.index.get_level_values("city_id").unique()
    frames: list[pd.DataFrame] = []
    for origin in sorted(set(origins)):
        lag_year = origin - lookback_years
        outcome_start_year = origin + outcome_gap_years
        outcome_end_year = outcome_start_year + horizon_years
        required_years = sorted({lag_year, origin, outcome_start_year, outcome_end_year})
        keys = pd.MultiIndex.from_product(
            [city_ids, required_years],
            names=["city_id", "year"],
        )
        wide = source.reindex(keys).reset_index().pivot(index="city_id", columns="year")

        lag_population = wide[("population", lag_year)]
        origin_population = wide[("population", origin)]
        predictor_eligible = lag_population.notna() & origin_population.notna()
        risk = wide.loc[predictor_eligible].copy()
        if risk.empty:
            continue

        outcome_start_population = risk[("population", outcome_start_year)]
        outcome_end_population = risk[("population", outcome_end_year)]
        outcome_start_type = risk[("observation_type", outcome_start_year)]
        outcome_end_type = risk[("observation_type", outcome_end_year)]
        outcome_values_present = outcome_start_population.notna() & outcome_end_population.notna()
        outcome_types_allowed = outcome_start_type.isin(allowed) & outcome_end_type.isin(allowed)
        outcome_observed = outcome_values_present & outcome_types_allowed

        rows = pd.DataFrame(index=risk.index)
        rows["origin"] = origin
        rows["lag_year"] = lag_year
        rows["outcome_start_year"] = outcome_start_year
        rows["outcome_end_year"] = outcome_end_year
        rows["origin_risk_set_member"] = True
        rows["outcome_values_present"] = outcome_values_present
        rows["outcome_types_allowed"] = outcome_types_allowed
        rows["outcome_observed"] = outcome_observed
        rows["outcome_coverage_exclusion_reason"] = ""
        rows.loc[~outcome_values_present, "outcome_coverage_exclusion_reason"] = (
            "missing_future_outcome_value"
        )
        rows.loc[
            outcome_values_present & ~outcome_types_allowed,
            "outcome_coverage_exclusion_reason",
        ] = "future_outcome_type_not_allowed"
        frames.append(rows.reset_index())

    if not frames:
        raise SourceSchemaError("No origin risk-set members have complete lag/origin predictors")

    row_level = pd.concat(frames, ignore_index=True).sort_values(["origin", "city_id"])
    summary = (
        row_level.groupby("origin", as_index=False)
        .agg(
            origin_risk_set_rows=("city_id", "size"),
            observed_outcome_rows=("outcome_observed", "sum"),
            missing_outcome_rows=("outcome_observed", lambda values: int((~values).sum())),
        )
        .sort_values("origin")
        .reset_index(drop=True)
    )
    summary["observed_outcome_share"] = (
        summary["observed_outcome_rows"] / summary["origin_risk_set_rows"]
    )
    summary["coverage_denominator_rule"] = "lag_and_origin_predictors_only"
    summary["future_outcome_used_for_membership"] = False
    return row_level.reset_index(drop=True), summary


def observed_outcome_scoring_keys(coverage_rows: pd.DataFrame) -> pd.DataFrame:
    """Return observed city-origin keys without discarding the auditable denominator."""
    require_columns(
        coverage_rows,
        {"city_id", "origin", "origin_risk_set_member", "outcome_observed"},
        source_name="forecast coverage rows",
    )
    if not pd.api.types.is_bool_dtype(coverage_rows["origin_risk_set_member"].dtype):
        raise SourceSchemaError("origin_risk_set_member must be boolean")
    if not pd.api.types.is_bool_dtype(coverage_rows["outcome_observed"].dtype):
        raise SourceSchemaError("outcome_observed must be boolean")
    if not coverage_rows["origin_risk_set_member"].all():
        raise SourceSchemaError("Coverage table must contain origin risk-set members only")
    return (
        coverage_rows.loc[coverage_rows["outcome_observed"], ["city_id", "origin"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

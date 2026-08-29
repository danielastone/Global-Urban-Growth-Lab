"""Machine-readable audits of forecast-sample construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def _validate_origins(origins: list[int]) -> list[int]:
    if not origins or any(not isinstance(year, int) for year in origins):
        raise SourceSchemaError("Selection-audit origins must be non-empty integer years")
    if len(origins) != len(set(origins)):
        raise SourceSchemaError("Selection-audit origins must be unique")
    return sorted(origins)


def _coverage_flags(
    ledger: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    lookback_years: int,
    horizon_years: int,
    outcome_gap_years: int,
) -> pd.DataFrame:
    require_columns(panel, {"city_id", "year"}, source_name="selection-audit panel")
    reject_duplicate_keys(panel, ["city_id", "year"], source_name="selection-audit panel")
    available = pd.MultiIndex.from_frame(panel[["city_id", "year"]])
    years = {
        "lag_available": ledger["origin"] - lookback_years,
        "origin_available": ledger["origin"],
        "outcome_start_available": ledger["origin"] + outcome_gap_years,
        "outcome_end_available": ledger["origin"] + outcome_gap_years + horizon_years,
    }
    result = ledger.copy()
    for column, year in years.items():
        keys = pd.MultiIndex.from_arrays([result["city_id"], year])
        result[column] = keys.isin(available)
    result["complete_required_years"] = result[list(years)].all(axis=1)
    return result


def _first_false_reason(frame: pd.DataFrame, rules: list[tuple[str, str]]) -> pd.Series:
    conditions = [~frame[column] for column, _ in rules]
    choices = [reason for _, reason in rules]
    return pd.Series(
        np.select(conditions, choices, default="included"), index=frame.index, dtype="string"
    )


def wup_forecast_selection_ledger(
    population_panel: pd.DataFrame,
    analytical_panel: pd.DataFrame,
    origins: list[int],
    *,
    lookback_years: int = 5,
    horizon_years: int = 5,
    outcome_gap_years: int = 0,
    estimate_end_year: int = 2025,
) -> pd.DataFrame:
    """Audit WUP threshold timing and complete-case selection at every origin.

    The universe is every city exposed by F21, including cities whose first
    nonblank value occurs only in the projection period. The analytical panel
    is the stricter F21/F25/F30/F34 intersection used by forecast construction.
    """
    required = {
        "city_id", "year", "population", "ISO3_Code", "City_Name",
        "sample_entry_year", "sample_exit_year", "eligible_at_reference_year",
        "observation_type",
    }
    require_columns(population_panel, required, source_name="WUP population panel")
    reject_duplicate_keys(population_panel, ["city_id", "year"], source_name="WUP population")
    years = _validate_origins(origins)
    if min(lookback_years, horizon_years) <= 0 or outcome_gap_years < 0:
        raise SourceSchemaError("Selection-audit lookback/horizon must be positive")
    population_working = population_panel.copy()
    population_working["_projection_period_observation"] = (
        population_working["year"] > estimate_end_year
    )
    metadata = population_working.sort_values("year").groupby("city_id", as_index=False).agg(
        country_code=("ISO3_Code", "first"),
        city_name=("City_Name", "first"),
        sample_entry_year=("sample_entry_year", "first"),
        sample_exit_year=("sample_exit_year", "first"),
        eligible_at_reference_year=("eligible_at_reference_year", "first"),
        has_projection_period_observation=("_projection_period_observation", "any"),
    )
    universe = metadata.assign(_key=1).merge(
        pd.DataFrame({"origin": years, "_key": 1}), on="_key", validate="many_to_many"
    ).drop(columns="_key")
    population_coverage = _coverage_flags(
        universe,
        population_panel,
        lookback_years=lookback_years,
        horizon_years=horizon_years,
        outcome_gap_years=outcome_gap_years,
    ).rename(
        columns={
            "lag_available": "population_lag_available",
            "origin_available": "population_origin_available",
            "outcome_start_available": "population_outcome_start_available",
            "outcome_end_available": "population_outcome_end_available",
            "complete_required_years": "population_complete_required_years",
        }
    )
    analytical_coverage = _coverage_flags(
        universe[["city_id", "origin"]],
        analytical_panel,
        lookback_years=lookback_years,
        horizon_years=horizon_years,
        outcome_gap_years=outcome_gap_years,
    ).rename(
        columns={
            "lag_available": "analytical_lag_available",
            "origin_available": "analytical_origin_available",
            "outcome_start_available": "analytical_outcome_start_available",
            "outcome_end_available": "analytical_outcome_end_available",
            "complete_required_years": "analytical_complete_required_years",
        }
    )
    analytical_columns = [
        "city_id", "origin", "analytical_lag_available", "analytical_origin_available",
        "analytical_outcome_start_available", "analytical_outcome_end_available",
        "analytical_complete_required_years",
    ]
    result = population_coverage.merge(
        analytical_coverage[analytical_columns],
        on=["city_id", "origin"],
        validate="one_to_one",
    )
    result["entry_occurs_after_forecast_origin"] = result["sample_entry_year"] > result["origin"]
    result["entry_occurs_in_projection_period"] = result["sample_entry_year"] > estimate_end_year
    result["not_eligible_at_2025_reference"] = ~result[
        "eligible_at_reference_year"
    ].astype(bool)
    result["future_projection_selected"] = (
        result["not_eligible_at_2025_reference"]
        & result["has_projection_period_observation"]
    )
    result["outcome_is_estimate"] = (
        result["origin"] + outcome_gap_years + horizon_years <= estimate_end_year
    )
    result["included"] = result["analytical_complete_required_years"] & result[
        "outcome_is_estimate"
    ]
    result["primary_exclusion_reason"] = _first_false_reason(
        result,
        [
            ("population_lag_available", "population_lag_missing_threshold_blank"),
            ("population_origin_available", "population_origin_missing_threshold_blank"),
            (
                "population_outcome_start_available",
                "population_outcome_start_missing_threshold_blank",
            ),
            ("population_outcome_end_available", "population_outcome_end_missing_threshold_blank"),
            ("outcome_is_estimate", "projection_outcome_not_allowed"),
            ("analytical_lag_available", "lag_covariates_missing"),
            ("analytical_origin_available", "origin_covariates_missing"),
            ("analytical_outcome_start_available", "outcome_start_covariates_missing"),
            ("analytical_outcome_end_available", "outcome_end_covariates_missing"),
        ],
    )
    result["source_stream"] = "WUP_2025_DEGURBA_cities"
    result["geographic_comparability"] = "publisher_city_definition_not_fixed_polygon"
    reject_duplicate_keys(result, ["city_id", "origin"], source_name="WUP selection ledger")
    return result.sort_values(["origin", "country_code", "city_id"]).reset_index(drop=True)


def ghsl_forecast_selection_ledger(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    boundary_mode: str,
    lookback_years: int = 5,
    horizon_years: int = 5,
    outcome_gap_years: int = 0,
) -> pd.DataFrame:
    """Audit fixed or dynamic GHSL city-origin coverage without pooling streams."""
    required = {"city_id", "year", "boundary_mode", "GC_CNT_GAD_2025"}
    require_columns(panel, required, source_name="GHSL selection panel")
    if boundary_mode not in {"fixed", "dynamic"}:
        raise SourceSchemaError("GHSL selection audit requires fixed or dynamic mode")
    if panel["boundary_mode"].ne(boundary_mode).any():
        raise SourceSchemaError("GHSL selection panel mixes boundary modes")
    years = _validate_origins(origins)
    metadata_aggregations: dict[str, tuple[str, str]] = {
        "country_code": ("GC_CNT_GAD_2025", "first")
    }
    for source, target in [
        ("GC_UCB_YOB _2025", "trajectory_birth_year"),
        ("GC_UCB_YOD _2025", "trajectory_death_year"),
        ("quality_controlled_2025", "quality_controlled_2025"),
    ]:
        if source in panel.columns:
            metadata_aggregations[target] = (source, "first")
    metadata = panel.groupby("city_id", as_index=False).agg(**metadata_aggregations)
    universe = metadata.assign(_key=1).merge(
        pd.DataFrame({"origin": years, "_key": 1}), on="_key", validate="many_to_many"
    ).drop(columns="_key")
    result = _coverage_flags(
        universe,
        panel,
        lookback_years=lookback_years,
        horizon_years=horizon_years,
        outcome_gap_years=outcome_gap_years,
    )
    if "quality_controlled_2025" not in result:
        result["quality_controlled_2025"] = True
    result["quality_controlled_2025"] = result["quality_controlled_2025"].fillna(False).astype(bool)
    result["conditioned_on_2025_quality"] = boundary_mode == "dynamic"
    result["uses_future_reference_polygon"] = boundary_mode == "fixed"
    result["included"] = result["complete_required_years"] & result[
        "quality_controlled_2025"
    ]
    result["primary_exclusion_reason"] = _first_false_reason(
        result,
        [
            ("quality_controlled_2025", "not_quality_controlled_at_2025"),
            ("lag_available", "trajectory_absent_at_lag"),
            ("origin_available", "trajectory_absent_at_origin"),
            ("outcome_start_available", "trajectory_absent_at_outcome_start"),
            ("outcome_end_available", "trajectory_absent_at_outcome_end"),
        ],
    )
    result["source_stream"] = f"GHSL_2024_{boundary_mode}_boundaries"
    result["geographic_comparability"] = np.where(
        boundary_mode == "fixed",
        "fixed_2025_polygon_using_future_reference",
        "changing_polygon_sensitivity_not_primary_estimand",
    )
    reject_duplicate_keys(result, ["city_id", "origin"], source_name="GHSL selection ledger")
    return result.sort_values(["origin", "country_code", "city_id"]).reset_index(drop=True)


def selection_summary(ledger: pd.DataFrame) -> pd.DataFrame:
    """Summarize inclusion and exclusion counts without hiding the universe."""
    required = {
        "source_stream", "origin", "country_code", "included",
        "primary_exclusion_reason", "geographic_comparability",
    }
    require_columns(ledger, required, source_name="selection ledger")
    summary = ledger.groupby(
        [
            "source_stream", "geographic_comparability", "origin", "included",
            "primary_exclusion_reason",
        ],
        dropna=False,
        sort=True,
    ).agg(
        city_origin_rows=("city_id", "size"),
        countries=("country_code", "nunique"),
    ).reset_index()
    totals = ledger.groupby(["source_stream", "origin"])["city_id"].transform("size")
    working = ledger.assign(_origin_universe=totals)
    denominators = working.groupby(["source_stream", "origin"])["_origin_universe"].first()
    summary["origin_universe_rows"] = pd.MultiIndex.from_frame(
        summary[["source_stream", "origin"]]
    ).map(denominators)
    summary["share_of_origin_universe"] = (
        summary["city_origin_rows"] / summary["origin_universe_rows"]
    )
    return summary

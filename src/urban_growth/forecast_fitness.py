"""Fitness-gated persistence-only out-of-sample forecast evaluation."""

from __future__ import annotations

import pandas as pd

from urban_growth.forecast import evaluate_rolling_baselines, rolling_baseline_errors
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

PERSISTENCE_BASELINE_MODELS = {
    "zero_growth",
    "persistence",
    "country_mean_leave_city_out",
    "region_mean_leave_city_out",
    "subregion_mean_leave_city_out",
    "national_city_category_persistence_leave_city_out",
}


def fitness_gated_forecast_panel(
    panel: pd.DataFrame,
    *,
    eligibility_column: str = "growth_eligible",
) -> pd.DataFrame:
    """Return only explicitly eligible forecast rows.

    Eligibility must already have been produced by a source-specific application of
    the City Data Fitness Standard. Missing eligibility is an error rather than an
    implicit pass.
    """
    require_columns(
        panel,
        {
            "city_id",
            "period_start",
            "period_end",
            "country_code",
            "recent_growth",
            "future_growth",
            eligibility_column,
        },
        source_name="fitness-gated forecast panel",
    )
    reject_duplicate_keys(
        panel,
        ["city_id", "period_start", "period_end"],
        source_name="fitness-gated forecast panel",
    )
    eligibility = panel[eligibility_column]
    if not pd.api.types.is_bool_dtype(eligibility.dtype):
        raise SourceSchemaError(f"{eligibility_column} must be boolean")
    result = panel.loc[eligibility].copy()
    if result.empty:
        raise SourceSchemaError("No forecast rows pass the declared data-fitness gate")
    result["forecast_fitness_gate"] = eligibility_column
    result["forecast_fitness_gate_passed"] = True
    return result.reset_index(drop=True)


def _validate_multi_origin_oos(panel: pd.DataFrame, origins: list[int]) -> list[int]:
    if not origins or len(set(origins)) != len(origins):
        raise SourceSchemaError("Forecast origins must be unique and non-empty")
    declared = sorted(origins)
    available = set(panel["period_start"].unique())
    missing = [origin for origin in declared if origin not in available]
    if missing:
        raise SourceSchemaError(f"Fitness-eligible panel lacks declared origins: {missing}")
    usable = []
    for origin in declared:
        has_train = panel["period_end"].le(origin).any()
        has_test = panel["period_start"].eq(origin).any()
        if has_train and has_test:
            usable.append(origin)
    if len(usable) < 2:
        raise SourceSchemaError(
            "Persistence OOS benchmark requires at least two rolling origins with "
            "fitness-eligible training and test rows"
        )
    return usable


def evaluate_fitness_gated_persistence_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Evaluate the locked simple-baseline ladder on eligible rows only."""
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    usable_origins = _validate_multi_origin_oos(gated, origins)
    result = evaluate_rolling_baselines(gated, usable_origins, outcome_column=outcome_column)
    result = result.loc[result["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
    if "persistence" not in set(result["model"]):
        raise SourceSchemaError("Persistence baseline was not produced")
    if "zero_growth" not in set(result["model"]):
        raise SourceSchemaError("Zero-growth baseline was not produced")
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["benchmark_stage"] = "persistence_only"
    return result.sort_values(["origin", "model"]).reset_index(drop=True)


def fitness_gated_persistence_errors(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Return row-level errors for the same locked fitness-gated baseline ladder."""
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    usable_origins = _validate_multi_origin_oos(gated, origins)
    result = rolling_baseline_errors(gated, usable_origins, outcome_column=outcome_column)
    result = result.loc[result["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
    if result.empty:
        raise SourceSchemaError("No persistence-stage row-level errors were produced")
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["benchmark_stage"] = "persistence_only"
    return result.reset_index(drop=True)

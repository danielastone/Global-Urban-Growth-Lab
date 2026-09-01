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


def _attach_forecast_horizon(panel: pd.DataFrame) -> pd.DataFrame:
    """Attach the target horizon without counting any pre-outcome gap as forecast time."""
    out = panel.copy()
    period_end = pd.to_numeric(out["period_end"], errors="coerce")
    period_start = pd.to_numeric(out["period_start"], errors="coerce")

    derived: pd.Series | None = None
    if "outcome_start_year" in out.columns:
        outcome_start = pd.to_numeric(out["outcome_start_year"], errors="coerce")
        derived = period_end - outcome_start
    elif "outcome_gap_years" in out.columns:
        outcome_gap = pd.to_numeric(out["outcome_gap_years"], errors="coerce")
        derived = period_end - (period_start + outcome_gap)
    elif "forecast_horizon_years" not in out.columns:
        derived = period_end - period_start

    explicit: pd.Series | None = None
    if "forecast_horizon_years" in out.columns:
        explicit = pd.to_numeric(out["forecast_horizon_years"], errors="coerce")

    if explicit is not None and derived is not None:
        mismatch = explicit.notna() & derived.notna() & explicit.ne(derived)
        if mismatch.any():
            raise SourceSchemaError(
                "Explicit forecast_horizon_years disagrees with the declared outcome interval"
            )

    horizon = explicit if explicit is not None else derived
    if horizon is None or horizon.isna().any() or horizon.le(0).any():
        raise SourceSchemaError("forecast_horizon_years must be positive and known for every row")
    out["forecast_horizon_years"] = horizon.astype(float)
    return out


def fitness_gated_forecast_panel(
    panel: pd.DataFrame,
    *,
    eligibility_column: str = "growth_eligible",
) -> pd.DataFrame:
    """Return only explicitly eligible forecast rows."""
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
    result = _attach_forecast_horizon(panel.loc[eligibility].copy())
    if result.empty:
        raise SourceSchemaError("No forecast rows pass the declared data-fitness gate")
    result["forecast_fitness_gate"] = eligibility_column
    result["forecast_fitness_gate_passed"] = True
    return result.reset_index(drop=True)


def point_in_time_fitness_gated_forecast_panel(
    panel: pd.DataFrame,
    *,
    eligibility_column: str = "growth_eligible",
    availability_column: str = "point_in_time_available",
    provenance_column: str = "availability_provenance_verified",
) -> pd.DataFrame:
    """Return rows passing fitness plus an auditable point-in-time availability gate."""
    require_columns(
        panel,
        {availability_column, provenance_column},
        source_name="point-in-time forecast panel",
    )
    availability = panel[availability_column]
    provenance = panel[provenance_column]
    if not pd.api.types.is_bool_dtype(availability.dtype):
        raise SourceSchemaError(f"{availability_column} must be boolean")
    if not pd.api.types.is_bool_dtype(provenance.dtype):
        raise SourceSchemaError(f"{provenance_column} must be boolean")
    if not provenance.all():
        raise SourceSchemaError(
            "Point-in-time persistence requires verified availability provenance for every row"
        )
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    result = gated.loc[gated[availability_column] & gated[provenance_column]].copy()
    if result.empty:
        raise SourceSchemaError("No forecast rows pass both fitness and point-in-time gates")
    result["forecast_availability_gate"] = availability_column
    result["forecast_availability_gate_passed"] = True
    result["forecast_availability_provenance_gate"] = provenance_column
    result["forecast_availability_provenance_gate_passed"] = True
    return result.reset_index(drop=True)


def _validate_single_horizon(panel: pd.DataFrame) -> float:
    horizons = sorted(pd.unique(panel["forecast_horizon_years"]))
    if len(horizons) != 1:
        raise SourceSchemaError(
            "Persistence benchmark cannot pool mixed forecast horizons; stratify to one "
            f"forecast_horizon_years value before evaluation: {horizons}"
        )
    return float(horizons[0])


def _validate_declared_origins(panel: pd.DataFrame, origins: list[int]) -> list[int]:
    if not origins or len(set(origins)) != len(origins):
        raise SourceSchemaError("Forecast origins must be unique and non-empty")
    declared = sorted(origins)
    available = set(panel["period_start"].unique())
    missing = [origin for origin in declared if origin not in available]
    if missing:
        raise SourceSchemaError(f"Fitness-eligible panel lacks declared origins: {missing}")
    return declared


def _validate_multi_origin_oos(panel: pd.DataFrame, origins: list[int]) -> list[int]:
    declared = _validate_declared_origins(panel, origins)
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


def _origin_specific_point_in_time_panel(
    panel: pd.DataFrame,
    origin: int,
    *,
    forecast_origin_date_column: str,
    outcome_available_column: str,
) -> tuple[pd.DataFrame, int, int]:
    """Return one origin's test rows plus only training outcomes published by its as-of date."""
    require_columns(
        panel,
        {forecast_origin_date_column, outcome_available_column},
        source_name="point-in-time persistence panel",
    )
    test = panel.loc[panel["period_start"].eq(origin)].copy()
    if test.empty:
        raise SourceSchemaError(f"Point-in-time panel lacks test rows for origin {origin}")
    origin_dates = pd.to_datetime(test[forecast_origin_date_column], errors="coerce")
    if origin_dates.isna().any() or origin_dates.nunique() != 1:
        raise SourceSchemaError(
            f"{forecast_origin_date_column} must resolve to one valid date per forecast origin"
        )
    as_of = origin_dates.iloc[0]
    outcome_available = pd.to_datetime(panel[outcome_available_column], errors="coerce")
    if outcome_available.isna().any():
        raise SourceSchemaError(
            f"{outcome_available_column} must be known for every point-in-time forecast row"
        )
    candidate_train = panel["period_end"].le(origin)
    available_train = candidate_train & outcome_available.le(as_of)
    train = panel.loc[available_train].copy()
    if train.empty:
        raise SourceSchemaError(f"No training outcomes were published by forecast origin {origin}")
    combined = pd.concat([train, test], ignore_index=True)
    reject_duplicate_keys(
        combined,
        ["city_id", "period_start", "period_end"],
        source_name=f"point-in-time persistence origin {origin}",
    )
    return combined, int(candidate_train.sum()), int(available_train.sum())


def _evaluate_persistence_baselines(
    gated: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str,
    outcome_column: str,
    benchmark_stage: str,
) -> pd.DataFrame:
    horizon = _validate_single_horizon(gated)
    usable_origins = _validate_multi_origin_oos(gated, origins)
    result = evaluate_rolling_baselines(gated, usable_origins, outcome_column=outcome_column)
    result = result.loc[result["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
    if "persistence" not in set(result["model"]):
        raise SourceSchemaError("Persistence baseline was not produced")
    if "zero_growth" not in set(result["model"]):
        raise SourceSchemaError("Zero-growth baseline was not produced")
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["benchmark_stage"] = benchmark_stage
    result["forecast_horizon_years"] = horizon
    return result.sort_values(["origin", "model"]).reset_index(drop=True)


def evaluate_fitness_gated_persistence_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Evaluate retrospective persistence baselines on fitness-eligible rows only."""
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    return _evaluate_persistence_baselines(
        gated,
        origins,
        eligibility_column=eligibility_column,
        outcome_column=outcome_column,
        benchmark_stage="retrospective_persistence_only",
    )


def evaluate_point_in_time_persistence_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    availability_column: str = "point_in_time_available",
    provenance_column: str = "availability_provenance_verified",
    forecast_origin_date_column: str = "forecast_origin_date",
    outcome_available_column: str = "outcome_available_date",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Evaluate deployable persistence baselines with auditable timing gates."""
    gated = point_in_time_fitness_gated_forecast_panel(
        panel,
        eligibility_column=eligibility_column,
        availability_column=availability_column,
        provenance_column=provenance_column,
    )
    horizon = _validate_single_horizon(gated)
    declared = _validate_declared_origins(gated, origins)
    frames: list[pd.DataFrame] = []
    for origin in declared:
        try:
            origin_panel, candidate_train_n, available_train_n = _origin_specific_point_in_time_panel(
                gated,
                origin,
                forecast_origin_date_column=forecast_origin_date_column,
                outcome_available_column=outcome_available_column,
            )
        except SourceSchemaError as exc:
            if "No training outcomes were published" in str(exc):
                continue
            raise
        scored = evaluate_rolling_baselines(origin_panel, [origin], outcome_column=outcome_column)
        scored = scored.loc[scored["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
        if scored.empty:
            continue
        scored["candidate_training_rows"] = candidate_train_n
        scored["available_training_rows"] = available_train_n
        scored["training_outcome_availability_enforced"] = True
        frames.append(scored)
    if len(frames) < 2:
        raise SourceSchemaError(
            "Point-in-time persistence benchmark requires at least two origins with published "
            "training outcomes and eligible test rows"
        )
    result = pd.concat(frames, ignore_index=True)
    if "persistence" not in set(result["model"]) or "zero_growth" not in set(result["model"]):
        raise SourceSchemaError("Required persistence-stage baselines were not produced")
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["availability_gate"] = availability_column
    result["availability_gate_enforced"] = True
    result["availability_provenance_gate"] = provenance_column
    result["availability_provenance_gate_enforced"] = True
    result["training_outcome_availability_column"] = outcome_available_column
    result["benchmark_stage"] = "point_in_time_persistence_only"
    result["forecast_horizon_years"] = horizon
    return result.sort_values(["origin", "model"]).reset_index(drop=True)


def fitness_gated_persistence_errors(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Return retrospective row-level errors for the fitness-gated baseline ladder."""
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    horizon = _validate_single_horizon(gated)
    usable_origins = _validate_multi_origin_oos(gated, origins)
    result = rolling_baseline_errors(gated, usable_origins, outcome_column=outcome_column)
    result = result.loc[result["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
    if result.empty:
        raise SourceSchemaError("No persistence-stage row-level errors were produced")
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["benchmark_stage"] = "retrospective_persistence_only"
    result["forecast_horizon_years"] = horizon
    return result.reset_index(drop=True)


def point_in_time_persistence_errors(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    availability_column: str = "point_in_time_available",
    provenance_column: str = "availability_provenance_verified",
    forecast_origin_date_column: str = "forecast_origin_date",
    outcome_available_column: str = "outcome_available_date",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Return row-level errors after auditable predictor and training-outcome timing gates."""
    gated = point_in_time_fitness_gated_forecast_panel(
        panel,
        eligibility_column=eligibility_column,
        availability_column=availability_column,
        provenance_column=provenance_column,
    )
    horizon = _validate_single_horizon(gated)
    declared = _validate_declared_origins(gated, origins)
    frames: list[pd.DataFrame] = []
    for origin in declared:
        try:
            origin_panel, candidate_train_n, available_train_n = _origin_specific_point_in_time_panel(
                gated,
                origin,
                forecast_origin_date_column=forecast_origin_date_column,
                outcome_available_column=outcome_available_column,
            )
        except SourceSchemaError as exc:
            if "No training outcomes were published" in str(exc):
                continue
            raise
        scored = rolling_baseline_errors(origin_panel, [origin], outcome_column=outcome_column)
        scored = scored.loc[scored["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
        if scored.empty:
            continue
        scored["candidate_training_rows"] = candidate_train_n
        scored["available_training_rows"] = available_train_n
        scored["training_outcome_availability_enforced"] = True
        frames.append(scored)
    if len(frames) < 2:
        raise SourceSchemaError(
            "Point-in-time persistence errors require at least two origins with published "
            "training outcomes and eligible test rows"
        )
    result = pd.concat(frames, ignore_index=True)
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["availability_gate"] = availability_column
    result["availability_gate_enforced"] = True
    result["availability_provenance_gate"] = provenance_column
    result["availability_provenance_gate_enforced"] = True
    result["training_outcome_availability_column"] = outcome_available_column
    result["benchmark_stage"] = "point_in_time_persistence_only"
    result["forecast_horizon_years"] = horizon
    return result.reset_index(drop=True)

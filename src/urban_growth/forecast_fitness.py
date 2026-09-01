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
    out = panel.copy()
    period_end = pd.to_numeric(out["period_end"], errors="coerce")
    period_start = pd.to_numeric(out["period_start"], errors="coerce")
    derived: pd.Series | None = None
    if "outcome_start_year" in out.columns:
        derived = period_end - pd.to_numeric(out["outcome_start_year"], errors="coerce")
    elif "outcome_gap_years" in out.columns:
        gap = pd.to_numeric(out["outcome_gap_years"], errors="coerce")
        derived = period_end - (period_start + gap)
    elif "forecast_horizon_years" not in out.columns:
        derived = period_end - period_start
    explicit = (
        pd.to_numeric(out["forecast_horizon_years"], errors="coerce")
        if "forecast_horizon_years" in out.columns
        else None
    )
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
    origin_registration_column: str = "forecast_origin_registration_verified",
) -> pd.DataFrame:
    require_columns(
        panel,
        {availability_column, provenance_column, origin_registration_column},
        source_name="point-in-time forecast panel",
    )
    availability = panel[availability_column]
    provenance = panel[provenance_column]
    origin_registration = panel[origin_registration_column]
    if not pd.api.types.is_bool_dtype(availability.dtype):
        raise SourceSchemaError(f"{availability_column} must be boolean")
    if not pd.api.types.is_bool_dtype(provenance.dtype):
        raise SourceSchemaError(f"{provenance_column} must be boolean")
    if not pd.api.types.is_bool_dtype(origin_registration.dtype):
        raise SourceSchemaError(f"{origin_registration_column} must be boolean")
    if not provenance.all():
        raise SourceSchemaError(
            "Point-in-time persistence requires verified availability provenance for every row"
        )
    if not origin_registration.all():
        raise SourceSchemaError(
            "Point-in-time persistence requires verified forecast-origin registration for every row"
        )
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    result = gated.loc[
        gated[availability_column]
        & gated[provenance_column]
        & gated[origin_registration_column]
    ].copy()
    if result.empty:
        raise SourceSchemaError("No forecast rows pass fitness and point-in-time gates")
    result["forecast_availability_gate"] = availability_column
    result["forecast_availability_gate_passed"] = True
    result["forecast_availability_provenance_gate"] = provenance_column
    result["forecast_availability_provenance_gate_passed"] = True
    result["forecast_origin_registration_gate"] = origin_registration_column
    result["forecast_origin_registration_gate_passed"] = True
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
        if panel["period_end"].le(origin).any() and panel["period_start"].eq(origin).any():
            usable.append(origin)
    if len(usable) < 2:
        raise SourceSchemaError(
            "Persistence OOS benchmark requires at least two rolling origins with "
            "fitness-eligible training and test rows"
        )
    return usable


def _nonblank_strings(panel: pd.DataFrame, column: str) -> pd.Series:
    values = panel[column].astype("string").str.strip()
    if values.isna().any() or values.eq("").any():
        raise SourceSchemaError(f"{column} must provide provenance for every availability date")
    return values


def _point_in_time_evidence_panel(
    panel: pd.DataFrame,
    *,
    eligibility_column: str,
    availability_column: str,
    provenance_column: str,
    origin_registration_column: str,
    predictor_available_column: str,
    concordance_available_column: str,
    predictor_reference_column: str,
    concordance_reference_column: str,
    outcome_available_column: str,
    outcome_available_reference_column: str,
) -> pd.DataFrame:
    required = {
        availability_column,
        provenance_column,
        origin_registration_column,
        predictor_available_column,
        concordance_available_column,
        predictor_reference_column,
        concordance_reference_column,
        outcome_available_column,
        outcome_available_reference_column,
    }
    require_columns(panel, required, source_name="point-in-time persistence evidence panel")
    for column in (availability_column, provenance_column, origin_registration_column):
        if not pd.api.types.is_bool_dtype(panel[column].dtype):
            raise SourceSchemaError(f"{column} must be boolean")
    if not panel[provenance_column].all():
        raise SourceSchemaError(
            "Point-in-time persistence requires verified availability provenance for every row"
        )
    if not panel[origin_registration_column].all():
        raise SourceSchemaError(
            "Point-in-time persistence requires verified forecast-origin registration for every row"
        )
    _nonblank_strings(panel, predictor_reference_column)
    _nonblank_strings(panel, concordance_reference_column)
    _nonblank_strings(panel, outcome_available_reference_column)
    for column in (
        predictor_available_column,
        concordance_available_column,
        outcome_available_column,
    ):
        if pd.to_datetime(panel[column], errors="coerce").isna().any():
            raise SourceSchemaError(f"{column} must be known for every point-in-time forecast row")
    return fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)


def _origin_specific_point_in_time_panel(
    panel: pd.DataFrame,
    origin: int,
    *,
    availability_column: str,
    forecast_origin_date_column: str,
    predictor_available_column: str,
    concordance_available_column: str,
    outcome_available_column: str,
) -> tuple[pd.DataFrame, int, int]:
    test_all = panel.loc[panel["period_start"].eq(origin)].copy()
    if test_all.empty:
        raise SourceSchemaError(f"Point-in-time panel lacks test rows for origin {origin}")
    origin_dates = pd.to_datetime(test_all[forecast_origin_date_column], errors="coerce")
    if origin_dates.isna().any() or origin_dates.nunique() != 1:
        raise SourceSchemaError(
            f"{forecast_origin_date_column} must resolve to one valid date per forecast origin"
        )
    as_of = origin_dates.iloc[0]
    test = test_all.loc[test_all[availability_column]].copy()
    if test.empty:
        raise SourceSchemaError(f"No test rows were available at forecast origin {origin}")

    predictor_available = pd.to_datetime(panel[predictor_available_column], errors="coerce")
    concordance_available = pd.to_datetime(panel[concordance_available_column], errors="coerce")
    outcome_available = pd.to_datetime(panel[outcome_available_column], errors="coerce")
    candidate_train = panel["period_end"].le(origin)
    available_train = (
        candidate_train
        & predictor_available.le(as_of)
        & concordance_available.le(as_of)
        & outcome_available.le(as_of)
    )
    train = panel.loc[available_train].copy()
    if train.empty:
        raise SourceSchemaError(f"No training evidence was available by forecast origin {origin}")
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
    gated = fitness_gated_forecast_panel(panel, eligibility_column=eligibility_column)
    return _evaluate_persistence_baselines(
        gated,
        origins,
        eligibility_column=eligibility_column,
        outcome_column=outcome_column,
        benchmark_stage="retrospective_persistence_only",
    )


def _evaluate_point_in_time(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    row_errors: bool,
    eligibility_column: str,
    availability_column: str,
    provenance_column: str,
    origin_registration_column: str,
    forecast_origin_date_column: str,
    predictor_available_column: str,
    concordance_available_column: str,
    predictor_reference_column: str,
    concordance_reference_column: str,
    outcome_available_column: str,
    outcome_available_reference_column: str,
    outcome_column: str,
) -> pd.DataFrame:
    gated = _point_in_time_evidence_panel(
        panel,
        eligibility_column=eligibility_column,
        availability_column=availability_column,
        provenance_column=provenance_column,
        origin_registration_column=origin_registration_column,
        predictor_available_column=predictor_available_column,
        concordance_available_column=concordance_available_column,
        predictor_reference_column=predictor_reference_column,
        concordance_reference_column=concordance_reference_column,
        outcome_available_column=outcome_available_column,
        outcome_available_reference_column=outcome_available_reference_column,
    )
    horizon = _validate_single_horizon(gated)
    declared = _validate_declared_origins(gated, origins)
    frames: list[pd.DataFrame] = []
    for origin in declared:
        try:
            origin_panel, candidate_train_n, available_train_n = _origin_specific_point_in_time_panel(
                gated,
                origin,
                availability_column=availability_column,
                forecast_origin_date_column=forecast_origin_date_column,
                predictor_available_column=predictor_available_column,
                concordance_available_column=concordance_available_column,
                outcome_available_column=outcome_available_column,
            )
        except SourceSchemaError as exc:
            if "No training evidence was available" in str(exc) or "No test rows were available" in str(exc):
                continue
            raise
        scorer = rolling_baseline_errors if row_errors else evaluate_rolling_baselines
        scored = scorer(origin_panel, [origin], outcome_column=outcome_column)
        scored = scored.loc[scored["model"].isin(PERSISTENCE_BASELINE_MODELS)].copy()
        if scored.empty:
            continue
        scored["candidate_training_rows"] = candidate_train_n
        scored["available_training_rows"] = available_train_n
        scored["training_predictor_availability_enforced"] = True
        scored["training_concordance_availability_enforced"] = True
        scored["training_outcome_availability_enforced"] = True
        scored["training_availability_provenance_enforced"] = True
        scored["training_uses_current_origin_as_of"] = True
        frames.append(scored)
    if len(frames) < 2:
        raise SourceSchemaError(
            "Point-in-time persistence requires at least two origins with available training evidence and test rows"
        )
    result = pd.concat(frames, ignore_index=True)
    if not row_errors and (
        "persistence" not in set(result["model"]) or "zero_growth" not in set(result["model"])
    ):
        raise SourceSchemaError("Required persistence-stage baselines were not produced")
    result["fitness_gate"] = eligibility_column
    result["fitness_gate_enforced"] = True
    result["availability_gate"] = availability_column
    result["availability_gate_enforced"] = True
    result["availability_provenance_gate"] = provenance_column
    result["availability_provenance_gate_enforced"] = True
    result["forecast_origin_registration_gate"] = origin_registration_column
    result["forecast_origin_registration_gate_enforced"] = True
    result["training_predictor_availability_column"] = predictor_available_column
    result["training_concordance_availability_column"] = concordance_available_column
    result["training_outcome_availability_column"] = outcome_available_column
    result["training_outcome_provenance_column"] = outcome_available_reference_column
    result["benchmark_stage"] = "point_in_time_persistence_only"
    result["forecast_horizon_years"] = horizon
    if row_errors:
        return result.reset_index(drop=True)
    return result.sort_values(["origin", "model"]).reset_index(drop=True)


def evaluate_point_in_time_persistence_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    availability_column: str = "point_in_time_available",
    provenance_column: str = "availability_provenance_verified",
    origin_registration_column: str = "forecast_origin_registration_verified",
    forecast_origin_date_column: str = "forecast_origin_date",
    predictor_available_column: str = "predictor_available_date",
    concordance_available_column: str = "concordance_available_date",
    predictor_reference_column: str = "predictor_availability_source",
    concordance_reference_column: str = "concordance_availability_source",
    outcome_available_column: str = "outcome_available_date",
    outcome_available_reference_column: str = "outcome_available_reference",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    return _evaluate_point_in_time(
        panel,
        origins,
        row_errors=False,
        eligibility_column=eligibility_column,
        availability_column=availability_column,
        provenance_column=provenance_column,
        origin_registration_column=origin_registration_column,
        forecast_origin_date_column=forecast_origin_date_column,
        predictor_available_column=predictor_available_column,
        concordance_available_column=concordance_available_column,
        predictor_reference_column=predictor_reference_column,
        concordance_reference_column=concordance_reference_column,
        outcome_available_column=outcome_available_column,
        outcome_available_reference_column=outcome_available_reference_column,
        outcome_column=outcome_column,
    )


def fitness_gated_persistence_errors(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    eligibility_column: str = "growth_eligible",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
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
    origin_registration_column: str = "forecast_origin_registration_verified",
    forecast_origin_date_column: str = "forecast_origin_date",
    predictor_available_column: str = "predictor_available_date",
    concordance_available_column: str = "concordance_available_date",
    predictor_reference_column: str = "predictor_availability_source",
    concordance_reference_column: str = "concordance_availability_source",
    outcome_available_column: str = "outcome_available_date",
    outcome_available_reference_column: str = "outcome_available_reference",
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    return _evaluate_point_in_time(
        panel,
        origins,
        row_errors=True,
        eligibility_column=eligibility_column,
        availability_column=availability_column,
        provenance_column=provenance_column,
        origin_registration_column=origin_registration_column,
        forecast_origin_date_column=forecast_origin_date_column,
        predictor_available_column=predictor_available_column,
        concordance_available_column=concordance_available_column,
        predictor_reference_column=predictor_reference_column,
        concordance_reference_column=concordance_reference_column,
        outcome_available_column=outcome_available_column,
        outcome_available_reference_column=outcome_available_reference_column,
        outcome_column=outcome_column,
    )

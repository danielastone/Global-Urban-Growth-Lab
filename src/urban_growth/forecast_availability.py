"""Point-in-time availability gate for rolling forecast panels."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def apply_forecast_availability_gate(
    panel: pd.DataFrame,
    *,
    origin_column: str = "forecast_origin_date",
    predictor_available_column: str = "predictor_available_date",
    concordance_available_column: str = "concordance_available_date",
) -> pd.DataFrame:
    """Mark whether predictor evidence was actually available at forecast origin.

    Reference periods are not publication dates, and integer origin years are not
    timestamps. A historical predictor may only be called deployable at an origin
    when an explicit forecast-origin date is supplied and both its statistical
    payload and any geography/concordance evidence needed to construct it were
    available no later than that date.
    """
    require_columns(
        panel,
        {
            "city_id",
            "period_start",
            "period_end",
            origin_column,
            predictor_available_column,
            concordance_available_column,
        },
        source_name="forecast availability panel",
    )
    reject_duplicate_keys(
        panel,
        ["city_id", "period_start", "period_end"],
        source_name="forecast availability panel",
    )
    out = panel.copy()
    origin = pd.to_datetime(out[origin_column], errors="coerce")
    predictor_available = pd.to_datetime(out[predictor_available_column], errors="coerce")
    concordance_available = pd.to_datetime(out[concordance_available_column], errors="coerce")
    if origin.isna().any():
        raise SourceSchemaError(f"{origin_column} must contain valid forecast-origin dates")
    if predictor_available.isna().any():
        raise SourceSchemaError(f"{predictor_available_column} must be known for every forecast row")
    if concordance_available.isna().any():
        raise SourceSchemaError(f"{concordance_available_column} must be known for every forecast row")

    out["predictor_available_at_origin"] = predictor_available.le(origin)
    out["concordance_available_at_origin"] = concordance_available.le(origin)
    out["point_in_time_available"] = (
        out["predictor_available_at_origin"] & out["concordance_available_at_origin"]
    )
    out["availability_exclusion_reason"] = ""
    out.loc[~out["predictor_available_at_origin"], "availability_exclusion_reason"] = (
        "predictor_not_available_at_origin"
    )
    out.loc[
        out["predictor_available_at_origin"] & ~out["concordance_available_at_origin"],
        "availability_exclusion_reason",
    ] = "concordance_not_available_at_origin"
    out["forecast_deployable_at_origin"] = out["point_in_time_available"]
    return out


def point_in_time_forecast_sample(panel: pd.DataFrame) -> pd.DataFrame:
    """Return only rows whose required predictor evidence existed at the origin."""
    require_columns(
        panel,
        {"point_in_time_available"},
        source_name="forecast availability panel",
    )
    eligible = panel["point_in_time_available"]
    if not pd.api.types.is_bool_dtype(eligible.dtype):
        raise SourceSchemaError("point_in_time_available must be boolean")
    return panel.loc[eligible].copy().reset_index(drop=True)

"""Point-in-time availability gate for rolling forecast panels."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def _require_availability_provenance(frame: pd.DataFrame, column: str) -> pd.Series:
    """Return normalized nonblank provenance strings for an availability field."""
    values = frame[column].astype("string").str.strip()
    missing = values.isna() | values.eq("")
    if missing.any():
        raise SourceSchemaError(
            f"{column} must identify the source evidence supporting every availability date"
        )
    return values


def apply_forecast_availability_gate(
    panel: pd.DataFrame,
    *,
    origin_column: str = "forecast_origin_date",
    predictor_available_column: str = "predictor_available_date",
    concordance_available_column: str = "concordance_available_date",
    predictor_provenance_column: str = "predictor_availability_source",
    concordance_provenance_column: str = "concordance_availability_source",
) -> pd.DataFrame:
    """Mark whether auditable predictor evidence was available at forecast origin.

    Reference periods are not publication dates, and integer origin years are not
    timestamps. A historical predictor may only be called deployable at an origin
    when an explicit forecast-origin date is supplied, both statistical and
    geography/concordance evidence were available no later than that date, and the
    claimed first-availability dates have nonblank source provenance.
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
            predictor_provenance_column,
            concordance_provenance_column,
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

    out[predictor_provenance_column] = _require_availability_provenance(
        out, predictor_provenance_column
    )
    out[concordance_provenance_column] = _require_availability_provenance(
        out, concordance_provenance_column
    )
    out["availability_provenance_verified"] = True
    out["predictor_available_at_origin"] = predictor_available.le(origin)
    out["concordance_available_at_origin"] = concordance_available.le(origin)
    out["point_in_time_available"] = (
        out["predictor_available_at_origin"]
        & out["concordance_available_at_origin"]
        & out["availability_provenance_verified"]
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
        {"point_in_time_available", "availability_provenance_verified"},
        source_name="forecast availability panel",
    )
    eligible = panel["point_in_time_available"]
    provenance = panel["availability_provenance_verified"]
    if not pd.api.types.is_bool_dtype(eligible.dtype):
        raise SourceSchemaError("point_in_time_available must be boolean")
    if not pd.api.types.is_bool_dtype(provenance.dtype) or not provenance.all():
        raise SourceSchemaError("Point-in-time sample requires verified availability provenance")
    return panel.loc[eligible].copy().reset_index(drop=True)

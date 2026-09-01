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


def _validate_forecast_origin_registration(
    frame: pd.DataFrame,
    *,
    origin_column: str,
    registration_column: str,
) -> pd.Series:
    """Validate that rolling forecast origins follow one registered calendar rule."""
    registration = frame[registration_column].astype("string").str.strip()
    if registration.isna().any() or registration.eq("").any():
        raise SourceSchemaError(
            f"{registration_column} must document the predeclared forecast-origin rule"
        )

    origin = pd.to_datetime(frame[origin_column], errors="coerce")
    if origin.isna().any():
        raise SourceSchemaError(f"{origin_column} must contain valid forecast-origin dates")

    period_start = pd.to_numeric(frame["period_start"], errors="coerce")
    if period_start.isna().any() or period_start.mod(1).ne(0).any():
        raise SourceSchemaError("period_start must contain integer forecast-origin years")
    origin_year = origin.dt.year.astype(float)
    if origin_year.ne(period_start).any():
        raise SourceSchemaError(
            f"{origin_column} must fall within the year declared by period_start"
        )

    origin_frame = pd.DataFrame(
        {
            "period_start": period_start.astype(int),
            "origin_date": origin.dt.normalize(),
            "calendar_rule": origin.dt.strftime("%m-%d"),
        }
    )
    if origin_frame.groupby("period_start")["origin_date"].nunique().gt(1).any():
        raise SourceSchemaError(
            f"{origin_column} must resolve to one as-of date per forecast-origin year"
        )
    if origin_frame["calendar_rule"].nunique() != 1:
        raise SourceSchemaError(
            f"{origin_column} must follow one registered month-day rule across rolling origins"
        )
    if registration.nunique() != 1:
        raise SourceSchemaError(
            f"{registration_column} must identify one registered origin rule for the panel"
        )
    return registration


def apply_forecast_availability_gate(
    panel: pd.DataFrame,
    *,
    origin_column: str = "forecast_origin_date",
    predictor_available_column: str = "predictor_available_date",
    concordance_available_column: str = "concordance_available_date",
    predictor_provenance_column: str = "predictor_availability_source",
    concordance_provenance_column: str = "concordance_availability_source",
    origin_registration_column: str = "forecast_origin_registration",
) -> pd.DataFrame:
    """Mark whether auditable predictor evidence was available at a registered origin.

    Reference periods are not publication dates, and integer origin years are not
    timestamps. A historical predictor may only be called deployable when its as-of
    date follows a predeclared rolling-origin rule, both statistical and geography
    evidence were available by that date, and the claimed first-availability dates
    have nonblank source provenance.
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
            origin_registration_column,
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
    if predictor_available.isna().any():
        raise SourceSchemaError(f"{predictor_available_column} must be known for every forecast row")
    if concordance_available.isna().any():
        raise SourceSchemaError(f"{concordance_available_column} must be known for every forecast row")

    out[origin_registration_column] = _validate_forecast_origin_registration(
        out,
        origin_column=origin_column,
        registration_column=origin_registration_column,
    )
    out["forecast_origin_registration_verified"] = True
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
        & out["forecast_origin_registration_verified"]
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
    """Return only rows whose required evidence existed at a registered origin."""
    require_columns(
        panel,
        {
            "point_in_time_available",
            "availability_provenance_verified",
            "forecast_origin_registration_verified",
        },
        source_name="forecast availability panel",
    )
    eligible = panel["point_in_time_available"]
    provenance = panel["availability_provenance_verified"]
    origin_registration = panel["forecast_origin_registration_verified"]
    if not pd.api.types.is_bool_dtype(eligible.dtype):
        raise SourceSchemaError("point_in_time_available must be boolean")
    if not pd.api.types.is_bool_dtype(provenance.dtype) or not provenance.all():
        raise SourceSchemaError("Point-in-time sample requires verified availability provenance")
    if not pd.api.types.is_bool_dtype(origin_registration.dtype) or not origin_registration.all():
        raise SourceSchemaError("Point-in-time sample requires verified forecast-origin registration")
    return panel.loc[eligible].copy().reset_index(drop=True)

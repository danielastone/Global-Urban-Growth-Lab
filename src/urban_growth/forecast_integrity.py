"""Recompute point-in-time forecast eligibility from raw evidence before scoring."""

from __future__ import annotations

import pandas as pd

from urban_growth.forecast_availability import apply_forecast_availability_gate
from urban_growth.io import SourceSchemaError, require_columns


DERIVED_POINT_IN_TIME_COLUMNS = {
    "point_in_time_available": "point_in_time_available",
    "availability_provenance_verified": "availability_provenance_verified",
    "forecast_origin_registration_verified": "forecast_origin_registration_verified",
}


def recompute_point_in_time_evidence(
    panel: pd.DataFrame,
    *,
    origin_column: str = "forecast_origin_date",
    predictor_available_column: str = "predictor_available_date",
    concordance_available_column: str = "concordance_available_date",
    predictor_provenance_column: str = "predictor_availability_source",
    concordance_provenance_column: str = "concordance_availability_source",
    origin_registration_column: str = "forecast_origin_registration",
    availability_column: str = "point_in_time_available",
    provenance_verified_column: str = "availability_provenance_verified",
    origin_registration_verified_column: str = "forecast_origin_registration_verified",
) -> pd.DataFrame:
    """Recompute deployability flags and reject caller-supplied flag disagreement."""
    require_columns(
        panel,
        {
            origin_column,
            predictor_available_column,
            concordance_available_column,
            predictor_provenance_column,
            concordance_provenance_column,
            origin_registration_column,
        },
        source_name="verified point-in-time forecast panel",
    )

    supplied = panel.copy()
    recomputed = apply_forecast_availability_gate(
        supplied,
        origin_column=origin_column,
        predictor_available_column=predictor_available_column,
        concordance_available_column=concordance_available_column,
        predictor_provenance_column=predictor_provenance_column,
        concordance_provenance_column=concordance_provenance_column,
        origin_registration_column=origin_registration_column,
    )

    comparisons = {
        availability_column: "point_in_time_available",
        provenance_verified_column: "availability_provenance_verified",
        origin_registration_verified_column: "forecast_origin_registration_verified",
    }
    for supplied_column, derived_column in comparisons.items():
        if supplied_column not in supplied.columns:
            raise SourceSchemaError(
                f"{supplied_column} must be present so recomputed point-in-time evidence can be reconciled"
            )
        if not pd.api.types.is_bool_dtype(supplied[supplied_column].dtype):
            raise SourceSchemaError(f"{supplied_column} must be boolean")
        expected = recomputed[derived_column]
        actual = supplied[supplied_column]
        if not actual.equals(expected):
            raise SourceSchemaError(
                f"{supplied_column} disagrees with the value recomputed from raw availability evidence"
            )

    recomputed["point_in_time_evidence_recomputed"] = True
    recomputed["derived_point_in_time_flags_reconciled"] = True
    return recomputed


def evaluate_verified_point_in_time_persistence_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    **kwargs: object,
) -> pd.DataFrame:
    """Evaluate persistence only after recomputing own-origin deployability evidence."""
    from urban_growth.forecast_fitness import evaluate_point_in_time_persistence_baselines

    verified = recompute_point_in_time_evidence(panel)
    result = evaluate_point_in_time_persistence_baselines(verified, origins, **kwargs)
    result["point_in_time_evidence_recomputed"] = True
    result["derived_point_in_time_flags_reconciled"] = True
    return result


def verified_point_in_time_persistence_errors(
    panel: pd.DataFrame,
    origins: list[int],
    **kwargs: object,
) -> pd.DataFrame:
    """Return row-level errors only after recomputing own-origin deployability evidence."""
    from urban_growth.forecast_fitness import point_in_time_persistence_errors

    verified = recompute_point_in_time_evidence(panel)
    result = point_in_time_persistence_errors(verified, origins, **kwargs)
    result["point_in_time_evidence_recomputed"] = True
    result["derived_point_in_time_flags_reconciled"] = True
    return result

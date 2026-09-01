"""Empirical-lineage classification for WUP 2025 DEGURBA city population series."""
# ruff: noqa: I001

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns


WUP_REFERENCE_ESTIMATE_START = 1975
WUP_REFERENCE_ESTIMATE_END = 2020
WUP_CRISP_PROJECTION_START = 2021


def classify_wup_city_population_lineage(panel: pd.DataFrame) -> pd.DataFrame:
    """Separate publisher estimate labels from empirical outcome lineage.

    WUP 2025 describes the published 1950-2025 population series as estimates,
    but its DEGURBA methodology uses reference estimates from GHS-WUP-POP for
    1975-2020 and CRISP-generated values after 2020. Forecast evaluation therefore
    must not treat post-2020 city endpoints as observed/reference estimates merely
    because they fall inside the publisher's estimate period.
    """
    require_columns(
        panel,
        {"year", "observation_type"},
        source_name="WUP city population lineage",
    )
    out = panel.copy()
    year = pd.to_numeric(out["year"], errors="coerce")
    if year.isna().any():
        raise SourceSchemaError("WUP city population lineage requires numeric years")

    out["publisher_observation_type"] = out["observation_type"].astype("string")
    out["empirical_lineage_type"] = "unclassified"
    out.loc[year.lt(WUP_REFERENCE_ESTIMATE_START), "empirical_lineage_type"] = (
        "historical_backcast"
    )
    out.loc[
        year.between(WUP_REFERENCE_ESTIMATE_START, WUP_REFERENCE_ESTIMATE_END),
        "empirical_lineage_type",
    ] = "reference_estimate"
    out.loc[year.ge(WUP_CRISP_PROJECTION_START), "empirical_lineage_type"] = (
        "crisp_projection"
    )
    if out["empirical_lineage_type"].eq("unclassified").any():
        years = sorted(
            out.loc[out["empirical_lineage_type"].eq("unclassified"), "year"].unique()
        )
        raise SourceSchemaError(f"Unclassified WUP empirical-lineage years: {years}")

    out["observation_type"] = out["empirical_lineage_type"].map(
        {
            "historical_backcast": "estimate",
            "reference_estimate": "estimate",
            "crisp_projection": "projection",
        }
    )
    out["empirical_outcome_reference_estimate"] = out["empirical_lineage_type"].eq(
        "reference_estimate"
    )
    out["wup_lineage_methodology_reference"] = (
        "WUP2025 methodology: 1975-2020 GHS-WUP-POP reference estimates; "
        "post-2020 CRISP-generated values"
    )
    return out

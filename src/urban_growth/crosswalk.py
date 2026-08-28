"""Explicit crosswalk controls for source-specific urban identifier namespaces."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

CROSSWALK_COLUMNS = {
    "wup_city_id",
    "ghsl_city_id",
    "match_status",
    "match_method",
    "evidence",
}
MATCH_STATUSES = {"accepted", "review", "rejected"}


def validate_wup_ghsl_crosswalk(crosswalk: pd.DataFrame) -> None:
    """Validate an evidence-bearing WUP-to-GHSL crosswalk.

    WUP and GHSL identifiers are unrelated numeric namespaces. A WUP record may
    map to at most one accepted GHSL centre. Multiple WUP records may fall inside
    one GHSL centre, but callers must handle that aggregation explicitly.
    """
    require_columns(crosswalk, CROSSWALK_COLUMNS, source_name="WUP-GHSL crosswalk")
    invalid_statuses = sorted(set(crosswalk["match_status"].dropna()) - MATCH_STATUSES)
    if invalid_statuses:
        raise SourceSchemaError(f"WUP-GHSL crosswalk has invalid statuses: {invalid_statuses}")
    accepted = crosswalk.loc[crosswalk["match_status"].eq("accepted")]
    if accepted[["wup_city_id", "ghsl_city_id", "match_method", "evidence"]].isna().any().any():
        raise SourceSchemaError("Accepted WUP-GHSL matches require IDs, method, and evidence")
    if accepted.duplicated(["wup_city_id"]).any():
        raise SourceSchemaError("A WUP city has multiple accepted GHSL matches")


def accepted_crosswalk(crosswalk: pd.DataFrame, *, allow_many_to_one: bool = False) -> pd.DataFrame:
    """Return accepted mappings, requiring explicit consent for many-to-one units."""
    validate_wup_ghsl_crosswalk(crosswalk)
    accepted = crosswalk.loc[crosswalk["match_status"].eq("accepted")].copy()
    counts = accepted.groupby("ghsl_city_id")["wup_city_id"].transform("size")
    accepted["wup_units_per_ghsl"] = counts.astype(int)
    if not allow_many_to_one and accepted["wup_units_per_ghsl"].gt(1).any():
        raise SourceSchemaError(
            "Crosswalk contains multiple WUP cities per GHSL centre; choose an aggregation rule"
        )
    return accepted.reset_index(drop=True)

"""GHS-UCDB normalization helpers with explicit boundary semantics."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, reject_duplicate_keys

BOUNDARY_MODES = {"dynamic", "fixed"}


def indicator_panel(
    frame: pd.DataFrame,
    *,
    city_id_column: str,
    indicator_pattern: str,
    value_name: str,
    boundary_mode: str,
    metadata_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Convert a declared UCDB indicator family to a city-year panel."""
    if boundary_mode not in BOUNDARY_MODES:
        raise SourceSchemaError("boundary_mode must be 'dynamic' or 'fixed'")
    ids = [city_id_column, *(metadata_columns or [])]
    panel = wide_years_to_long(
        frame, id_columns=ids, value_pattern=indicator_pattern, value_name=value_name
    )
    panel = panel.rename(columns={city_id_column: "city_id"})
    panel["boundary_mode"] = boundary_mode
    reject_duplicate_keys(panel, ["city_id", "year", "boundary_mode"], source_name="UCDB")
    return panel

"""GHS-UCDB normalization helpers with explicit boundary semantics."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, reject_duplicate_keys

BOUNDARY_PRODUCTS = {
    "ucdb_multitemporal_footprints": "dynamic",
    "zonal_stats_fixed_2020_footprint": "fixed",
}


def indicator_panel(
    frame: pd.DataFrame,
    *,
    city_id_column: str,
    indicator_pattern: str,
    value_name: str,
    boundary_product: str,
    metadata_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Convert a declared UCDB indicator family to a city-year panel."""
    if boundary_product not in BOUNDARY_PRODUCTS:
        allowed = ", ".join(sorted(BOUNDARY_PRODUCTS))
        raise SourceSchemaError(f"Unregistered boundary_product; expected one of: {allowed}")
    boundary_mode = BOUNDARY_PRODUCTS[boundary_product]
    ids = [city_id_column, *(metadata_columns or [])]
    panel = wide_years_to_long(
        frame, id_columns=ids, value_pattern=indicator_pattern, value_name=value_name
    )
    panel = panel.rename(columns={city_id_column: "city_id"})
    panel["boundary_mode"] = boundary_mode
    panel["boundary_product"] = boundary_product
    reject_duplicate_keys(panel, ["city_id", "year", "boundary_product"], source_name="UCDB")
    return panel

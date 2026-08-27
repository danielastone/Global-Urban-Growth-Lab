"""GHS-UCDB normalization helpers with explicit boundary semantics."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, read_table, reject_duplicate_keys, require_columns

BOUNDARY_PRODUCTS = {
    "ucdb_multitemporal_boundaries": "dynamic",
    "ucdb_fixed_2025_boundary": "fixed",
}

GHSL_THEME_METADATA = ["GC_UCN_MAI_2025", "GC_CNT_GAD_2025"]


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


def read_ghsl_theme_csv(path: str) -> pd.DataFrame:
    """Read the official R2024A v1.2 thematic CSV using its actual encoding."""
    return read_table(path, encoding="cp1252", low_memory=False)


def fixed_2025_theme_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize GHSL population and built-up area inside fixed 2025 boundaries.

    The thematic package is a fixed-entity history. It must not be interpreted as
    the separate multi-temporal-boundary product.
    """
    required = {"ID_UC_G0", *GHSL_THEME_METADATA}
    require_columns(frame, required, source_name="GHS-UCDB theme R2024A v1.2")
    population = indicator_panel(
        frame,
        city_id_column="ID_UC_G0",
        metadata_columns=GHSL_THEME_METADATA,
        indicator_pattern=r"GH_POP_TOT_(?P<year>\d{4})",
        value_name="population",
        boundary_product="ucdb_fixed_2025_boundary",
    )
    built_up = indicator_panel(
        frame,
        city_id_column="ID_UC_G0",
        metadata_columns=GHSL_THEME_METADATA,
        indicator_pattern=r"GH_BUS_TOT_(?P<year>\d{4})",
        value_name="built_up_area_m2",
        boundary_product="ucdb_fixed_2025_boundary",
    )
    keys = [
        "city_id",
        *GHSL_THEME_METADATA,
        "year",
        "boundary_mode",
        "boundary_product",
    ]
    panel = population.merge(built_up, on=keys, validate="one_to_one")
    for column in ["population", "built_up_area_m2"]:
        raw = panel[column]
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid = raw.notna() & numeric.isna()
        if invalid.any():
            examples = ", ".join(sorted(raw[invalid].astype(str).unique())[:3])
            raise SourceSchemaError(f"GHS-UCDB has non-numeric {column}: {examples}")
        panel[column] = numeric
    if panel[["population", "built_up_area_m2"]].isna().any().any():
        raise SourceSchemaError("GHS-UCDB fixed theme has missing population or built-up area")
    if (panel["population"] <= 0).any() or (panel["built_up_area_m2"] <= 0).any():
        raise SourceSchemaError("GHS-UCDB fixed theme requires positive values")
    reject_duplicate_keys(
        panel, ["city_id", "year", "boundary_product"], source_name="GHS-UCDB theme"
    )
    return panel.sort_values(["city_id", "year"]).reset_index(drop=True)

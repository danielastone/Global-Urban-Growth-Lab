"""WUP 2025 normalization helpers for cities/towns/rural categories."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

DEGURBA_CATEGORIES = {"city", "town_and_semi_dense", "rural"}


def degree_of_urbanization_panel(
    frame: pd.DataFrame,
    *,
    location_id_column: str,
    category_column: str,
    year_pattern: str = r"(?P<year>\d{4})",
    population_unit: str = "thousands",
    metadata_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Normalize a WUP category table after the caller maps publisher labels."""
    require_columns(frame, {location_id_column, category_column}, source_name="WUP")
    ids = [location_id_column, category_column, *(metadata_columns or [])]
    panel = wide_years_to_long(
        frame, id_columns=ids, value_pattern=year_pattern, value_name="population"
    ).rename(columns={location_id_column: "location_id", category_column: "category"})
    unknown = sorted(set(panel["category"].dropna()) - DEGURBA_CATEGORIES)
    if unknown:
        raise SourceSchemaError(f"Unmapped DEGURBA categories: {', '.join(map(str, unknown))}")
    if population_unit == "thousands":
        panel["population"] = panel["population"] * 1000
    elif population_unit != "persons":
        raise SourceSchemaError("population_unit must be 'thousands' or 'persons'")
    if (panel["population"].dropna() < 0).any():
        raise SourceSchemaError("WUP population cannot be negative")
    reject_duplicate_keys(panel, ["location_id", "category", "year"], source_name="WUP")
    return panel

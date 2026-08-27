"""WUP 2025 normalization helpers for cities/towns/rural categories."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

DEGURBA_CATEGORIES = {"city", "town_and_semi_dense", "rural"}


def _scale_population(panel: pd.DataFrame, population_unit: str) -> pd.DataFrame:
    if population_unit == "thousands":
        panel["population"] = panel["population"] * 1000
    elif population_unit != "persons":
        raise SourceSchemaError("population_unit must be 'thousands' or 'persons'")
    if panel["population"].isna().any() or (panel["population"] < 0).any():
        raise SourceSchemaError("WUP population must be present and nonnegative")
    return panel


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
    panel = _scale_population(panel, population_unit)
    reject_duplicate_keys(panel, ["location_id", "category", "year"], source_name="WUP")
    return panel


def city_population_panel(
    frame: pd.DataFrame,
    *,
    city_id_column: str,
    year_pattern: str = r"(?P<year>\d{4})",
    population_unit: str = "thousands",
    metadata_columns: list[str] | None = None,
    estimate_end_year: int = 2025,
    inclusion_reference_year: int = 2025,
    inclusion_threshold: int = 50_000,
) -> pd.DataFrame:
    """Normalize the WUP individual-city series without truncating its history."""
    ids = [city_id_column, *(metadata_columns or [])]
    panel = wide_years_to_long(
        frame, id_columns=ids, value_pattern=year_pattern, value_name="population"
    ).rename(columns={city_id_column: "city_id"})
    panel = _scale_population(panel, population_unit)
    panel["observation_type"] = panel["year"].le(estimate_end_year).map(
        {True: "estimate", False: "projection"}
    )
    reference = panel.loc[panel["year"] == inclusion_reference_year, ["city_id", "population"]]
    if reference.empty:
        raise SourceSchemaError(f"Missing inclusion reference year {inclusion_reference_year}")
    reject_duplicate_keys(reference, ["city_id"], source_name="WUP reference year")
    eligible = reference.set_index("city_id")["population"].ge(inclusion_threshold)
    panel["eligible_at_reference_year"] = panel["city_id"].map(eligible)
    if panel["eligible_at_reference_year"].isna().any():
        raise SourceSchemaError("A city is missing from the inclusion reference year")
    reject_duplicate_keys(panel, ["city_id", "year"], source_name="WUP cities")
    return panel

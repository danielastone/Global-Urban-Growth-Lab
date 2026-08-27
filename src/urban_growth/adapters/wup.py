"""WUP 2025 normalization helpers for cities/towns/rural categories."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

DEGURBA_CATEGORIES = {"city", "town_and_semi_dense", "rural"}


def _scale_population(
    panel: pd.DataFrame, population_unit: str, *, allow_missing: bool = False
) -> pd.DataFrame:
    if population_unit == "thousands":
        panel["population"] = panel["population"] * 1000
    elif population_unit != "persons":
        raise SourceSchemaError("population_unit must be 'thousands' or 'persons'")
    if not allow_missing and panel["population"].isna().any():
        raise SourceSchemaError("WUP population must be present")
    if (panel["population"].dropna() < 0).any():
        raise SourceSchemaError("WUP population cannot be negative")
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
    panel = _scale_population(panel, population_unit, allow_missing=True)
    panel["observation_type"] = panel["year"].le(estimate_end_year).map(
        {True: "estimate", False: "projection"}
    )
    reference_rows = panel.loc[
        panel["year"] == inclusion_reference_year, ["city_id", "population"]
    ]
    if reference_rows.empty:
        raise SourceSchemaError(f"Missing inclusion reference year {inclusion_reference_year}")
    reject_duplicate_keys(reference_rows, ["city_id"], source_name="WUP reference year")
    eligible = reference_rows.set_index("city_id")["population"].ge(inclusion_threshold)
    panel["eligible_at_reference_year"] = panel["city_id"].map(eligible).fillna(False)

    observed = panel.loc[panel["population"].notna(), ["city_id", "year", "population"]]
    if observed.empty:
        raise SourceSchemaError("WUP city table contains no observed population values")
    spans = observed.groupby("city_id", sort=False)["year"].agg(
        sample_entry_year="min", sample_exit_year="max"
    )
    panel = panel.loc[panel["population"].notna()].copy()
    panel = panel.join(spans, on="city_id")
    panel["threshold_observed"] = panel["population"].ge(inclusion_threshold)
    if not panel["threshold_observed"].all():
        raise SourceSchemaError(
            "A populated WUP F21 cell is below the declared reporting threshold"
        )
    reject_duplicate_keys(panel, ["city_id", "year"], source_name="WUP cities")
    return panel


def read_f21_city_population(path: str) -> pd.DataFrame:
    """Read and normalize the verified WUP 2025 F21 workbook schema."""
    from urban_growth.io import read_table, require_columns

    frame = read_table(path, sheet_name="Data")
    required = {
        "LocID", "ISO3_Code", "City_Code", "City_Name",
        "PWCent_Longitude", "PWCent_Latitude", "1975", "2025", "2050",
    }
    require_columns(frame, required, source_name="WUP 2025 F21")
    return city_population_panel(
        frame,
        city_id_column="City_Code",
        metadata_columns=[
            "LocID", "ISO3_Code", "City_Name", "PWCent_Longitude", "PWCent_Latitude"
        ],
    )


def city_area_panel(
    frame: pd.DataFrame,
    *,
    city_id_column: str,
    year_pattern: str = r"(?P<year>\d{4})",
    metadata_columns: list[str] | None = None,
    estimate_end_year: int = 2025,
) -> pd.DataFrame:
    """Normalize a threshold-truncated WUP city-area table."""
    ids = [city_id_column, *(metadata_columns or [])]
    panel = wide_years_to_long(
        frame, id_columns=ids, value_pattern=year_pattern, value_name="land_area_km2"
    ).rename(columns={city_id_column: "city_id"})
    panel["land_area_km2"] = pd.to_numeric(panel["land_area_km2"], errors="coerce")
    panel = panel.loc[panel["land_area_km2"].notna()].copy()
    if panel.empty or (panel["land_area_km2"] <= 0).any():
        raise SourceSchemaError("WUP land area must be positive when reported")
    panel["observation_type"] = panel["year"].le(estimate_end_year).map(
        {True: "estimate", False: "projection"}
    )
    spans = panel.groupby("city_id", sort=False)["year"].agg(
        sample_entry_year="min", sample_exit_year="max"
    )
    panel = panel.join(spans, on="city_id")
    reject_duplicate_keys(panel, ["city_id", "year"], source_name="WUP city land area")
    return panel


def read_f25_city_land_area(path: str) -> pd.DataFrame:
    """Read and normalize the verified WUP 2025 F25 workbook schema."""
    from urban_growth.io import read_table, require_columns

    frame = read_table(path, sheet_name="Data")
    required = {
        "LocID", "ISO3_Code", "City_Code", "City_Name",
        "PWCent_Longitude", "PWCent_Latitude", "1975", "2025", "2050",
    }
    require_columns(frame, required, source_name="WUP 2025 F25")
    return city_area_panel(
        frame,
        city_id_column="City_Code",
        metadata_columns=[
            "LocID", "ISO3_Code", "City_Name", "PWCent_Longitude", "PWCent_Latitude"
        ],
    )

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


def city_metric_panel(
    frame: pd.DataFrame,
    *,
    city_id_column: str,
    value_name: str,
    allow_zero: bool,
    year_pattern: str = r"(?P<year>\d{4})",
    metadata_columns: list[str] | None = None,
    estimate_end_year: int = 2025,
) -> pd.DataFrame:
    """Normalize a threshold-truncated WUP city metric with declared zero semantics."""
    ids = [city_id_column, *(metadata_columns or [])]
    panel = wide_years_to_long(
        frame, id_columns=ids, value_pattern=year_pattern, value_name=value_name
    ).rename(columns={city_id_column: "city_id"})
    raw = panel[value_name]
    numeric = pd.to_numeric(raw, errors="coerce")
    invalid = raw.notna() & numeric.isna()
    if invalid.any():
        raise SourceSchemaError(f"WUP {value_name} contains non-numeric reported values")
    panel[value_name] = numeric
    panel = panel.loc[panel[value_name].notna()].copy()
    if panel.empty:
        raise SourceSchemaError(f"WUP {value_name} contains no reported values")
    invalid_range = panel[value_name].lt(0) if allow_zero else panel[value_name].le(0)
    if invalid_range.any():
        qualifier = "nonnegative" if allow_zero else "positive"
        raise SourceSchemaError(f"WUP {value_name} must be {qualifier} when reported")
    panel["reported_zero"] = panel[value_name].eq(0)
    panel["observation_type"] = panel["year"].le(estimate_end_year).map(
        {True: "estimate", False: "projection"}
    )
    reject_duplicate_keys(panel, ["city_id", "year"], source_name=f"WUP {value_name}")
    return panel


def _read_verified_city_metric(path: str, *, table: str, value_name: str, allow_zero: bool) -> pd.DataFrame:
    from urban_growth.io import read_table, require_columns

    frame = read_table(path, sheet_name="Data")
    required = {
        "LocID", "ISO3_Code", "City_Code", "City_Name",
        "PWCent_Longitude", "PWCent_Latitude", "1975", "2025", "2050",
    }
    require_columns(frame, required, source_name=f"WUP 2025 {table}")
    return city_metric_panel(
        frame,
        city_id_column="City_Code",
        value_name=value_name,
        allow_zero=allow_zero,
        metadata_columns=[
            "LocID", "ISO3_Code", "City_Name", "PWCent_Longitude", "PWCent_Latitude"
        ],
    )


def read_f30_built_up_area_per_capita(path: str) -> pd.DataFrame:
    """Read verified F30 built-up area per capita in square metres per person."""
    return _read_verified_city_metric(
        path, table="F30", value_name="built_up_area_m2_per_capita", allow_zero=True
    )


def read_f34_population_density(path: str) -> pd.DataFrame:
    """Read verified F34 population density in persons per square kilometre."""
    return _read_verified_city_metric(
        path, table="F34", value_name="population_density_per_km2", allow_zero=False
    )


def validate_density_identity(
    population_panel: pd.DataFrame,
    area_panel: pd.DataFrame,
    density_panel: pd.DataFrame,
    *,
    density_rounding_tolerance: float = 0.005001,
    population_rounding_tolerance: float = 0.500001,
) -> pd.DataFrame:
    """Verify F34 equals F21 persons divided by F25 square kilometres."""
    left = population_panel[["city_id", "year", "population"]]
    middle = area_panel[["city_id", "year", "land_area_km2"]]
    right = density_panel[["city_id", "year", "population_density_per_km2"]]
    audit = left.merge(middle, on=["city_id", "year"], validate="one_to_one").merge(
        right, on=["city_id", "year"], validate="one_to_one"
    )
    if len(audit) != len(left) or len(audit) != len(middle) or len(audit) != len(right):
        raise SourceSchemaError("WUP F21/F25/F34 city-year coverage differs")
    audit["calculated_density_per_km2"] = audit["population"] / audit["land_area_km2"]
    audit["density_difference"] = (
        audit["calculated_density_per_km2"] - audit["population_density_per_km2"]
    )
    audit["allowed_rounding_difference"] = (
        density_rounding_tolerance + population_rounding_tolerance / audit["land_area_km2"]
    )
    if audit["density_difference"].abs().gt(audit["allowed_rounding_difference"]).any():
        raise SourceSchemaError("WUP F34 density disagrees with F21/F25 beyond rounding")
    return audit

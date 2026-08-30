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


def read_f22_2018_city_population(path: str) -> pd.DataFrame:
    """Read the WUP 2018 annual urban-agglomeration vintage."""
    from urban_growth.io import read_table, require_columns

    frame = read_table(path, sheet_name="Data", header=16)
    required = {
        "Country Code", "Country or area", "City Code", "Urban Agglomeration",
        "Latitude", "Longitude",
        1950, 2018, 2035,
    }
    require_columns(frame, required, source_name="WUP 2018 F22")
    panel = wide_years_to_long(
        frame,
        id_columns=[
            "City Code", "Country Code", "Country or area", "Urban Agglomeration",
            "Latitude", "Longitude"
        ],
        value_pattern=r"(?P<year>\d{4})",
        value_name="population",
    ).rename(
        columns={
            "City Code": "city_id",
            "Country Code": "country_location_id",
            "Country or area": "country_name",
            "Urban Agglomeration": "city_name",
            "Latitude": "latitude",
            "Longitude": "longitude",
        }
    )
    panel = _scale_population(panel, "thousands")
    panel["observation_type"] = panel["year"].le(2018).map(
        {True: "estimate", False: "projection"}
    )
    reference = panel.loc[panel["year"].eq(2018), "population"]
    if len(reference) != frame["City Code"].nunique() or reference.lt(300_000).any():
        raise SourceSchemaError("WUP 2018 F22 violates its 300,000-in-2018 universe")
    reject_duplicate_keys(panel, ["city_id", "year"], source_name="WUP 2018 F22")
    panel["revision"] = "WUP_2018_vintage"
    panel["urban_definition"] = "national_urban_agglomeration_over_300k_in_2018"
    return panel


def read_f01_country_city_population(path: str) -> pd.DataFrame:
    """Read national populations in WUP's harmonized Cities category.

    The returned history is from the 2025 revision. It can support a
    revised-history national comparator, but must not be represented as a
    vintage-real-time forecast.
    """
    from urban_growth.io import read_table, require_columns

    frame = read_table(path, sheet_name="Cities")
    required = {
        "LocID", "ISO3_Code", "Location", "LocType", "LocTypeName",
        "ParentID", "1950", "2025", "2050",
    }
    require_columns(frame, required, source_name="WUP 2025 F01 Cities")
    countries = frame.loc[frame["LocType"].eq(4)].copy()
    if countries.empty or countries["LocTypeName"].ne("Country/Area").any():
        raise SourceSchemaError("WUP F01 has no valid Country/Area rows")
    locations = frame.set_index("LocID", drop=False)
    hierarchy_rows: list[dict[str, int | str]] = []
    for row in countries.itertuples(index=False):
        parent_id = int(row.ParentID)
        if parent_id == 918:
            # F01 points the five Northern American Country/Area rows to 918,
            # but omits that subregion row. The corresponding region row is 905.
            subregion_name = "Northern America"
            region_id = 905
        else:
            if parent_id not in locations.index:
                raise SourceSchemaError(f"WUP F01 lacks parent {parent_id}")
            subregion = locations.loc[parent_id]
            if subregion["LocType"] != 3 or subregion["LocTypeName"] != "Subregion":
                raise SourceSchemaError("WUP F01 Country/Area parent is not a subregion")
            subregion_name = str(subregion["Location"])
            region_id = int(subregion["ParentID"])
        if region_id not in locations.index:
            raise SourceSchemaError(f"WUP F01 lacks region {region_id}")
        region = locations.loc[region_id]
        if region["LocType"] != 2 or region["LocTypeName"] != "Geographic region":
            raise SourceSchemaError("WUP F01 subregion parent is not a geographic region")
        hierarchy_rows.append(
            {
                "subregion_id": parent_id,
                "subregion_name": subregion_name,
                "region_id": region_id,
                "region_name": str(region["Location"]),
            }
        )
    hierarchy = pd.DataFrame(hierarchy_rows, index=countries.index)
    countries = countries.join(hierarchy)
    if countries[["subregion_id", "region_id"]].isna().any().any():
        raise SourceSchemaError("WUP F01 country hierarchy is incomplete")
    countries["category"] = "city"
    panel = degree_of_urbanization_panel(
        countries,
        location_id_column="LocID",
        category_column="category",
        metadata_columns=[
            "ISO3_Code", "Location", "ParentID", "subregion_id", "subregion_name",
            "region_id", "region_name",
        ],
    ).rename(
        columns={
            "ISO3_Code": "country_code",
            "Location": "country_name",
            "population": "national_city_category_population",
        }
    )
    if panel["country_code"].isna().any():
        raise SourceSchemaError("WUP F01 Country/Area row lacks ISO3 code")
    reject_duplicate_keys(
        panel, ["country_code", "year"], source_name="WUP F01 national Cities"
    )
    panel["observation_type"] = panel["year"].le(2025).map(
        {True: "estimate", False: "projection"}
    )
    panel["revision_semantics"] = "WUP_2025_revised_history"
    return panel.sort_values(["country_code", "year"]).reset_index(drop=True)


def read_f01_country_degurb_population(path: str) -> pd.DataFrame:
    """Read reconciled country Cities, Towns, and Rural populations from WUP F01."""
    from urban_growth.io import read_table, require_columns

    city = read_f01_country_city_population(path)
    hierarchy_columns = [
        "location_id", "country_code", "country_name", "ParentID", "subregion_id",
        "subregion_name", "region_id", "region_name", "year", "observation_type",
        "revision_semantics",
    ]
    hierarchy = city[hierarchy_columns].copy()
    category_frames = [
        city.rename(columns={"national_city_category_population": "population"}).assign(
            category="city"
        )
    ]
    required = {
        "LocID", "ISO3_Code", "Location", "LocType", "LocTypeName",
        "ParentID", "1950", "2025", "2050",
    }
    for sheet_name, category in (("Towns", "town_and_semi_dense"), ("Rural", "rural")):
        frame = read_table(path, sheet_name=sheet_name)
        require_columns(frame, required, source_name=f"WUP 2025 F01 {sheet_name}")
        countries = frame.loc[frame["LocType"].eq(4)].copy()
        if countries.empty or countries["LocTypeName"].ne("Country/Area").any():
            raise SourceSchemaError(f"WUP F01 {sheet_name} has no valid Country/Area rows")
        countries["category"] = category
        panel = degree_of_urbanization_panel(
            countries,
            location_id_column="LocID",
            category_column="category",
            metadata_columns=["ISO3_Code", "Location"],
        ).rename(
            columns={"ISO3_Code": "country_code", "Location": "country_name"}
        )
        panel["observation_type"] = panel["year"].le(2025).map(
            {True: "estimate", False: "projection"}
        )
        panel["revision_semantics"] = "WUP_2025_revised_history"
        category_frames.append(
            panel.merge(
                hierarchy.drop(columns=["country_name", "observation_type", "revision_semantics"]),
                on=["location_id", "country_code", "year"],
                how="left",
                validate="one_to_one",
            )
        )
    result = pd.concat(category_frames, ignore_index=True)
    result = result[
        [
            "location_id", "country_code", "country_name", "ParentID", "subregion_id",
            "subregion_name", "region_id", "region_name", "year", "category", "population",
            "observation_type", "revision_semantics",
        ]
    ]
    if result[["country_code", "subregion_id", "region_id"]].isna().any().any():
        raise SourceSchemaError("WUP F01 category sheets do not match the Cities hierarchy")
    reject_duplicate_keys(
        result, ["country_code", "year", "category"], source_name="WUP F01 DEGURBA"
    )

    total_frame = read_table(path, sheet_name="Total")
    require_columns(total_frame, required, source_name="WUP 2025 F01 Total")
    total_countries = total_frame.loc[total_frame["LocType"].eq(4)].copy()
    total = wide_years_to_long(
        total_countries,
        id_columns=["LocID", "ISO3_Code"],
        value_pattern=r"(?P<year>\d{4})",
        value_name="reported_total",
    ).rename(columns={"LocID": "location_id", "ISO3_Code": "country_code"})
    total = _scale_population(total.rename(columns={"reported_total": "population"}), "thousands")
    total = total.rename(columns={"population": "reported_total"})
    computed = result.groupby(["location_id", "country_code", "year"], as_index=False)[
        "population"
    ].sum().rename(columns={"population": "computed_total"})
    reconciliation = computed.merge(
        total, on=["location_id", "country_code", "year"], validate="one_to_one"
    )
    difference = (reconciliation["computed_total"] - reconciliation["reported_total"]).abs()
    if difference.gt(3).any():
        raise SourceSchemaError("WUP F01 category populations do not reconcile to Total")
    return result.sort_values(["country_code", "year", "category"]).reset_index(drop=True)


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

"""GHS-UCDB normalization helpers with explicit boundary semantics."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wide import wide_years_to_long
from urban_growth.io import SourceSchemaError, read_table, reject_duplicate_keys, require_columns

BOUNDARY_PRODUCTS = {
    "ucdb_multitemporal_boundaries": "dynamic",
    "ucdb_fixed_2025_boundary": "fixed",
}

GHSL_THEME_METADATA = ["GC_UCN_MAI_2025", "GC_CNT_GAD_2025", "GC_UCA_KM2_2025"]
GHSL_MTUC_METADATA = [
    "GC_UCN_MAI_2025",
    "GC_CNT_GAD_2025",
    "GC_UCB_YOB _2025",
    "GC_UCB_YOD _2025",
]


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


def read_ghsl_mtuc_csv(path: str) -> pd.DataFrame:
    """Read the official R2024A v1.2 multi-temporal-boundary CSV."""
    return read_table(path, encoding="cp1252", low_memory=False)


def _publisher_numeric(series: pd.Series, *, column: str) -> pd.Series:
    """Parse GHSL display-formatted numbers while preserving declared '-' missing values."""
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", "", regex=False)
        .replace("-", pd.NA)
    )
    numeric = pd.to_numeric(cleaned, errors="coerce")
    invalid = series.notna() & cleaned.notna() & numeric.isna()
    if invalid.any():
        examples = ", ".join(sorted(series[invalid].astype(str).unique())[:3])
        raise SourceSchemaError(f"GHS-UCDB has non-numeric {column}: {examples}")
    return numeric


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
    panel = panel.rename(columns={"GC_UCA_KM2_2025": "urban_centre_area_km2"})
    for column in ["population", "built_up_area_m2", "urban_centre_area_km2"]:
        raw = panel[column]
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid = raw.notna() & numeric.isna()
        if invalid.any():
            examples = ", ".join(sorted(raw[invalid].astype(str).unique())[:3])
            raise SourceSchemaError(f"GHS-UCDB has non-numeric {column}: {examples}")
        panel[column] = numeric
    if panel[["population", "built_up_area_m2", "urban_centre_area_km2"]].isna().any().any():
        raise SourceSchemaError("GHS-UCDB fixed theme has missing core measures")
    if (panel[["population", "built_up_area_m2", "urban_centre_area_km2"]] <= 0).any().any():
        raise SourceSchemaError("GHS-UCDB fixed theme requires positive values")
    reject_duplicate_keys(
        panel, ["city_id", "year", "boundary_product"], source_name="GHS-UCDB theme"
    )
    return panel.sort_values(["city_id", "year"]).reset_index(drop=True)


def reconcile_2025_streams(
    fixed_panel: pd.DataFrame,
    dynamic_panel: pd.DataFrame,
    *,
    population_tolerance: float = 0.500001,
) -> pd.DataFrame:
    """Audit the publisher's stated fixed/dynamic comparability at the 2025 epoch."""
    fixed = fixed_panel.loc[fixed_panel["year"].eq(2025)].copy()
    dynamic = dynamic_panel.loc[
        dynamic_panel["year"].eq(2025) & dynamic_panel["quality_controlled_2025"]
    ].copy()
    measures = ["population", "built_up_area_m2", "urban_centre_area_km2"]
    required = {"city_id", "year", "GC_CNT_GAD_2025", *measures}
    require_columns(fixed, required, source_name="GHS-UCDB fixed 2025 panel")
    require_columns(dynamic, required, source_name="GHS-UCDB dynamic 2025 panel")
    audit = fixed.merge(
        dynamic,
        on="city_id",
        how="outer",
        suffixes=("_fixed", "_dynamic"),
        validate="one_to_one",
        indicator=True,
    )
    if audit["_merge"].ne("both").any():
        raise SourceSchemaError("GHS-UCDB quality-controlled 2025 identifier sets disagree")
    if audit["GC_CNT_GAD_2025_fixed"].ne(audit["GC_CNT_GAD_2025_dynamic"]).any():
        raise SourceSchemaError("GHS-UCDB 2025 country assignments disagree")
    audit["population_difference"] = audit["population_fixed"] - audit["population_dynamic"]
    audit["built_up_area_difference_m2"] = (
        audit["built_up_area_m2_fixed"] - audit["built_up_area_m2_dynamic"]
    )
    audit["urban_centre_area_difference_km2"] = (
        audit["urban_centre_area_km2_fixed"] - audit["urban_centre_area_km2_dynamic"]
    )
    if audit["population_difference"].abs().gt(population_tolerance).any():
        raise SourceSchemaError("GHS-UCDB 2025 population differs beyond rounding tolerance")
    if audit["built_up_area_difference_m2"].ne(0).any():
        raise SourceSchemaError("GHS-UCDB 2025 built-up area differs between streams")
    if audit["urban_centre_area_difference_km2"].ne(0).any():
        raise SourceSchemaError("GHS-UCDB 2025 centre area differs between streams")
    return audit[
        [
            "city_id",
            "population_difference",
            "built_up_area_difference_m2",
            "urban_centre_area_difference_km2",
        ]
    ].sort_values("city_id").reset_index(drop=True)


def multitemporal_boundary_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize MTUC values only during each centre's declared active lifespan."""
    require_columns(
        frame,
        {"ID_MTUC_G0", *GHSL_MTUC_METADATA},
        source_name="GHS-UCDB MTUC R2024A v1.2",
    )
    families = [
        (r"MT_POP_TOT_(?P<year>\d{4})", "population"),
        (r"MT_BUS_TOT_(?P<year>\d{4})", "built_up_area_m2"),
        (r"MT_UCA_KM2_(?P<year>\d{4})", "urban_centre_area_km2"),
    ]
    panels = [
        indicator_panel(
            frame,
            city_id_column="ID_MTUC_G0",
            metadata_columns=GHSL_MTUC_METADATA,
            indicator_pattern=pattern,
            value_name=value,
            boundary_product="ucdb_multitemporal_boundaries",
        )
        for pattern, value in families
    ]
    keys = [
        "city_id",
        *GHSL_MTUC_METADATA,
        "year",
        "boundary_mode",
        "boundary_product",
    ]
    panel = panels[0]
    for other in panels[1:]:
        panel = panel.merge(other, on=keys, validate="one_to_one")
    measures = ["population", "built_up_area_m2", "urban_centre_area_km2"]
    for column in measures:
        panel[column] = _publisher_numeric(panel[column], column=column)
    core = ["population", "urban_centre_area_km2"]
    partially_missing_core = panel[core].isna().any(axis=1) & panel[core].notna().any(axis=1)
    if partially_missing_core.any():
        raise SourceSchemaError("GHS-UCDB MTUC has incomplete core measures for a city-year")
    panel = panel.loc[panel[core].notna().all(axis=1)].copy()
    birth = panel["GC_UCB_YOB _2025"]
    death = panel["GC_UCB_YOD _2025"]
    if ((panel["year"] < birth) | (panel["year"] > death)).any():
        raise SourceSchemaError("GHS-UCDB MTUC value falls outside its declared lifespan")
    if (panel[measures] <= 0).any().any():
        raise SourceSchemaError("GHS-UCDB MTUC requires positive active-period values")
    panel["built_up_area_available"] = panel["built_up_area_m2"].notna()
    panel["quality_controlled_2025"] = panel["GC_CNT_GAD_2025"].notna()
    reject_duplicate_keys(
        panel, ["city_id", "year", "boundary_product"], source_name="GHS-UCDB MTUC"
    )
    return panel.sort_values(["city_id", "year"]).reset_index(drop=True)

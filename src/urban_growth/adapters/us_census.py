"""Adapters for the U.S. decennial place threshold-validation pilot."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from urban_growth.census_threshold import (
    classify_threshold_measurement_band,
    validate_boundary_cohort,
)
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

PLACE_POPULATION_VARIABLES = {2010: "P001001", 2020: "P1_001N"}


def read_place_population_snapshot(path: Path, *, year: int) -> pd.DataFrame:
    """Read one saved Census API place response without making a network call."""
    if year not in PLACE_POPULATION_VARIABLES:
        raise SourceSchemaError("U.S. place pilot supports only 2010 and 2020")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list) or len(payload) < 2:
        raise SourceSchemaError("Census API snapshot must contain a header and data rows")
    header = payload[0]
    variable = PLACE_POPULATION_VARIABLES[year]
    required = {"NAME", variable, "state", "place"}
    if not required.issubset(header):
        raise SourceSchemaError("Census API snapshot has an unexpected schema")
    frame = pd.DataFrame(payload[1:], columns=header)
    frame["state"] = frame["state"].astype(str).str.zfill(2)
    frame["place"] = frame["place"].astype(str).str.zfill(5)
    frame["geoid"] = frame["state"] + frame["place"]
    frame["population"] = pd.to_numeric(frame[variable], errors="coerce")
    if frame["population"].isna().any() or frame["population"].lt(0).any():
        raise SourceSchemaError("Census place population must be non-negative and complete")
    reject_duplicate_keys(frame, ["geoid"], source_name=f"{year} Census places")
    return frame[["geoid", "NAME", "population"]].rename(columns={"NAME": "place_name"})


def read_2020_place_relationship(path: Path) -> pd.DataFrame:
    """Read the official national 2020-place to 2010-place relationship file."""
    frame = pd.read_csv(path, sep="|", dtype=str, encoding="utf-8-sig")
    required = {
        "GEOID_PLACE_20",
        "GEOID_PLACE_10",
        "NAMELSAD_PLACE_20",
        "NAMELSAD_PLACE_10",
        "AREALAND_PLACE_20",
        "AREALAND_PLACE_10",
        "AREALAND_PART",
    }
    require_columns(frame, required, source_name="2020-to-2010 Census place relationship")
    for column in ["GEOID_PLACE_20", "GEOID_PLACE_10"]:
        frame[column] = frame[column].str.strip().replace("", pd.NA)
    for column in ["AREALAND_PLACE_20", "AREALAND_PLACE_10", "AREALAND_PART"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def build_us_place_boundary_cohort(
    population_2010: pd.DataFrame,
    population_2020: pd.DataFrame,
    relationship: pd.DataFrame,
    *,
    minimum_origin_population: int = 25_000,
    maximum_origin_population: int = 100_000,
    minimum_land_overlap: float = 0.995,
) -> pd.DataFrame:
    """Build a strict one-to-one, near-identical-land U.S. place cohort.

    Land overlap is a feasibility screen, not proof of population comparability.
    Places failing it remain excluded rather than being treated as demographic change.
    """
    if not 0 < minimum_land_overlap <= 1:
        raise SourceSchemaError("Minimum land overlap must be in (0, 1]")
    if minimum_origin_population <= 0 or maximum_origin_population < minimum_origin_population:
        raise SourceSchemaError("Origin population bounds are invalid")
    for frame, label in [
        (population_2010, "2010 Census places"),
        (population_2020, "2020 Census places"),
    ]:
        require_columns(frame, {"geoid", "place_name", "population"}, source_name=label)
        reject_duplicate_keys(frame, ["geoid"], source_name=label)
        if frame["population"].isna().any() or frame["population"].le(0).any():
            raise SourceSchemaError(f"{label} population must be positive and complete")

    require_columns(
        relationship,
        {
            "GEOID_PLACE_10",
            "GEOID_PLACE_20",
            "AREALAND_PLACE_10",
            "AREALAND_PLACE_20",
            "AREALAND_PART",
        },
        source_name="2020-to-2010 Census place relationship",
    )

    related = relationship.dropna(subset=["GEOID_PLACE_10", "GEOID_PLACE_20"]).copy()
    count_10 = related.groupby("GEOID_PLACE_10")["GEOID_PLACE_20"].transform("size")
    count_20 = related.groupby("GEOID_PLACE_20")["GEOID_PLACE_10"].transform("size")
    related["one_to_one_relationship"] = count_10.eq(1) & count_20.eq(1)
    related["origin_land_overlap"] = related["AREALAND_PART"] / related["AREALAND_PLACE_10"]
    related["endpoint_land_overlap"] = related["AREALAND_PART"] / related["AREALAND_PLACE_20"]
    comparable = related.loc[
        related["one_to_one_relationship"]
        & related["origin_land_overlap"].ge(minimum_land_overlap)
        & related["endpoint_land_overlap"].ge(minimum_land_overlap)
    ].copy()
    cohort = comparable.merge(
        population_2010.add_suffix("_2010"),
        left_on="GEOID_PLACE_10",
        right_on="geoid_2010",
        validate="one_to_one",
    ).merge(
        population_2020.add_suffix("_2020"),
        left_on="GEOID_PLACE_20",
        right_on="geoid_2020",
        validate="one_to_one",
    )
    cohort = cohort.loc[
        cohort["population_2010"].between(
            minimum_origin_population, maximum_origin_population, inclusive="both"
        )
    ].copy()
    if cohort.empty:
        raise SourceSchemaError("No U.S. places satisfy the threshold-pilot cohort rules")
    cohort["settlement_id"] = "US_PLACE_2010_" + cohort["GEOID_PLACE_10"]
    cohort["country_code"] = "USA"
    cohort["origin_year"] = 2010
    cohort["endpoint_year"] = 2020
    cohort["population_origin"] = cohort["population_2010"]
    cohort["population_endpoint"] = cohort["population_2020"]
    cohort["geography_status"] = np.where(
        cohort["GEOID_PLACE_10"].eq(cohort["GEOID_PLACE_20"]),
        "stable",
        "official_crosswalk",
    )
    cohort["origin_population_status"] = "direct_decennial_enumeration"
    cohort["endpoint_population_status"] = "direct_decennial_enumeration"
    cohort["origin_threshold_band"] = classify_threshold_measurement_band(
        cohort["population_origin"]
    ).astype(str)
    cohort["endpoint_threshold_band"] = classify_threshold_measurement_band(
        cohort["population_endpoint"]
    ).astype(str)
    cohort["crossed_50000"] = cohort["population_origin"].lt(50_000) & cohort[
        "population_endpoint"
    ].ge(50_000)
    cohort["crossing_interval_lower"] = np.where(cohort["crossed_50000"], 2010, np.nan)
    cohort["crossing_interval_upper"] = np.where(cohort["crossed_50000"], 2020, np.nan)
    cohort["annualized_log_growth"] = (
        np.log(cohort["population_endpoint"]) - np.log(cohort["population_origin"])
    ) / 10
    output_columns = [
        "settlement_id",
        "country_code",
        "GEOID_PLACE_10",
        "GEOID_PLACE_20",
        "place_name_2010",
        "place_name_2020",
        "origin_year",
        "endpoint_year",
        "population_origin",
        "population_endpoint",
        "origin_population_status",
        "endpoint_population_status",
        "geography_status",
        "origin_land_overlap",
        "endpoint_land_overlap",
        "origin_threshold_band",
        "endpoint_threshold_band",
        "crossed_50000",
        "crossing_interval_lower",
        "crossing_interval_upper",
        "annualized_log_growth",
    ]
    result = cohort[output_columns].sort_values("settlement_id").reset_index(drop=True)
    validate_boundary_cohort(result)
    return result

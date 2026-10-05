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


def _validate_us_place_inputs(
    population_2010: pd.DataFrame,
    population_2020: pd.DataFrame,
    relationship: pd.DataFrame,
) -> None:
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


def build_us_place_origin_denominator(
    population_2010: pd.DataFrame,
    population_2020: pd.DataFrame,
    relationship: pd.DataFrame,
    *,
    minimum_origin_population: int = 25_000,
    maximum_origin_population: int = 100_000,
    minimum_land_overlap: float = 0.995,
) -> pd.DataFrame:
    """Fix the 2010 population cohort before evaluating geographic concordance.

    Every 2010 place inside the registered population bounds remains in the denominator.
    Relationship quality, land overlap, and endpoint population are classified only after
    membership is fixed. Unresolved places therefore cannot disappear before coverage is
    measured.
    """
    if not 0 < minimum_land_overlap <= 1:
        raise SourceSchemaError("Minimum land overlap must be in (0, 1]")
    if minimum_origin_population <= 0 or maximum_origin_population < minimum_origin_population:
        raise SourceSchemaError("Origin population bounds are invalid")
    _validate_us_place_inputs(population_2010, population_2020, relationship)

    denominator = population_2010.loc[
        population_2010["population"].between(
            minimum_origin_population, maximum_origin_population, inclusive="both"
        )
    ].copy()
    if denominator.empty:
        raise SourceSchemaError("No U.S. places satisfy the origin population cohort rules")
    denominator = denominator.rename(
        columns={"geoid": "GEOID_PLACE_10", "place_name": "place_name_2010", "population": "population_origin"}
    )
    denominator["settlement_id"] = "US_PLACE_2010_" + denominator["GEOID_PLACE_10"]
    denominator["country_code"] = "USA"
    denominator["origin_year"] = 2010
    denominator["endpoint_year"] = 2020
    denominator["cohort_defined_at_origin"] = True
    denominator["cohort_population_basis"] = "population_origin"
    denominator["cohort_uses_endpoint_population"] = False

    related = relationship.dropna(subset=["GEOID_PLACE_10", "GEOID_PLACE_20"]).copy()
    related = related.drop_duplicates(subset=["GEOID_PLACE_10", "GEOID_PLACE_20"])
    origin_counts = related.groupby("GEOID_PLACE_10")["GEOID_PLACE_20"].nunique()
    endpoint_counts = related.groupby("GEOID_PLACE_20")["GEOID_PLACE_10"].nunique()
    related["origin_endpoint_count"] = related["GEOID_PLACE_10"].map(origin_counts)
    related["endpoint_origin_count"] = related["GEOID_PLACE_20"].map(endpoint_counts)
    related["one_to_one_relationship"] = related["origin_endpoint_count"].eq(1) & related[
        "endpoint_origin_count"
    ].eq(1)
    related["origin_land_overlap"] = related["AREALAND_PART"] / related["AREALAND_PLACE_10"]
    related["endpoint_land_overlap"] = related["AREALAND_PART"] / related["AREALAND_PLACE_20"]

    one_row_per_origin = related.sort_values(
        ["GEOID_PLACE_10", "one_to_one_relationship", "origin_land_overlap", "endpoint_land_overlap"],
        ascending=[True, False, False, False],
        na_position="last",
    ).drop_duplicates(subset=["GEOID_PLACE_10"], keep="first")
    keep_relationship = [
        "GEOID_PLACE_10",
        "GEOID_PLACE_20",
        "origin_endpoint_count",
        "endpoint_origin_count",
        "one_to_one_relationship",
        "origin_land_overlap",
        "endpoint_land_overlap",
    ]
    denominator = denominator.merge(
        one_row_per_origin[keep_relationship],
        on="GEOID_PLACE_10",
        how="left",
        validate="one_to_one",
    )

    endpoint = population_2020.rename(
        columns={"geoid": "GEOID_PLACE_20", "place_name": "place_name_2020", "population": "population_endpoint"}
    )
    denominator = denominator.merge(endpoint, on="GEOID_PLACE_20", how="left", validate="many_to_one")

    denominator["concordance_resolved"] = (
        denominator["one_to_one_relationship"].fillna(False).astype(bool)
        & denominator["origin_land_overlap"].ge(minimum_land_overlap).fillna(False)
        & denominator["endpoint_land_overlap"].ge(minimum_land_overlap).fillna(False)
    )
    denominator["endpoint_population_observed"] = denominator["population_endpoint"].notna()
    denominator["analysis_eligible"] = denominator["concordance_resolved"] & denominator[
        "endpoint_population_observed"
    ]

    denominator["concordance_exclusion_reason"] = "eligible"
    no_relationship = denominator["GEOID_PLACE_20"].isna()
    multiple_endpoint = denominator["origin_endpoint_count"].fillna(0).gt(1)
    multiple_origin = denominator["endpoint_origin_count"].fillna(0).gt(1)
    missing_overlap = (
        denominator["GEOID_PLACE_20"].notna()
        & (denominator["origin_land_overlap"].isna() | denominator["endpoint_land_overlap"].isna())
    )
    low_origin_overlap = denominator["origin_land_overlap"].lt(minimum_land_overlap).fillna(False)
    low_endpoint_overlap = denominator["endpoint_land_overlap"].lt(minimum_land_overlap).fillna(False)
    missing_endpoint_population = denominator["concordance_resolved"] & ~denominator[
        "endpoint_population_observed"
    ]
    denominator.loc[no_relationship, "concordance_exclusion_reason"] = "no_relationship"
    denominator.loc[multiple_endpoint, "concordance_exclusion_reason"] = "origin_to_multiple_endpoints"
    denominator.loc[~multiple_endpoint & multiple_origin, "concordance_exclusion_reason"] = (
        "endpoint_from_multiple_origins"
    )
    denominator.loc[
        ~(multiple_endpoint | multiple_origin) & missing_overlap,
        "concordance_exclusion_reason",
    ] = "missing_land_overlap"
    denominator.loc[
        ~(multiple_endpoint | multiple_origin | missing_overlap) & low_origin_overlap,
        "concordance_exclusion_reason",
    ] = "insufficient_origin_land_overlap"
    denominator.loc[
        ~(multiple_endpoint | multiple_origin | missing_overlap | low_origin_overlap)
        & low_endpoint_overlap,
        "concordance_exclusion_reason",
    ] = "insufficient_endpoint_land_overlap"
    denominator.loc[missing_endpoint_population, "concordance_exclusion_reason"] = (
        "endpoint_population_missing"
    )

    denominator["geography_status"] = "unresolved"
    stable = denominator["concordance_resolved"] & denominator["GEOID_PLACE_10"].eq(
        denominator["GEOID_PLACE_20"]
    )
    denominator.loc[stable, "geography_status"] = "stable"
    denominator.loc[denominator["concordance_resolved"] & ~stable, "geography_status"] = (
        "official_crosswalk"
    )
    denominator["minimum_land_overlap_rule"] = minimum_land_overlap
    reject_duplicate_keys(denominator, ["settlement_id"], source_name="U.S. place origin denominator")
    return denominator.sort_values("settlement_id").reset_index(drop=True)


def us_place_concordance_coverage(denominator: pd.DataFrame) -> pd.DataFrame:
    """Summarize concordance coverage against the origin-defined denominator."""
    require_columns(
        denominator,
        {
            "settlement_id",
            "population_origin",
            "concordance_resolved",
            "endpoint_population_observed",
            "analysis_eligible",
            "cohort_defined_at_origin",
            "cohort_uses_endpoint_population",
        },
        source_name="U.S. place origin denominator",
    )
    reject_duplicate_keys(denominator, ["settlement_id"], source_name="U.S. place origin denominator")
    if not denominator["cohort_defined_at_origin"].eq(True).all():
        raise SourceSchemaError("U.S. denominator must be defined at origin")
    if not denominator["cohort_uses_endpoint_population"].eq(False).all():
        raise SourceSchemaError("U.S. denominator cannot use endpoint population for membership")
    total_rows = len(denominator)
    total_population = float(denominator["population_origin"].sum())
    if total_rows == 0 or total_population <= 0:
        raise SourceSchemaError("U.S. denominator coverage requires positive cohort support")

    resolved = denominator["concordance_resolved"].astype(bool)
    observed = denominator["endpoint_population_observed"].astype(bool)
    eligible = denominator["analysis_eligible"].astype(bool)
    return pd.DataFrame(
        [
            {
                "origin_denominator_rows": total_rows,
                "origin_denominator_population": total_population,
                "concordance_resolved_rows": int(resolved.sum()),
                "concordance_resolved_population": float(
                    denominator.loc[resolved, "population_origin"].sum()
                ),
                "concordance_count_coverage": float(resolved.mean()),
                "concordance_population_coverage": float(
                    denominator.loc[resolved, "population_origin"].sum() / total_population
                ),
                "endpoint_population_observed_rows": int(observed.sum()),
                "analysis_eligible_rows": int(eligible.sum()),
                "analysis_eligible_count_coverage": float(eligible.mean()),
                "analysis_eligible_population_coverage": float(
                    denominator.loc[eligible, "population_origin"].sum() / total_population
                ),
                "coverage_denominator_rule": "2010_origin_population_25000_100000_before_concordance",
                "future_outcome_used_for_membership": False,
                "coverage_threshold_registered": False,
            }
        ]
    )


def build_us_place_boundary_cohort(
    population_2010: pd.DataFrame,
    population_2020: pd.DataFrame,
    relationship: pd.DataFrame,
    *,
    minimum_origin_population: int = 25_000,
    maximum_origin_population: int = 100_000,
    minimum_land_overlap: float = 0.995,
) -> pd.DataFrame:
    """Build the resolved U.S. analysis cohort from an origin-defined denominator."""
    denominator = build_us_place_origin_denominator(
        population_2010,
        population_2020,
        relationship,
        minimum_origin_population=minimum_origin_population,
        maximum_origin_population=maximum_origin_population,
        minimum_land_overlap=minimum_land_overlap,
    )
    cohort = denominator.loc[denominator["analysis_eligible"]].copy()
    if cohort.empty:
        raise SourceSchemaError("No U.S. places satisfy the threshold-pilot analysis rules")
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

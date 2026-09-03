"""Qualification gate for a China direct-count benchmark under issue #124."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

REQUIRED = {
    "candidate_id",
    "official_source",
    "waves",
    "direct_enumeration",
    "locality_concept_comparable",
    "population_concept_consistent",
    "origin_denominator_available",
    "future_membership_conditioned",
    "official_population_weighted_concordance",
    "usable_forecast_origins",
    "release_status",
}


def china_issue_124_source_register() -> pd.DataFrame:
    """Register official China source paths without equating cities and administrative units."""
    return pd.DataFrame(
        [
            {
                "candidate_id": "china_census_county_2000_2020",
                "official_source": "NBS fifth, sixth, and seventh national population censuses",
                "waves": "2000;2010;2020",
                "direct_enumeration": True,
                "locality_concept_comparable": False,
                "population_concept_consistent": True,
                "origin_denominator_available": True,
                "future_membership_conditioned": False,
                "official_population_weighted_concordance": False,
                "usable_forecast_origins": 1,
                "release_status": "released",
                "qualification_note": (
                    "County, county-level city, and urban-district populations are administrative "
                    "territories rather than stable settlement footprints; three waves yield only "
                    "one recent-to-future origin"
                ),
            },
            {
                "candidate_id": "china_census_county_1990_2020",
                "official_source": "NBS fourth through seventh national population censuses",
                "waves": "1990;2000;2010;2020",
                "direct_enumeration": True,
                "locality_concept_comparable": False,
                "population_concept_consistent": True,
                "origin_denominator_available": True,
                "future_membership_conditioned": False,
                "official_population_weighted_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "released_fragmented",
                "qualification_note": (
                    "Nominally enough waves, but no registered national population-weighted "
                    "crosswalk resolves district annexations, splits, mergers, and code changes"
                ),
            },
            {
                "candidate_id": "china_city_statistical_yearbooks",
                "official_source": "NBS and Ministry of Housing urban construction/city yearbooks",
                "waves": "annual",
                "direct_enumeration": False,
                "locality_concept_comparable": False,
                "population_concept_consistent": False,
                "origin_denominator_available": False,
                "future_membership_conditioned": False,
                "official_population_weighted_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "released",
                "qualification_note": (
                    "Annual city fields mix administrative territory, urban district, built-up-area, "
                    "permanent-resident, and hukou concepts and are not direct locality enumerations"
                ),
            },
            {
                "candidate_id": "china_statistical_zoning_codes",
                "official_source": "NBS statistical division and urban-rural division codes",
                "waves": "annual_from_2009",
                "direct_enumeration": False,
                "locality_concept_comparable": False,
                "population_concept_consistent": False,
                "origin_denominator_available": False,
                "future_membership_conditioned": False,
                "official_population_weighted_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "released",
                "qualification_note": (
                    "Codes classify main-city, fringe, town-centre, and rural areas for a vintage; "
                    "they do not provide direct counts or a population-weighted crosswave concordance"
                ),
            },
            {
                "candidate_id": "china_prefecture_city_totals",
                "official_source": "China Statistical Yearbook prefecture-level administrative data",
                "waves": "annual",
                "direct_enumeration": False,
                "locality_concept_comparable": False,
                "population_concept_consistent": False,
                "origin_denominator_available": True,
                "future_membership_conditioned": False,
                "official_population_weighted_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "released",
                "qualification_note": (
                    "Prefecture-level cities include large rural hinterlands and cannot be matched "
                    "to GHSL urban-centre footprints as if they were individual localities"
                ),
            },
        ]
    )


def qualify_china_issue_124_sources(register: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the direct-count, geographic-identity, and multi-origin requirements."""
    require_columns(register, REQUIRED, source_name="China issue 124 source register")
    reject_duplicate_keys(register, ["candidate_id"], source_name="China issue 124 source register")
    out = register.copy()
    boolean_columns = [
        "direct_enumeration",
        "locality_concept_comparable",
        "population_concept_consistent",
        "origin_denominator_available",
        "future_membership_conditioned",
        "official_population_weighted_concordance",
    ]
    for column in boolean_columns:
        if out[column].isna().any():
            raise SourceSchemaError(f"China source register has unknown {column}")
        out[column] = out[column].astype(bool)
    out["usable_forecast_origins"] = pd.to_numeric(
        out["usable_forecast_origins"], errors="coerce"
    )
    if out["usable_forecast_origins"].isna().any():
        raise SourceSchemaError("China source register has invalid usable forecast-origin counts")

    out["issue_124_qualified"] = (
        out["direct_enumeration"]
        & out["locality_concept_comparable"]
        & out["population_concept_consistent"]
        & out["origin_denominator_available"]
        & ~out["future_membership_conditioned"]
        & out["official_population_weighted_concordance"]
        & out["usable_forecast_origins"].ge(2)
        & out["release_status"].eq("released")
    )
    out["exclusion_reason"] = "qualified"
    out.loc[~out["direct_enumeration"], "exclusion_reason"] = "not_direct_enumeration"
    out.loc[
        out["direct_enumeration"] & ~out["locality_concept_comparable"], "exclusion_reason"
    ] = "administrative_unit_not_comparable_locality"
    out.loc[
        out["direct_enumeration"]
        & out["locality_concept_comparable"]
        & ~out["population_concept_consistent"],
        "exclusion_reason",
    ] = "population_concept_inconsistent"
    out.loc[out["future_membership_conditioned"], "exclusion_reason"] = (
        "future_conditioned_universe"
    )
    out.loc[
        out["direct_enumeration"]
        & out["locality_concept_comparable"]
        & out["population_concept_consistent"]
        & ~out["official_population_weighted_concordance"],
        "exclusion_reason",
    ] = "official_population_weighted_concordance_unresolved"
    out.loc[
        out["direct_enumeration"]
        & out["locality_concept_comparable"]
        & out["population_concept_consistent"]
        & out["official_population_weighted_concordance"]
        & out["usable_forecast_origins"].lt(2),
        "exclusion_reason",
    ] = "insufficient_forecast_origins"
    out.loc[out["release_status"].eq("not_released"), "exclusion_reason"] = (
        "official_outputs_not_released"
    )

    qualified = out["issue_124_qualified"]
    status = pd.DataFrame(
        [
            {
                "issue": 124,
                "pilot": "China national censuses",
                "candidate_sources": len(out),
                "qualified_sources": int(qualified.sum()),
                "benchmark_estimable": bool(qualified.any()),
                "h1_independent_confirmation": False,
                "county_2000_2020_sensitivity_permitted": True,
                "county_sensitivity_closes_issue_124": False,
                "decision": (
                    "ready_for_matched_benchmark"
                    if qualified.any()
                    else "unresolved_no_stable_locality_multiwave_population_concordance"
                ),
            }
        ]
    )
    return out, status

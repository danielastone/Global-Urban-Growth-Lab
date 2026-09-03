"""Qualification and acquisition gate for Japan under issue #124."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

REQUIRED = {
    "candidate_id",
    "official_source",
    "waves",
    "direct_census_population",
    "locality_concept_comparable",
    "population_concept_consistent",
    "official_vintage_geometry",
    "usable_forecast_origins",
    "future_membership_conditioned",
    "data_acquired",
    "origin_denominator_constructed",
    "geometry_overlap_audited",
}


def japan_issue_124_source_register() -> pd.DataFrame:
    """Register Japan candidates, separating a viable DID path from municipality shortcuts."""
    return pd.DataFrame(
        [
            {
                "candidate_id": "japan_did_2000_2020",
                "official_source": "Statistics Bureau Population Census Densely Inhabited Districts",
                "waves": "2000;2005;2010;2015;2020",
                "direct_census_population": True,
                "locality_concept_comparable": True,
                "population_concept_consistent": True,
                "official_vintage_geometry": True,
                "usable_forecast_origins": 3,
                "future_membership_conditioned": False,
                "data_acquired": True,
                "origin_denominator_constructed": True,
                "geometry_overlap_audited": True,
                "qualification_note": (
                    "Qualified national path: registered direct counts and vintage DID geometry "
                    "with origin-first overlap audit and explicit unresolved denominators"
                ),
            },
            {
                "candidate_id": "japan_municipal_census_2000_2025",
                "official_source": "Statistics Bureau Population Census municipality tables",
                "waves": "2000;2005;2010;2015;2020;2025_preliminary",
                "direct_census_population": True,
                "locality_concept_comparable": False,
                "population_concept_consistent": True,
                "official_vintage_geometry": True,
                "usable_forecast_origins": 4,
                "future_membership_conditioned": False,
                "data_acquired": False,
                "origin_denominator_constructed": False,
                "geometry_overlap_audited": False,
                "qualification_note": (
                    "Strong administrative-unit sensitivity, but municipalities can combine multiple "
                    "settlements and rural territory and are not interchangeable with urban localities"
                ),
            },
            {
                "candidate_id": "japan_current_boundary_readjusted_municipal_history",
                "official_source": "Population Census prior-wave population readjusted to later boundaries",
                "waves": "adjacent_five_year_pairs",
                "direct_census_population": True,
                "locality_concept_comparable": False,
                "population_concept_consistent": True,
                "official_vintage_geometry": True,
                "usable_forecast_origins": 0,
                "future_membership_conditioned": True,
                "data_acquired": False,
                "origin_denominator_constructed": False,
                "geometry_overlap_audited": False,
                "qualification_note": (
                    "Useful for transition checks, but chaining histories on a later municipality "
                    "universe conditions earlier membership on future mergers and boundaries"
                ),
            },
            {
                "candidate_id": "japan_population_census_mesh",
                "official_source": "Statistics Bureau Population Census small-area and grid-square data",
                "waves": "2000;2005;2010;2015;2020",
                "direct_census_population": True,
                "locality_concept_comparable": False,
                "population_concept_consistent": True,
                "official_vintage_geometry": True,
                "usable_forecast_origins": 3,
                "future_membership_conditioned": False,
                "data_acquired": False,
                "origin_denominator_constructed": False,
                "geometry_overlap_audited": False,
                "qualification_note": (
                    "Potential fixed-footprint sensitivity, but grid cells are not official localities "
                    "and aggregation to a later GHSL footprint would reintroduce future membership"
                ),
            },
        ]
    )


def qualify_japan_issue_124_sources(register: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Identify acquisition-ready sources and qualify only registered, audited inputs."""
    require_columns(register, REQUIRED, source_name="Japan issue 124 source register")
    reject_duplicate_keys(register, ["candidate_id"], source_name="Japan issue 124 source register")
    out = register.copy()
    boolean_columns = [
        "direct_census_population",
        "locality_concept_comparable",
        "population_concept_consistent",
        "official_vintage_geometry",
        "future_membership_conditioned",
        "data_acquired",
        "origin_denominator_constructed",
        "geometry_overlap_audited",
    ]
    for column in boolean_columns:
        if out[column].isna().any():
            raise SourceSchemaError(f"Japan source register has unknown {column}")
        out[column] = out[column].astype(bool)
    out["usable_forecast_origins"] = pd.to_numeric(
        out["usable_forecast_origins"], errors="coerce"
    )
    if out["usable_forecast_origins"].isna().any():
        raise SourceSchemaError("Japan source register has invalid usable forecast-origin counts")

    out["acquisition_ready"] = (
        out["direct_census_population"]
        & out["locality_concept_comparable"]
        & out["population_concept_consistent"]
        & out["official_vintage_geometry"]
        & out["usable_forecast_origins"].ge(2)
        & ~out["future_membership_conditioned"]
    )
    out["issue_124_qualified"] = (
        out["acquisition_ready"]
        & out["data_acquired"]
        & out["origin_denominator_constructed"]
        & out["geometry_overlap_audited"]
    )
    out["status"] = "not_comparable_locality_source"
    out.loc[out["future_membership_conditioned"], "status"] = "future_conditioned_universe"
    out.loc[
        out["direct_census_population"]
        & out["locality_concept_comparable"]
        & out["usable_forecast_origins"].lt(2),
        "status",
    ] = "insufficient_forecast_origins"
    out.loc[out["acquisition_ready"] & ~out["data_acquired"], "status"] = (
        "acquisition_ready_inputs_not_registered"
    )
    out.loc[
        out["acquisition_ready"]
        & out["data_acquired"]
        & ~out["origin_denominator_constructed"],
        "status",
    ] = "origin_denominator_not_constructed"
    out.loc[
        out["acquisition_ready"]
        & out["data_acquired"]
        & out["origin_denominator_constructed"]
        & ~out["geometry_overlap_audited"],
        "status",
    ] = "geometry_overlap_not_audited"
    out.loc[out["issue_124_qualified"], "status"] = "qualified"

    acquisition_ready = out["acquisition_ready"]
    qualified = out["issue_124_qualified"]
    status = pd.DataFrame(
        [
            {
                "issue": 124,
                "pilot": "Japan Population Census DIDs",
                "candidate_sources": len(out),
                "acquisition_ready_sources": int(acquisition_ready.sum()),
                "qualified_sources": int(qualified.sum()),
                "benchmark_estimable": bool(qualified.any()),
                "h1_independent_confirmation": False,
                "recommended_candidate": "japan_did_2000_2020",
                "next_gate": (
                    "run_matched_direct_ghsl_benchmark"
                    if qualified.any()
                    else "acquire_did_counts_and_geometry_then_audit_origin_overlap"
                ),
                "decision": (
                    "ready_for_matched_benchmark"
                    if qualified.any()
                    else "acquisition_ready_not_yet_empirically_qualified"
                ),
            }
        ]
    )
    return out, status

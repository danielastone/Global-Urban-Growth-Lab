"""Source-specific City Data Fitness mapping for GHSL fixed-boundary forecasts."""

from __future__ import annotations

import pandas as pd

from urban_growth.data_fitness import evaluate_city_data_fitness
from urban_growth.io import SourceSchemaError, require_columns


def apply_ghsl_fixed_forecast_fitness(panel: pd.DataFrame) -> pd.DataFrame:
    """Map GHSL fixed-2025 forecast intervals into the common fitness vocabulary.

    The thematic GHSL stream is temporally fixed because every historical statistic is
    measured inside the 2025 urban-centre footprint. That makes growth comparisons
    internally stable, but it also uses future boundary information relative to earlier
    forecast origins. Rows can therefore be used for retrospective persistence
    sensitivity analysis, but never as deployable-at-origin or headline evidence.
    """
    require_columns(
        panel,
        {
            "city_id",
            "country_code",
            "period_start",
            "period_end",
            "boundary_mode",
            "boundary_product",
            "boundary_reference_year",
            "boundary_temporally_fixed",
            "boundary_history_uses_future_reference",
            "cross_stream_reconciled",
        },
        source_name="GHSL fixed forecast panel",
    )
    if panel["boundary_mode"].ne("fixed").any():
        raise SourceSchemaError("GHSL fixed fitness requires fixed-boundary rows only")
    if panel["boundary_product"].ne("ucdb_fixed_2025_boundary").any():
        raise SourceSchemaError("GHSL fixed fitness requires the registered thematic boundary product")
    if panel["boundary_reference_year"].ne(2025).any():
        raise SourceSchemaError("GHSL fixed fitness requires the 2025 reference boundary")
    if not panel["boundary_temporally_fixed"].eq(True).all():
        raise SourceSchemaError("GHSL fixed fitness requires temporally fixed boundaries")
    if not panel["boundary_history_uses_future_reference"].eq(True).all():
        raise SourceSchemaError("GHSL fixed histories must declare use of the 2025 future reference")
    if not panel["cross_stream_reconciled"].eq(True).all():
        raise SourceSchemaError("GHSL fixed forecast rows require completed 2025 cross-stream reconciliation")

    evidence = panel.copy()
    evidence["source_id"] = "ghsl_ucdb_r2024a_v1_2_fixed"
    evidence["population_concept"] = "ghsl_urban_centre_population_inside_2025_footprint"
    evidence["geographic_unit"] = "urban_centre_fixed_2025_polygon"
    evidence["reference_date"] = evidence["period_start"]
    evidence["observation_type"] = "retrospective_model_epoch"
    evidence["temporal_comparable"] = True
    evidence["geographic_comparable"] = True
    evidence["concordance_status"] = "stable"
    evidence["boundary_change_status"] = "none_within_fixed_2025_footprint"
    evidence["administrative_reclassification"] = False
    evidence["methodology_change"] = False
    evidence["minimum_reporting_threshold"] = "not_applicable_fixed_thematic_stream"
    evidence["truncation_exposure"] = "low"
    evidence["survivorship_exposure"] = "material"
    evidence["known_inconsistency"] = False
    evidence["validation_status"] = "passed"
    evidence["coordinates_validated"] = False
    evidence["network_geography_validated"] = False

    evaluated = evaluate_city_data_fitness(evidence)
    # Source-specific override: retrospective fixed-footprint growth is analytically
    # usable, but a 2025 boundary is future information for earlier forecast origins.
    evaluated["headline_eligible"] = False
    evaluated["headline_exclusion_reasons"] = evaluated["headline_exclusion_reasons"].apply(
        lambda value: ";".join(filter(None, [value, "future_boundary_reference"]))
    )
    evaluated["deployable_at_origin"] = False
    evaluated["benchmark_interpretation"] = "retrospective_stable_footprint_sensitivity"
    evaluated["boundary_information_leakage"] = True
    return evaluated

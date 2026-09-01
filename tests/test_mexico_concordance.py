from __future__ import annotations

import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.mexico_concordance import (
    build_mexico_multiwave_history,
    mexico_transition_coverage,
    validate_mexico_locality_transition,
)


def row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "analysis_id": "MEX_LOC_001",
        "origin_year": 1995,
        "endpoint_year": 2000,
        "origin_population": 40_000,
        "endpoint_population": 44_000,
        "origin_event_type": "population_count",
        "endpoint_event_type": "census",
        "match_status": "stable_geometry",
        "relationship_cardinality": "one_to_one",
        "origin_overlap_ratio": 0.999,
        "endpoint_overlap_ratio": 0.999,
        "official_relationship_verified": True,
        "all_components_identified": True,
        "population_aggregation_complete": True,
        "double_count_free": True,
        "methodology_comparable": True,
        "evidence_reference_year": 2000,
        "uses_future_boundary_reference": False,
        "exclusion_reason": "",
    }
    base.update(overrides)
    return base


def test_transition_rejects_future_boundary_evidence() -> None:
    frame = pd.DataFrame([row(evidence_reference_year=2005)])
    with pytest.raises(SourceSchemaError, match="may not post-date"):
        validate_mexico_locality_transition(frame)


def test_harmonized_transition_requires_complete_components() -> None:
    frame = pd.DataFrame(
        [
            row(
                match_status="harmonized_common_geography",
                relationship_cardinality="one_to_many",
                all_components_identified=False,
            )
        ]
    )
    with pytest.raises(SourceSchemaError, match="complete official components"):
        validate_mexico_locality_transition(frame)


def test_methodology_failure_is_retained_but_ineligible() -> None:
    result = validate_mexico_locality_transition(
        pd.DataFrame([row(methodology_comparable=False)])
    )
    assert not result.loc[0, "transition_eligible"]
    assert result.loc[0, "transition_exclusion_reason"] == "methodology_not_comparable"


def test_multiwave_history_uses_only_immediately_prior_transition() -> None:
    transitions = pd.DataFrame(
        [
            row(),
            row(
                origin_year=2000,
                endpoint_year=2005,
                origin_population=44_000,
                endpoint_population=48_000,
                origin_event_type="census",
                endpoint_event_type="population_count",
                evidence_reference_year=2005,
            ),
            row(
                origin_year=2005,
                endpoint_year=2010,
                origin_population=48_000,
                endpoint_population=53_000,
                origin_event_type="population_count",
                endpoint_event_type="census",
                evidence_reference_year=2010,
            ),
        ]
    )
    result = build_mexico_multiwave_history(transitions)
    first = result.loc[result["origin_year"].eq(1995)].iloc[0]
    second = result.loc[result["origin_year"].eq(2000)].iloc[0]
    third = result.loc[result["origin_year"].eq(2005)].iloc[0]
    assert not first["forecast_interval_eligible"]
    assert second["forecast_interval_eligible"]
    assert third["forecast_interval_eligible"]
    assert second["previous_origin_year"] == 1995
    assert third["previous_origin_year"] == 2000
    assert not result["boundary_history_uses_future_reference"].any()


def test_transition_eligibility_does_not_self_promote_to_headline_or_deployable() -> None:
    transitions = pd.DataFrame(
        [
            row(),
            row(
                origin_year=2000,
                endpoint_year=2005,
                origin_population=44_000,
                endpoint_population=48_000,
                origin_event_type="census",
                endpoint_event_type="population_count",
                evidence_reference_year=2005,
            ),
        ]
    )
    result = build_mexico_multiwave_history(transitions)
    current = result.loc[result["origin_year"].eq(2000)].iloc[0]

    assert current["forecast_interval_eligible"]
    assert current["growth_eligible"]
    assert not current["headline_eligible"]
    assert current["headline_exclusion_reasons"] == "common_city_data_fitness_not_applied"
    assert not current["forecast_deployable_at_origin"]
    assert current["deployability_exclusion_reason"] == "point_in_time_availability_not_applied"


def test_failed_prior_transition_blocks_next_forecast_origin() -> None:
    transitions = pd.DataFrame(
        [
            row(methodology_comparable=False),
            row(
                origin_year=2000,
                endpoint_year=2005,
                origin_population=44_000,
                endpoint_population=48_000,
                origin_event_type="census",
                endpoint_event_type="population_count",
                evidence_reference_year=2005,
            ),
        ]
    )
    result = build_mexico_multiwave_history(transitions)
    current = result.loc[result["origin_year"].eq(2000)].iloc[0]
    assert not current["forecast_interval_eligible"]


def test_coverage_keeps_unresolved_records_in_denominator() -> None:
    frame = pd.DataFrame(
        [
            row(analysis_id="A", origin_population=40_000),
            row(
                analysis_id="B",
                origin_population=60_000,
                endpoint_population=65_000,
                match_status="unresolved",
                relationship_cardinality="one_to_many",
                official_relationship_verified=False,
                origin_overlap_ratio=0.5,
                endpoint_overlap_ratio=0.5,
                exclusion_reason="split_unresolved",
            ),
        ]
    )
    coverage = mexico_transition_coverage(frame)
    assert coverage.loc[0, "origin_localities"] == 2
    assert coverage.loc[0, "eligible_localities"] == 1
    assert coverage.loc[0, "count_coverage"] == 0.5
    assert coverage.loc[0, "population_coverage"] == 0.4

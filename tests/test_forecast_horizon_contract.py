import pandas as pd
import pytest

from urban_growth.forecast_fitness import evaluate_fitness_gated_persistence_baselines
from urban_growth.io import SourceSchemaError
from urban_growth.mexico_concordance import build_mexico_multiwave_history


def _mexico_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
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
    row.update(overrides)
    return row


def test_mexico_history_records_each_forecast_horizon() -> None:
    transitions = pd.DataFrame(
        [
            _mexico_row(),
            _mexico_row(
                origin_year=2000,
                endpoint_year=2005,
                origin_population=44_000,
                endpoint_population=48_000,
                origin_event_type="census",
                endpoint_event_type="population_count",
                evidence_reference_year=2005,
            ),
            _mexico_row(
                origin_year=2005,
                endpoint_year=2015,
                origin_population=48_000,
                endpoint_population=58_000,
                origin_event_type="population_count",
                endpoint_event_type="census",
                evidence_reference_year=2015,
            ),
        ]
    )
    result = build_mexico_multiwave_history(transitions)
    horizons = dict(zip(result["origin_year"], result["forecast_horizon_years"], strict=True))
    assert horizons[2000] == 5
    assert horizons[2005] == 10


def test_explicit_mixed_horizons_cannot_be_pooled() -> None:
    panel = pd.DataFrame(
        [
            {"city_id": "A", "country_code": "AAA", "period_start": 2000, "period_end": 2005, "recent_growth": 0.01, "future_growth": 0.01, "growth_eligible": True, "forecast_horizon_years": 5},
            {"city_id": "A", "country_code": "AAA", "period_start": 2005, "period_end": 2010, "recent_growth": 0.01, "future_growth": 0.01, "growth_eligible": True, "forecast_horizon_years": 5},
            {"city_id": "A", "country_code": "AAA", "period_start": 2010, "period_end": 2020, "recent_growth": 0.01, "future_growth": 0.01, "growth_eligible": True, "forecast_horizon_years": 10},
        ]
    )
    with pytest.raises(SourceSchemaError, match="cannot pool mixed forecast horizons"):
        evaluate_fitness_gated_persistence_baselines(panel, [2005, 2010])

import pandas as pd
import pytest

from urban_growth.census_threshold import (
    classify_threshold_measurement_band,
    entry_delay_interval,
    origin_defined_threshold_cohort,
    validate_boundary_cohort,
)
from urban_growth.io import SourceSchemaError


def test_entry_delay_bounds_are_open_and_correct() -> None:
    interval = entry_delay_interval(
        crossing_lower=2000, crossing_upper=2010, entry_lower=2005, entry_upper=2015
    )
    assert interval.lower == -5
    assert interval.upper == 15


def test_threshold_uncertainty_band() -> None:
    result = classify_threshold_measurement_band(pd.Series([47_499, 47_500, 52_499, 52_500]))
    assert result.astype(str).tolist() == [
        "clearly_below",
        "threshold_uncertain",
        "threshold_uncertain",
        "clearly_above",
    ]


def test_boundary_cohort_rejects_unresolved_geography() -> None:
    frame = pd.DataFrame(
        {
            "settlement_id": ["a"],
            "country_code": ["X"],
            "origin_year": [2000],
            "endpoint_year": [2010],
            "population_origin": [40_000],
            "population_endpoint": [60_000],
            "geography_status": ["unresolved"],
        }
    )
    with pytest.raises(SourceSchemaError, match="unresolved"):
        validate_boundary_cohort(frame)


def test_threshold_cohort_membership_uses_origin_population_only() -> None:
    frame = pd.DataFrame(
        {
            "settlement_id": ["grower", "decliner", "future_entrant", "future_exit"],
            "country_code": ["X"] * 4,
            "origin_year": [2000] * 4,
            "endpoint_year": [2010] * 4,
            "population_origin": [40_000, 80_000, 20_000, 120_000],
            "population_endpoint": [70_000, 30_000, 70_000, 80_000],
            "geography_status": ["stable"] * 4,
        }
    )
    result = origin_defined_threshold_cohort(frame)
    assert set(result["settlement_id"]) == {"grower", "decliner"}
    assert result["cohort_population_basis"].eq("population_origin").all()
    assert not result["cohort_uses_endpoint_population"].any()
    assert result["cohort_defined_at_origin"].all()


def test_threshold_cohort_is_invariant_to_endpoint_population_changes() -> None:
    frame = pd.DataFrame(
        {
            "settlement_id": ["a", "b", "c"],
            "country_code": ["X"] * 3,
            "origin_year": [2000] * 3,
            "endpoint_year": [2010] * 3,
            "population_origin": [30_000, 60_000, 110_000],
            "population_endpoint": [35_000, 65_000, 115_000],
            "geography_status": ["stable"] * 3,
        }
    )
    first = origin_defined_threshold_cohort(frame)
    changed = frame.copy()
    changed["population_endpoint"] = [200_000, 1_000, 50_000]
    second = origin_defined_threshold_cohort(changed)
    assert first["settlement_id"].tolist() == second["settlement_id"].tolist() == ["a", "b"]


def test_threshold_cohort_rejects_invalid_bounds() -> None:
    frame = pd.DataFrame(
        {
            "settlement_id": ["a"],
            "country_code": ["X"],
            "origin_year": [2000],
            "endpoint_year": [2010],
            "population_origin": [40_000],
            "population_endpoint": [60_000],
            "geography_status": ["stable"],
        }
    )
    with pytest.raises(SourceSchemaError, match="bounds"):
        origin_defined_threshold_cohort(frame, cohort_min=100_000, cohort_max=25_000)

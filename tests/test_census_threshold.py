import pandas as pd
import pytest

from urban_growth.census_threshold import (
    classify_threshold_measurement_band,
    entry_delay_interval,
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

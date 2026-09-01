import pandas as pd
import pytest

from urban_growth.forecast_availability import (
    apply_forecast_availability_gate,
    point_in_time_forecast_sample,
)
from urban_growth.io import SourceSchemaError


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": ["A", "B"],
            "period_start": ["2000-01-01", "2000-01-01"],
            "period_end": ["2005-01-01", "2005-01-01"],
            "predictor_available_date": ["1999-12-01", "2000-06-01"],
            "concordance_available_date": ["1999-11-01", "1999-11-01"],
        }
    )


def test_availability_gate_blocks_post_origin_predictor() -> None:
    result = apply_forecast_availability_gate(_panel())
    assert bool(result.loc[0, "point_in_time_available"])
    assert not bool(result.loc[1, "point_in_time_available"])
    assert result.loc[1, "availability_exclusion_reason"] == "predictor_not_available_at_origin"


def test_availability_gate_blocks_post_origin_concordance() -> None:
    frame = _panel().iloc[[0]].copy()
    frame["concordance_available_date"] = "2001-01-01"
    result = apply_forecast_availability_gate(frame)
    assert not bool(result.loc[0, "point_in_time_available"])
    assert result.loc[0, "availability_exclusion_reason"] == "concordance_not_available_at_origin"


def test_availability_gate_requires_known_dates() -> None:
    frame = _panel().iloc[[0]].copy()
    frame["predictor_available_date"] = None
    with pytest.raises(SourceSchemaError, match="must be known"):
        apply_forecast_availability_gate(frame)


def test_point_in_time_sample_cannot_reintroduce_late_rows() -> None:
    result = apply_forecast_availability_gate(_panel())
    sample = point_in_time_forecast_sample(result)
    assert sample["city_id"].tolist() == ["A"]

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
            "period_start": [2000, 2000],
            "period_end": [2005, 2005],
            "forecast_origin_date": ["2000-01-01", "2000-01-01"],
            "predictor_available_date": ["1999-12-01", "2000-06-01"],
            "concordance_available_date": ["1999-11-01", "1999-11-01"],
            "predictor_availability_source": ["official statistical release", "official statistical release"],
            "concordance_availability_source": ["official geography release", "official geography release"],
        }
    )


def test_availability_gate_blocks_post_origin_predictor() -> None:
    result = apply_forecast_availability_gate(_panel())
    assert bool(result.loc[0, "point_in_time_available"])
    assert not bool(result.loc[1, "point_in_time_available"])
    assert result.loc[1, "availability_exclusion_reason"] == "predictor_not_available_at_origin"
    assert result["availability_provenance_verified"].all()


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


def test_availability_gate_requires_predictor_provenance() -> None:
    frame = _panel().iloc[[0]].copy()
    frame["predictor_availability_source"] = "  "
    with pytest.raises(SourceSchemaError, match="source evidence"):
        apply_forecast_availability_gate(frame)


def test_availability_gate_requires_concordance_provenance() -> None:
    frame = _panel().iloc[[0]].drop(columns="concordance_availability_source")
    with pytest.raises(SourceSchemaError, match="concordance_availability_source"):
        apply_forecast_availability_gate(frame)


def test_integer_period_start_is_not_used_as_timestamp() -> None:
    frame = _panel().iloc[[0]].drop(columns=["forecast_origin_date"])
    with pytest.raises(SourceSchemaError, match="forecast_origin_date"):
        apply_forecast_availability_gate(frame)


def test_explicit_origin_column_can_be_overridden() -> None:
    frame = _panel().iloc[[0]].rename(columns={"forecast_origin_date": "as_of_date"})
    result = apply_forecast_availability_gate(frame, origin_column="as_of_date")
    assert bool(result.loc[0, "point_in_time_available"])


def test_point_in_time_sample_cannot_reintroduce_late_rows() -> None:
    result = apply_forecast_availability_gate(_panel())
    sample = point_in_time_forecast_sample(result)
    assert sample["city_id"].tolist() == ["A"]


def test_point_in_time_sample_rejects_unverified_provenance_flag() -> None:
    result = apply_forecast_availability_gate(_panel())
    result["availability_provenance_verified"] = False
    with pytest.raises(SourceSchemaError, match="verified availability provenance"):
        point_in_time_forecast_sample(result)

import pandas as pd
import pytest

from urban_growth.forecast_integrity import recompute_point_in_time_evidence
from urban_growth.io import SourceSchemaError


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": ["A", "B"],
            "period_start": [2000, 2000],
            "period_end": [2005, 2005],
            "forecast_origin_date": ["2000-12-31", "2000-12-31"],
            "forecast_origin_registration": [
                "annual December 31 as-of",
                "annual December 31 as-of",
            ],
            "predictor_available_date": ["2000-01-01", "2000-01-01"],
            "concordance_available_date": ["2000-01-01", "2000-01-01"],
            "predictor_availability_source": ["official predictor release", "official predictor release"],
            "concordance_availability_source": ["official geography release", "official geography release"],
            "point_in_time_available": [True, True],
            "availability_provenance_verified": [True, True],
            "forecast_origin_registration_verified": [True, True],
        }
    )


def test_recompute_accepts_matching_derived_flags() -> None:
    result = recompute_point_in_time_evidence(_panel())
    assert result["point_in_time_evidence_recomputed"].all()
    assert result["derived_point_in_time_flags_reconciled"].all()


def test_recompute_rejects_forged_available_flag() -> None:
    panel = _panel()
    panel.loc[0, "predictor_available_date"] = "2001-01-01"
    with pytest.raises(SourceSchemaError, match="point_in_time_available disagrees"):
        recompute_point_in_time_evidence(panel)


def test_recompute_rejects_forged_provenance_flag() -> None:
    panel = _panel()
    panel.loc[0, "predictor_availability_source"] = " "
    with pytest.raises(SourceSchemaError, match="source evidence"):
        recompute_point_in_time_evidence(panel)


def test_recompute_requires_raw_origin_registration() -> None:
    panel = _panel().drop(columns="forecast_origin_registration")
    with pytest.raises(SourceSchemaError, match="forecast_origin_registration"):
        recompute_point_in_time_evidence(panel)


def test_recompute_rejects_inconsistent_origin_calendar_rule() -> None:
    panel = _panel()
    extra = panel.iloc[[0]].copy()
    extra["city_id"] = "C"
    extra["period_start"] = 2005
    extra["period_end"] = 2010
    extra["forecast_origin_date"] = "2005-06-30"
    extra["predictor_available_date"] = "2005-01-01"
    extra["concordance_available_date"] = "2005-01-01"
    frame = pd.concat([panel, extra], ignore_index=True)
    with pytest.raises(SourceSchemaError, match="one registered month-day rule"):
        recompute_point_in_time_evidence(frame)

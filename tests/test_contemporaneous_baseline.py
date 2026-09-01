import pandas as pd
import pytest

from urban_growth.contemporaneous_baseline import (
    attach_contemporaneous_country_recent_growth,
    evaluate_contemporaneous_country_baseline,
)
from urban_growth.io import SourceSchemaError


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": [1, 2, 3, 4],
            "country_code": ["A", "A", "B", "C"],
            "period_start": [2000, 2000, 2000, 2000],
            "recent_growth": [0.01, 0.03, 0.02, 0.04],
            "future_growth": [0.02, 0.01, 0.025, 0.03],
        }
    )


def test_contemporaneous_country_baseline_is_leave_city_out() -> None:
    result = attach_contemporaneous_country_recent_growth(_panel())
    pred = result.set_index("city_id")[
        "country_contemporaneous_recent_growth_leave_city_out"
    ]
    assert pred.loc[1] == pytest.approx(0.03)
    assert pred.loc[2] == pytest.approx(0.01)
    # Singleton countries fall back to the global mean excluding the focal city.
    assert pred.loc[3] == pytest.approx((0.01 + 0.03 + 0.04) / 3)
    assert pred.loc[4] == pytest.approx((0.01 + 0.03 + 0.02) / 3)
    assert result.set_index("city_id").loc[1, "contemporaneous_country_peer_count"] == 1
    assert result.set_index("city_id").loc[3, "contemporaneous_country_fallback_global_loo"]
    assert not result["contemporaneous_country_uses_future_outcome"].any()


def test_contemporaneous_country_baseline_does_not_depend_on_future_growth() -> None:
    original = attach_contemporaneous_country_recent_growth(_panel())
    changed = _panel()
    changed["future_growth"] = [9.0, -3.0, 7.0, 12.0]
    rerun = attach_contemporaneous_country_recent_growth(changed)
    column = "country_contemporaneous_recent_growth_leave_city_out"
    assert rerun[column].tolist() == pytest.approx(original[column].tolist())


def test_contemporaneous_country_evaluation_reports_same_rows() -> None:
    result = evaluate_contemporaneous_country_baseline(_panel())
    assert result.loc[0, "origin"] == 2000
    assert result.loc[0, "n"] == 4
    assert result.loc[0, "comparator_information_time"] == "forecast_origin"
    assert bool(result.loc[0, "comparator_leave_city_out"])


def test_contemporaneous_country_baseline_requires_two_cities_per_origin() -> None:
    one = _panel().iloc[[0]].copy()
    with pytest.raises(SourceSchemaError, match="at least two cities"):
        attach_contemporaneous_country_recent_growth(one)

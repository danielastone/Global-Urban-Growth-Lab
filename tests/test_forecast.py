import pandas as pd
import pytest

from urban_growth.forecast import build_forecast_intervals, rolling_origin_splits, score_forecast
from urban_growth.io import SourceSchemaError


def test_rolling_origin_prevents_future_outcomes_in_training() -> None:
    panel = pd.DataFrame(
        {"period_start": [1995, 2000, 2005], "period_end": [2000, 2005, 2010]}
    )
    origin, train, test = next(rolling_origin_splits(panel, [2005]))
    assert origin == 2005
    assert train.tolist() == [0, 1]
    assert test.tolist() == [2]


def test_score_forecast_uses_matched_rows() -> None:
    actual = pd.Series([0.01, -0.02, None])
    predicted = pd.Series([0.02, -0.01, 0.5])
    metrics = score_forecast(actual, predicted)
    assert metrics.n == 2
    assert metrics.mae == pytest.approx(0.01)
    assert metrics.bias == pytest.approx(0.01)
    assert metrics.directional_accuracy == 1.0


def city_year_source() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": [1, 1, 1, 1], "year": [2015, 2020, 2025, 2030],
            "population": [80_000, 90_000, 100_000, 120_000],
            "observation_type": ["estimate", "estimate", "estimate", "projection"],
            "ISO3_Code": ["EXP"] * 4, "City_Name": ["Example"] * 4,
            "built_up_share_of_land": [0.2, 0.3, 0.4, 0.9],
            "population_density_per_km2": [1_000, 1_100, 1_200, 1_300],
        }
    )


def test_forecast_intervals_use_only_origin_predictors() -> None:
    result = build_forecast_intervals(city_year_source(), [2020])
    assert result["period_end"].tolist() == [2025]
    assert result["built_up_share_at_origin"].tolist() == [0.3]
    assert result["population_density_at_origin"].tolist() == [1_100]
    assert result["outcome_observation_type"].tolist() == ["estimate"]


def test_forecast_intervals_exclude_projection_outcomes_by_default() -> None:
    with pytest.raises(SourceSchemaError, match="No complete"):
        build_forecast_intervals(city_year_source(), [2025])
    result = build_forecast_intervals(
        city_year_source(), [2025], allowed_outcome_types={"projection"}
    )
    assert result["period_end"].tolist() == [2030]
    assert result["outcome_observation_type"].tolist() == ["projection"]


def test_forecast_intervals_require_exact_lag_year() -> None:
    source = city_year_source().loc[lambda x: x.year.ne(2015)]
    with pytest.raises(SourceSchemaError, match="No complete"):
        build_forecast_intervals(source, [2020])

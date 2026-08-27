import pandas as pd
import pytest

from urban_growth.forecast import (
    baseline_predictions,
    build_forecast_intervals,
    evaluate_rolling_baselines,
    paired_error_comparison,
    rolling_baseline_errors,
    rolling_origin_splits,
    score_forecast,
)
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


def test_baselines_use_training_country_mean_and_global_fallback() -> None:
    train = pd.DataFrame(
        {"country_code": ["A", "A", "B"], "future_growth": [0.01, 0.03, -0.01]}
    )
    test = pd.DataFrame(
        {"country_code": ["A", "C"], "recent_growth": [0.04, -0.02]}, index=[10, 11]
    )
    result = baseline_predictions(train, test)
    assert result["country_mean"].tolist() == pytest.approx([0.02, 0.01])
    assert result["global_mean"].tolist() == pytest.approx([0.01, 0.01])
    assert result["persistence"].tolist() == [0.04, -0.02]


def test_rolling_baselines_use_identical_test_rows() -> None:
    panel = pd.DataFrame(
        {
            "period_start": [2000, 2000, 2005, 2005],
            "period_end": [2005, 2005, 2010, 2010],
            "country_code": ["A", "B", "A", "B"],
            "future_growth": [0.01, -0.01, 0.02, -0.02],
            "recent_growth": [0.00, 0.00, 0.01, -0.01],
        }
    )
    result = evaluate_rolling_baselines(panel, [2005])
    assert set(result["model"]) == {"zero_growth", "global_mean", "country_mean", "persistence"}
    assert result["n"].unique().tolist() == [2]


def test_row_errors_support_paired_size_comparison() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 2, 1, 2],
            "period_start": [2000, 2000, 2005, 2005],
            "period_end": [2005, 2005, 2010, 2010],
            "country_code": ["A", "B", "A", "B"],
            "population_start": [100_000, 2_000_000, 110_000, 2_100_000],
            "future_growth": [0.01, -0.01, 0.02, -0.02],
            "recent_growth": [0.00, 0.00, 0.01, -0.01],
        }
    )
    errors = rolling_baseline_errors(panel, [2005])
    result = paired_error_comparison(errors)
    assert set(result["size_bin"].astype(str)) == {"50–150k", "2m+"}
    assert result["n"].tolist() == [1, 1]

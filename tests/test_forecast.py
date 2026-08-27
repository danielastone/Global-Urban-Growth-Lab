import pandas as pd
import pytest

from urban_growth.forecast import rolling_origin_splits, score_forecast


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

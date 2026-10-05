import pandas as pd
import pytest

from urban_growth.h1_information import evaluate_country_adjusted_recent_growth_information
from urban_growth.io import SourceSchemaError


def _panel() -> pd.DataFrame:
    rows = []
    for origin in [2000, 2005, 2010]:
        for city_id, country, recent, future in [
            (1, "A", 0.01 + (origin - 2000) / 1000, 0.012 + (origin - 2000) / 1000),
            (2, "A", 0.03 + (origin - 2000) / 1000, 0.028 + (origin - 2000) / 1000),
            (3, "B", -0.01, -0.008),
            (4, "B", 0.01, 0.012),
        ]:
            rows.append(
                {
                    "city_id": city_id,
                    "country_code": country,
                    "period_start": origin,
                    "period_end": origin + 5,
                    "recent_growth": recent,
                    "future_growth": future,
                }
            )
    return pd.DataFrame(rows)


def test_incremental_recent_growth_scores_nested_models_on_same_rows() -> None:
    result = evaluate_country_adjusted_recent_growth_information(_panel(), [2005, 2010])
    assert result["origin"].tolist() == [2005, 2010]
    assert result["n"].tolist() == [4, 4]
    assert result["test_rows_identical_across_nested_models"].all()
    assert result["training_precedes_origin"].all()
    assert result["comparison"].eq(
        "country_loo_only_vs_country_loo_plus_recent_growth"
    ).all()


def test_incremental_recent_growth_can_show_predictive_gain() -> None:
    result = evaluate_country_adjusted_recent_growth_information(_panel(), [2005, 2010])
    assert result["recent_growth_beta_within_country"].gt(0).all()
    assert result["recent_growth_improves_mae"].all()
    assert result["recent_growth_improves_rmse"].all()
    assert result["mae_delta_recent_minus_country"].lt(0).all()
    assert result["rmse_delta_recent_minus_country"].lt(0).all()


def test_incremental_recent_growth_rejects_duplicate_city_intervals() -> None:
    panel = pd.concat([_panel(), _panel().iloc[[0]]], ignore_index=True)
    with pytest.raises(SourceSchemaError, match="duplicate"):
        evaluate_country_adjusted_recent_growth_information(panel, [2005, 2010])


def test_incremental_recent_growth_requires_unique_origins() -> None:
    with pytest.raises(SourceSchemaError, match="unique and non-empty"):
        evaluate_country_adjusted_recent_growth_information(_panel(), [2005, 2005])

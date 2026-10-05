import pandas as pd
import pytest

from urban_growth.contemporaneous_baseline import (
    attach_contemporaneous_country_recent_growth,
    evaluate_contemporaneous_country_baseline,
    evaluate_contemporaneous_country_h1_hierarchy,
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
    pred = result.set_index("city_id")["country_contemporaneous_recent_growth_leave_city_out"]
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


def test_h1_hierarchy_reports_every_model_and_weighting_on_matched_rows() -> None:
    rows = []
    for origin in [1990, 1995, 2000]:
        for city_id, country, recent in [
            (1, "A", 0.01),
            (2, "A", 0.03),
            (3, "B", 0.02),
            (4, "B", 0.04),
        ]:
            rows.append(
                {
                    "city_id": city_id,
                    "country_code": country,
                    "period_start": origin,
                    "period_end": origin + 5,
                    "recent_growth": recent + (origin - 1990) / 1000,
                    "future_growth": 0.5 * recent + (0.005 if country == "A" else 0.01),
                }
            )
    result = evaluate_contemporaneous_country_h1_hierarchy(pd.DataFrame(rows), [2000])
    assert set(result["weighting"]) == {"row_weighted", "country_balanced"}
    assert set(result["model"]) == {
        "contemporaneous_country_only",
        "contemporaneous_country_plus_city_deviation",
        "historical_country_loo_only",
        "historical_country_loo_plus_recent_growth",
    }
    assert result["n"].eq(4).all()
    assert result["country_count"].eq(2).all()
    assert result["test_rows_identical_across_models"].all()
    assert result["training_precedes_origin"].all()
    assert not result["contemporaneous_country_uses_future_outcome"].any()
    assert result.groupby("weighting")["mae_winner"].sum().eq(1).all()


def test_h1_hierarchy_country_balancing_changes_unequal_country_fit() -> None:
    rows = []
    specifications = {
        1990: [(1, "A", 0.00), (2, "A", 0.01), (3, "A", 0.02), (4, "B", 0.10), (5, "B", 0.20)],
        1995: [(1, "A", 0.01), (2, "A", 0.02), (3, "A", 0.03), (4, "B", 0.20), (5, "B", 0.40)],
        2000: [(1, "A", 0.02), (2, "A", 0.03), (3, "A", 0.04), (4, "B", 0.30), (5, "B", 0.60)],
    }
    for origin, cities in specifications.items():
        for city_id, country, recent in cities:
            slope = 0.2 if country == "A" else 1.5
            rows.append(
                {
                    "city_id": city_id,
                    "country_code": country,
                    "period_start": origin,
                    "period_end": origin + 5,
                    "recent_growth": recent,
                    "future_growth": slope * recent,
                }
            )
    result = evaluate_contemporaneous_country_h1_hierarchy(pd.DataFrame(rows), [2000])
    augmented = result.loc[
        result["model"].eq("contemporaneous_country_plus_city_deviation")
    ].set_index("weighting")
    assert augmented.loc["row_weighted", "beta"] != pytest.approx(
        augmented.loc["country_balanced", "beta"]
    )

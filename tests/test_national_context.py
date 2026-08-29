import numpy as np
import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.national_context import attach_national_context


def national_panel() -> pd.DataFrame:
    rows = []
    values = {
        2000: {"city": 500.0, "town_and_semi_dense": 250.0, "rural": 150.0},
        2005: {"city": 600.0, "town_and_semi_dense": 260.0, "rural": 140.0},
        # This deliberately extreme future value must never enter an origin-2005 control.
        2010: {"city": 900_000.0, "town_and_semi_dense": 1.0, "rural": 1.0},
    }
    for year, categories in values.items():
        for category, population in categories.items():
            rows.append(
                {
                    "country_code": "X",
                    "year": year,
                    "category": category,
                    "population": population,
                }
            )
    return pd.DataFrame(rows)


def intervals() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": ["A"],
            "country_code": ["X"],
            "period_start": [2005],
            "period_end": [2010],
            "population_lag": [90.0],
            "population_start": [100.0],
        }
    )


def test_context_is_leave_one_city_out_and_origin_available() -> None:
    result = attach_national_context(intervals(), national_panel())
    row = result.iloc[0]

    assert row["national_population_loo_at_origin"] == pytest.approx(900.0)
    assert row["log_national_population_loo_at_origin"] == pytest.approx(np.log(900.0))
    assert row["national_population_recent_growth_loo"] == pytest.approx(
        (np.log(900.0) - np.log(810.0)) / 5
    )
    assert row["national_city_share_loo_at_origin"] == pytest.approx(500.0 / 900.0)
    assert row["national_town_share_loo_at_origin"] == pytest.approx(260.0 / 900.0)
    assert row["national_rural_share_loo_at_origin"] == pytest.approx(140.0 / 900.0)
    assert not row["national_context_uses_future_value"]
    assert row["national_context_leave_one_city_out"]


def test_compositional_invariants_hold() -> None:
    result = attach_national_context(intervals(), national_panel())
    shares = result.filter(regex=r"national_(city|town|rural)_share_loo_at_origin$")
    changes = result.filter(regex=r"national_(city|town|rural)_share_change_loo$")

    assert shares.sum(axis=1).iloc[0] == pytest.approx(1.0)
    assert changes.sum(axis=1).iloc[0] == pytest.approx(0.0)


def test_incomplete_composition_fails() -> None:
    source = national_panel()
    source = source.loc[~((source["year"] == 2005) & (source["category"] == "rural"))]
    with pytest.raises(SourceSchemaError, match="requires city"):
        attach_national_context(intervals(), source)


def test_focal_city_larger_than_national_city_category_fails() -> None:
    frame = intervals()
    frame["population_start"] = 700.0
    with pytest.raises(SourceSchemaError, match="exceeds"):
        attach_national_context(frame, national_panel())


def test_zero_residual_country_is_flagged_without_dropping_row() -> None:
    source = national_panel()
    source.loc[source["category"] != "city", "population"] = 0.0
    source.loc[source["year"] == 2000, "population"] = source.loc[
        source["year"] == 2000, "category"
    ].map({"city": 90.0, "town_and_semi_dense": 0.0, "rural": 0.0})
    source.loc[source["year"] == 2005, "population"] = source.loc[
        source["year"] == 2005, "category"
    ].map({"city": 100.0, "town_and_semi_dense": 0.0, "rural": 0.0})

    result = attach_national_context(intervals(), source)
    assert len(result) == 1
    assert not result.loc[0, "national_context_loo_available"]
    assert np.isnan(result.loc[0, "national_city_share_loo_at_origin"])

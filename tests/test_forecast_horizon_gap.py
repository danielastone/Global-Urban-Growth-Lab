from __future__ import annotations

import pandas as pd
import pytest

from urban_growth.forecast_fitness import fitness_gated_forecast_panel
from urban_growth.io import SourceSchemaError


def base_panel() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "city_id": "A",
                "country_code": "AAA",
                "period_start": 2000,
                "period_end": 2010,
                "outcome_start_year": 2005,
                "outcome_gap_years": 5,
                "recent_growth": 0.01,
                "future_growth": 0.02,
                "growth_eligible": True,
            }
        ]
    )


def test_horizon_excludes_pre_outcome_gap() -> None:
    result = fitness_gated_forecast_panel(base_panel())
    assert result.loc[0, "forecast_horizon_years"] == pytest.approx(5.0)


def test_outcome_gap_can_derive_horizon_without_outcome_start_year() -> None:
    panel = base_panel().drop(columns="outcome_start_year")
    result = fitness_gated_forecast_panel(panel)
    assert result.loc[0, "forecast_horizon_years"] == pytest.approx(5.0)


def test_explicit_horizon_must_match_declared_outcome_interval() -> None:
    panel = base_panel()
    panel["forecast_horizon_years"] = 10
    with pytest.raises(SourceSchemaError, match="disagrees with the declared outcome interval"):
        fitness_gated_forecast_panel(panel)


def test_explicit_matching_horizon_is_retained() -> None:
    panel = base_panel()
    panel["forecast_horizon_years"] = 5
    result = fitness_gated_forecast_panel(panel)
    assert result.loc[0, "forecast_horizon_years"] == pytest.approx(5.0)

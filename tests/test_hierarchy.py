import numpy as np
import pandas as pd
import pytest

from urban_growth.hierarchy import assign_origin_tiers, fixed_membership_ilr_balance
from urban_growth.io import SourceSchemaError


def test_origin_tiers_do_not_use_endpoint_population() -> None:
    frame = pd.DataFrame(
        {
            "city_id": ["a", "b", "c"],
            "country_code": ["X"] * 3,
            "period_start": [2000] * 3,
            "population_start": [1_000_000, 200_000, 40_000],
            "population_end": [10_000, 300_000, 2_000_000],
        }
    )
    result = assign_origin_tiers(frame)
    assert result["rank_origin"].tolist() == [1, 2, 3]
    assert result["tier_abs_origin"].astype(str).tolist() == ["1m+", "100-250k", "<50k"]
    assert result["tier_assignment_timing"].eq("forecast_origin_fixed").all()


def test_origin_rank_ties_break_on_stable_city_id() -> None:
    frame = pd.DataFrame(
        {
            "city_id": ["b", "a"],
            "country_code": ["X", "X"],
            "period_start": [2000, 2000],
            "population_start": [100_000, 100_000],
        }
    )
    result = assign_origin_tiers(frame).set_index("city_id")
    assert result.loc["a", "rank_origin"] == 1
    assert result.loc["b", "rank_origin"] == 2


def test_ilr_uses_fixed_membership_and_reports_empty_cells() -> None:
    frame = pd.DataFrame(
        {
            "country_code": ["X", "X"],
            "period_start": [2000, 2000],
            "tier": pd.Categorical(["large", "small"], categories=["large", "small"], ordered=True),
            "population_start": [100.0, 100.0],
            "population_end": [200.0, 100.0],
        }
    )
    result = fixed_membership_ilr_balance(frame, tier_column="tier")
    assert result.loc[0, "tier_ilr_change"] == pytest.approx(np.log(2) / np.sqrt(2))
    assert bool(result.loc[0, "ilr_eligible"])

    sparse = frame.loc[frame["tier"] == "large"]
    result = fixed_membership_ilr_balance(sparse, tier_column="tier")
    assert not bool(result.loc[0, "ilr_eligible"])
    assert result.loc[0, "exclusion_reason"] == "empty_origin_fixed_tier_cell"


def test_ilr_rejects_unordered_tier() -> None:
    frame = pd.DataFrame(
        {
            "country_code": ["X"],
            "period_start": [2000],
            "tier": ["large"],
            "population_start": [100.0],
            "population_end": [110.0],
        }
    )
    with pytest.raises(SourceSchemaError, match="ordered categorical"):
        fixed_membership_ilr_balance(frame, tier_column="tier")

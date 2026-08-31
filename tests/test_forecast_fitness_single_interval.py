import pandas as pd
import pytest

from urban_growth.forecast_fitness import evaluate_fitness_gated_persistence_baselines
from urban_growth.io import SourceSchemaError


def test_single_interval_census_like_panel_is_not_mislabeled_oos() -> None:
    panel = pd.DataFrame(
        [
            {
                "city_id": "US_PLACE_2010_0100001",
                "country_code": "USA",
                "period_start": 2010,
                "period_end": 2020,
                "population_start": 40_000,
                "recent_growth": 0.01,
                "future_growth": 0.02,
                "growth_eligible": True,
            }
        ]
    )
    with pytest.raises(SourceSchemaError):
        evaluate_fitness_gated_persistence_baselines(panel, [2010])

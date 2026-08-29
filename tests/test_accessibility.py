import pandas as pd
import pytest

from urban_growth.accessibility import mutually_exclusive_rival_mass
from urban_growth.io import SourceSchemaError


def test_rival_mass_bands_are_mutually_exclusive() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"] * 5,
            "rival_city_id": ["b", "c", "d", "e", "f"],
            "travel_time_hours": [0.5, 1.0, 1.99, 2.0, 7.99],
            "rival_population": [10, 20, 30, 40, 50],
        }
    )
    result = mutually_exclusive_rival_mass(pairs, nominal_vintage=2015).iloc[0]
    assert result["rival_mass_0_1h"] == 10
    assert result["rival_mass_1_2h"] == 50
    assert result["rival_mass_2_4h"] == 40
    assert result["rival_mass_4_8h"] == 50


def test_accessibility_rejects_historical_vintage() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )
    with pytest.raises(SourceSchemaError, match="modern validation"):
        mutually_exclusive_rival_mass(pairs, nominal_vintage=1990)

import numpy as np
import pandas as pd
import pytest

from urban_growth.accessibility import (
    border_conditioned_rival_mass,
    continuous_rival_mass,
    mutually_exclusive_rival_mass,
    travel_time_threshold_diagnostics,
)
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


def test_continuous_rival_mass_uses_exponential_decay_and_cutoff() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a", "a", "b"],
            "rival_city_id": ["b", "c", "a"],
            "travel_time_hours": [0.0, 1.0, 9.0],
            "rival_population": [100.0, 100.0, 500.0],
        }
    )

    result = continuous_rival_mass(
        pairs,
        nominal_vintage=2015,
        decay_scale_hours=1.0,
        max_time_hours=8.0,
    ).set_index("focal_city_id")

    assert result.loc["a", "rival_mass_exponential"] == pytest.approx(100 + 100 / np.e)
    assert result.loc["b", "rival_mass_exponential"] == 0
    assert result.loc["a", "exposure_definition"] == (
        "exponential_decay_border_neutral_or_registered_input"
    )


@pytest.mark.parametrize(
    ("parameter", "value", "message"),
    [
        ("decay_scale_hours", 0.0, "decay_scale_hours"),
        ("max_time_hours", 0.0, "max_time_hours"),
    ],
)
def test_continuous_rival_mass_rejects_nonpositive_parameters(
    parameter: str, value: float, message: str
) -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )
    kwargs = {parameter: value}
    with pytest.raises(SourceSchemaError, match=message):
        continuous_rival_mass(pairs, nominal_vintage=2015, **kwargs)


def test_threshold_diagnostics_quantify_pair_and_mass_exposure() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"] * 5,
            "rival_city_id": ["b", "c", "d", "e", "f"],
            "travel_time_hours": [0.75, 0.9, 1.1, 2.2, 4.0],
            "rival_population": [10, 20, 30, 40, 100],
        }
    )

    result = travel_time_threshold_diagnostics(
        pairs,
        nominal_vintage=2015,
        tolerance_minutes=6,
    ).set_index("threshold_hours")

    assert result.loc[1.0, "pair_count_near_threshold"] == 2
    assert result.loc[1.0, "pair_share_near_threshold"] == pytest.approx(2 / 5)
    assert result.loc[1.0, "rival_mass_near_threshold"] == 50
    assert result.loc[1.0, "rival_mass_share_near_threshold"] == pytest.approx(50 / 200)
    assert result.loc[2.0, "pair_count_near_threshold"] == 0
    assert result.loc[4.0, "pair_count_near_threshold"] == 1
    assert result.loc[4.0, "rival_mass_near_threshold"] == 100


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"tolerance_minutes": 0}, "tolerance_minutes"),
        ({"tolerance_minutes": 10, "thresholds_hours": ()}, "At least one"),
        ({"tolerance_minutes": 10, "thresholds_hours": (1.0, 1.0)}, "unique"),
        ({"tolerance_minutes": 10, "thresholds_hours": (0.0,)}, "positive"),
    ],
)
def test_threshold_diagnostics_fail_closed(kwargs: dict[str, object], message: str) -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )

    with pytest.raises(SourceSchemaError, match=message):
        travel_time_threshold_diagnostics(pairs, nominal_vintage=2015, **kwargs)


def test_border_conditioned_mass_splits_each_band() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"] * 5 + ["g", "g"],
            "rival_city_id": ["b", "c", "d", "e", "f", "a", "c"],
            "travel_time_hours": [0.5, 1.0, 1.99, 2.0, 7.99, 0.25, 4.0],
            "rival_population": [10, 20, 30, 40, 50, 60, 70],
        }
    )
    lookup = pd.DataFrame(
        {
            "city_id": ["a", "b", "c", "d", "e", "f", "g"],
            "country_code": ["AA", "AA", "BB", "AA", "BB", "AA", "BB"],
        }
    )

    result = border_conditioned_rival_mass(pairs, lookup, nominal_vintage=2015)
    focal_a = result.loc[result["focal_city_id"] == "a"].iloc[0]

    assert focal_a["rival_mass_0_1h_same_country"] == 10
    assert focal_a["rival_mass_0_1h_cross_border"] == 0
    assert focal_a["rival_mass_1_2h_same_country"] == 30
    assert focal_a["rival_mass_1_2h_cross_border"] == 20
    assert focal_a["rival_mass_2_4h_same_country"] == 0
    assert focal_a["rival_mass_2_4h_cross_border"] == 40
    assert focal_a["rival_mass_4_8h_same_country"] == 50
    assert focal_a["rival_mass_4_8h_cross_border"] == 0
    assert focal_a["border_definition"] == "country_code_equality"

    for lower, upper in ((0, 1), (1, 2), (2, 4), (4, 8)):
        total = f"rival_mass_{lower}_{upper}h"
        pd.testing.assert_series_equal(
            result[f"{total}_same_country"] + result[f"{total}_cross_border"],
            result[total],
            check_dtype=False,
            check_names=False,
        )


@pytest.mark.parametrize("invalid_code", [None, "", " AA "])
def test_border_conditioned_mass_rejects_invalid_country_codes(invalid_code: object) -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )
    lookup = pd.DataFrame(
        {"city_id": ["a", "b"], "country_code": ["AA", invalid_code]}
    )

    with pytest.raises(SourceSchemaError, match="country code"):
        border_conditioned_rival_mass(pairs, lookup, nominal_vintage=2015)


def test_border_conditioned_mass_rejects_duplicate_lookup_ids() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )
    lookup = pd.DataFrame(
        {"city_id": ["a", "b", "b"], "country_code": ["AA", "AA", "BB"]}
    )

    with pytest.raises(SourceSchemaError, match="unique city IDs"):
        border_conditioned_rival_mass(pairs, lookup, nominal_vintage=2015)


def test_border_conditioned_mass_rejects_unmatched_cities() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )
    lookup = pd.DataFrame({"city_id": ["a"], "country_code": ["AA"]})

    with pytest.raises(SourceSchemaError, match="Every focal and rival city"):
        border_conditioned_rival_mass(pairs, lookup, nominal_vintage=2015)


def test_border_conditioned_mass_reuses_vintage_validation() -> None:
    pairs = pd.DataFrame(
        {
            "focal_city_id": ["a"],
            "rival_city_id": ["b"],
            "travel_time_hours": [1.0],
            "rival_population": [10],
        }
    )
    lookup = pd.DataFrame(
        {"city_id": ["a", "b"], "country_code": ["AA", "BB"]}
    )

    with pytest.raises(SourceSchemaError, match="modern validation"):
        border_conditioned_rival_mass(pairs, lookup, nominal_vintage=1990)

import pandas as pd
import pytest

from urban_growth.forecast import build_forecast_intervals
from urban_growth.io import SourceSchemaError
from urban_growth.wup_lineage import classify_wup_city_population_lineage


def test_wup_lineage_separates_reference_estimates_from_crisp_values() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 1, 1, 1, 1],
            "year": [1970, 1975, 2020, 2021, 2025],
            "population": [40_000, 45_000, 60_000, 61_000, 65_000],
            "observation_type": ["estimate"] * 5,
        }
    )
    result = classify_wup_city_population_lineage(panel)
    assert result.set_index("year")["empirical_lineage_type"].to_dict() == {
        1970: "historical_backcast",
        1975: "reference_estimate",
        2020: "reference_estimate",
        2021: "crisp_projection",
        2025: "crisp_projection",
    }
    assert result.loc[result["year"].eq(2025), "publisher_observation_type"].item() == "estimate"
    assert result.loc[result["year"].eq(2021), "observation_type"].item() == "projection"
    assert not result.loc[result["year"].eq(2025), "empirical_outcome_reference_estimate"].item()


def test_default_forecast_gate_excludes_2020_to_2025_crisp_outcome() -> None:
    rows = []
    for year, population in [(2015, 50_000), (2020, 55_000), (2025, 60_000)]:
        rows.append(
            {
                "city_id": 1,
                "year": year,
                "population": population,
                "observation_type": "estimate",
                "ISO3_Code": "AAA",
                "City_Name": "Example",
                "built_up_share_of_land": 0.5,
                "population_density_per_km2": 1_000,
            }
        )
    panel = classify_wup_city_population_lineage(pd.DataFrame(rows))
    with pytest.raises(SourceSchemaError, match="No complete forecast intervals"):
        build_forecast_intervals(panel, [2020])


def test_projection_sensitivity_requires_explicit_opt_in() -> None:
    rows = []
    for year, population in [(2015, 50_000), (2020, 55_000), (2025, 60_000)]:
        rows.append(
            {
                "city_id": 1,
                "year": year,
                "population": population,
                "observation_type": "estimate",
                "ISO3_Code": "AAA",
                "City_Name": "Example",
                "built_up_share_of_land": 0.5,
                "population_density_per_km2": 1_000,
            }
        )
    panel = classify_wup_city_population_lineage(pd.DataFrame(rows))
    intervals = build_forecast_intervals(
        panel,
        [2020],
        allowed_outcome_types={"estimate", "projection"},
    )
    assert intervals["period_start"].tolist() == [2020]
    assert intervals["outcome_observation_type"].tolist() == ["projection"]

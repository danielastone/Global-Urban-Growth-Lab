import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.wup_panel import build_wup_city_year_panel


def panels() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    population = pd.DataFrame(
        {
            "city_id": [1], "year": [2025], "population": [60_000],
            "observation_type": ["estimate"], "ISO3_Code": ["EXP"],
            "City_Name": ["Example"], "PWCent_Longitude": [10.0],
            "PWCent_Latitude": [20.0], "eligible_at_reference_year": [True],
            "sample_entry_year": [2025], "sample_exit_year": [2050],
            "threshold_observed": [True],
        }
    )
    area = pd.DataFrame({"city_id": [1], "year": [2025], "land_area_km2": [12.0]})
    built = pd.DataFrame(
        {
            "city_id": [1], "year": [2025],
            "built_up_area_m2_per_capita": [100.0], "reported_zero": [False],
        }
    )
    density = pd.DataFrame(
        {"city_id": [1], "year": [2025], "population_density_per_km2": [5_000.0]}
    )
    return population, area, built, density


def test_wup_panel_derives_built_area_and_share() -> None:
    result = build_wup_city_year_panel(*panels())
    assert result["built_up_area_m2"].tolist() == [6_000_000]
    assert result["built_up_share_of_land"].tolist() == [0.5]
    assert result["built_up_area_status"].tolist() == ["derived_f21_times_f30"]


def test_wup_panel_excludes_publisher_zero_from_derived_area() -> None:
    population, area, built, density = panels()
    built.loc[0, "built_up_area_m2_per_capita"] = 0
    built.loc[0, "reported_zero"] = True
    result = build_wup_city_year_panel(population, area, built, density)
    assert result["built_up_area_m2"].isna().all()
    assert result["built_up_area_status"].tolist() == ["publisher_zero_excluded"]


def test_wup_panel_rejects_coverage_loss() -> None:
    population, area, built, density = panels()
    with pytest.raises(SourceSchemaError, match="coverage differs"):
        build_wup_city_year_panel(population, area.iloc[0:0], built, density)


def test_wup_panel_rejects_built_area_over_land_area() -> None:
    population, area, built, density = panels()
    built.loc[0, "built_up_area_m2_per_capita"] = 300
    with pytest.raises(SourceSchemaError, match="exceeds land area"):
        build_wup_city_year_panel(population, area, built, density)

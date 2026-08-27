import pandas as pd
import pytest

from urban_growth.adapters.ghsl_ucdb import fixed_2025_theme_panel, indicator_panel
from urban_growth.adapters.wup import (
    city_area_panel,
    city_population_panel,
    degree_of_urbanization_panel,
)
from urban_growth.io import SourceSchemaError


def test_ghsl_indicator_preserves_boundary_mode() -> None:
    source = pd.DataFrame(
        {"ID": [1], "NAME": ["Example"], "MT_POP_TOT_1975": [100], "MT_POP_TOT_1980": [120]}
    )
    result = indicator_panel(
        source, city_id_column="ID", metadata_columns=["NAME"],
        indicator_pattern=r"MT_POP_TOT_(?P<year>\d{4})", value_name="population",
        boundary_product="ucdb_multitemporal_boundaries",
    )
    assert result["year"].tolist() == [1975, 1980]
    assert result["boundary_mode"].unique().tolist() == ["dynamic"]
    assert result["boundary_product"].unique().tolist() == ["ucdb_multitemporal_boundaries"]


def test_ghsl_fixed_theme_uses_fixed_2025_boundary_and_joins_measures() -> None:
    source = pd.DataFrame(
        {
            "ID_UC_G0": [1],
            "GC_UCN_MAI_2025": ["Apia"],
            "GC_CNT_GAD_2025": ["Samoa"],
            "GH_POP_TOT_1975": [10.5],
            "GH_POP_TOT_2025": [60_041.7],
            "GH_BUS_TOT_1975": [378],
            "GH_BUS_TOT_2025": [2_829],
        }
    )
    result = fixed_2025_theme_panel(source)
    assert result["year"].tolist() == [1975, 2025]
    assert result["boundary_mode"].unique().tolist() == ["fixed"]
    assert result["boundary_product"].unique().tolist() == ["ucdb_fixed_2025_boundary"]
    assert result["population"].tolist() == [10.5, 60_041.7]
    assert result["built_up_area_m2"].tolist() == [378, 2_829]


def test_ghsl_fixed_theme_rejects_non_numeric_measure() -> None:
    source = pd.DataFrame(
        {
            "ID_UC_G0": [1],
            "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": ["Exampleland"],
            "GH_POP_TOT_2025": ["not available"],
            "GH_BUS_TOT_2025": [100],
        }
    )
    with pytest.raises(SourceSchemaError, match="non-numeric population"):
        fixed_2025_theme_panel(source)


def test_wup_converts_thousands_and_requires_mapped_categories() -> None:
    source = pd.DataFrame({"Code": [1], "Class": ["city"], "1975": [2.5], "1980": [3.0]})
    result = degree_of_urbanization_panel(
        source, location_id_column="Code", category_column="Class"
    )
    assert result["population"].tolist() == [2500.0, 3000.0]

    source.loc[0, "Class"] = "publisher label not mapped"
    with pytest.raises(SourceSchemaError, match="Unmapped"):
        degree_of_urbanization_panel(source, location_id_column="Code", category_column="Class")


def test_wup_city_panel_preserves_prethreshold_history_and_marks_projections() -> None:
    source = pd.DataFrame(
        {
            "ID": [1, 2],
            "2000": [None, 55.0],
            "2025": [60.0, None],
            "2030": [65.0, 52.0],
        }
    )
    result = city_population_panel(source, city_id_column="ID")
    city1 = result[result["city_id"] == 1]
    city2 = result[result["city_id"] == 2]
    assert city1["population"].tolist() == [60_000, 65_000]
    assert city1["eligible_at_reference_year"].all()
    assert city1["sample_entry_year"].unique().tolist() == [2025]
    assert city2["eligible_at_reference_year"].eq(False).all()
    assert city2["sample_entry_year"].unique().tolist() == [2000]
    assert result["threshold_observed"].all()


def test_unregistered_ghsl_boundary_product_fails() -> None:
    source = pd.DataFrame({"ID": [1], "MT_POP_TOT_1975": [100]})
    with pytest.raises(SourceSchemaError, match="Unregistered"):
        indicator_panel(
            source, city_id_column="ID",
            indicator_pattern=r"MT_POP_TOT_(?P<year>\d{4})", value_name="population",
            boundary_product="caller_guess",
        )


def test_wup_area_panel_drops_threshold_blanks_and_requires_positive_area() -> None:
    source = pd.DataFrame({"ID": [1], "1975": [None], "2025": [12.0], "2050": [15.0]})
    result = city_area_panel(source, city_id_column="ID")
    assert result["year"].tolist() == [2025, 2050]
    assert result["land_area_km2"].tolist() == [12.0, 15.0]

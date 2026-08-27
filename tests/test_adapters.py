import pandas as pd
import pytest

from urban_growth.adapters.ghsl_ucdb import (
    fixed_2025_theme_panel,
    indicator_panel,
    multitemporal_boundary_panel,
    reconcile_2025_streams,
)
from urban_growth.adapters.wup import (
    city_area_panel,
    city_metric_panel,
    city_population_panel,
    degree_of_urbanization_panel,
    read_f01_country_city_population,
    validate_density_identity,
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
            "GC_UCA_KM2_2025": [35],
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
            "GC_UCA_KM2_2025": [12],
            "GH_POP_TOT_2025": ["not available"],
            "GH_BUS_TOT_2025": [100],
        }
    )
    with pytest.raises(SourceSchemaError, match="non-numeric population"):
        fixed_2025_theme_panel(source)


def test_ghsl_2025_stream_reconciliation_allows_population_rounding() -> None:
    fixed_source = pd.DataFrame(
        {
            "ID_UC_G0": [1], "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": ["Exampleland"], "GC_UCA_KM2_2025": [12],
            "GH_POP_TOT_2025": [50_100.49], "GH_BUS_TOT_2025": [2_500],
        }
    )
    dynamic_source = pd.DataFrame(
        {
            "ID_MTUC_G0": [1], "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": ["Exampleland"], "GC_UCB_YOB _2025": [2025],
            "GC_UCB_YOD _2025": [2030], "MT_POP_TOT_2025": [50_100],
            "MT_BUS_TOT_2025": [2_500], "MT_UCA_KM2_2025": [12],
        }
    )
    audit = reconcile_2025_streams(
        fixed_2025_theme_panel(fixed_source),
        multitemporal_boundary_panel(dynamic_source),
    )
    assert audit["population_difference"].tolist() == pytest.approx([0.49])
    assert audit["built_up_area_difference_m2"].tolist() == [0]


def test_ghsl_2025_stream_reconciliation_rejects_material_difference() -> None:
    fixed_source = pd.DataFrame(
        {
            "ID_UC_G0": [1], "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": ["Exampleland"], "GC_UCA_KM2_2025": [12],
            "GH_POP_TOT_2025": [50_102], "GH_BUS_TOT_2025": [2_500],
        }
    )
    dynamic_source = pd.DataFrame(
        {
            "ID_MTUC_G0": [1], "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": ["Exampleland"], "GC_UCB_YOB _2025": [2025],
            "GC_UCB_YOD _2025": [2030], "MT_POP_TOT_2025": [50_100],
            "MT_BUS_TOT_2025": [2_500], "MT_UCA_KM2_2025": [12],
        }
    )
    with pytest.raises(SourceSchemaError, match="rounding tolerance"):
        reconcile_2025_streams(
            fixed_2025_theme_panel(fixed_source),
            multitemporal_boundary_panel(dynamic_source),
        )


def test_ghsl_multitemporal_panel_respects_birth_year_and_parses_commas() -> None:
    source = pd.DataFrame(
        {
            "ID_MTUC_G0": [1],
            "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": ["Exampleland"],
            "GC_UCB_YOB _2025": [2020],
            "GC_UCB_YOD _2025": [2030],
            "MT_POP_TOT_2015": ["-"],
            "MT_POP_TOT_2020": ["50,100"],
            "MT_BUS_TOT_2015": ["       -   "],
            "MT_BUS_TOT_2020": ["2,500"],
            "MT_UCA_KM2_2015": [None],
            "MT_UCA_KM2_2020": [12],
        }
    )
    result = multitemporal_boundary_panel(source)
    assert result["year"].tolist() == [2020]
    assert result["population"].tolist() == [50_100]
    assert result["built_up_area_m2"].tolist() == [2_500]
    assert result["boundary_mode"].unique().tolist() == ["dynamic"]
    assert result["quality_controlled_2025"].all()
    assert result["built_up_area_available"].all()


def test_ghsl_multitemporal_panel_flags_uncontrolled_records() -> None:
    source = pd.DataFrame(
        {
            "ID_MTUC_G0": [1],
            "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": [None],
            "GC_UCB_YOB _2025": [2025],
            "GC_UCB_YOD _2025": [2030],
            "MT_POP_TOT_2025": [50_100],
            "MT_BUS_TOT_2025": [2_500],
            "MT_UCA_KM2_2025": [12],
        }
    )
    result = multitemporal_boundary_panel(source)
    assert result["quality_controlled_2025"].eq(False).all()


def test_ghsl_multitemporal_panel_preserves_missing_optional_built_area() -> None:
    source = pd.DataFrame(
        {
            "ID_MTUC_G0": [1],
            "GC_UCN_MAI_2025": ["Example"],
            "GC_CNT_GAD_2025": [None],
            "GC_UCB_YOB _2025": [2025],
            "GC_UCB_YOD _2025": [2030],
            "MT_POP_TOT_2025": [50_100],
            "MT_BUS_TOT_2025": [" - "],
            "MT_UCA_KM2_2025": [12],
        }
    )
    result = multitemporal_boundary_panel(source)
    assert result["built_up_area_m2"].isna().all()
    assert result["built_up_area_available"].eq(False).all()


def test_wup_converts_thousands_and_requires_mapped_categories() -> None:
    source = pd.DataFrame({"Code": [1], "Class": ["city"], "1975": [2.5], "1980": [3.0]})
    result = degree_of_urbanization_panel(
        source, location_id_column="Code", category_column="Class"
    )
    assert result["population"].tolist() == [2500.0, 3000.0]

    source.loc[0, "Class"] = "publisher label not mapped"
    with pytest.raises(SourceSchemaError, match="Unmapped"):
        degree_of_urbanization_panel(source, location_id_column="Code", category_column="Class")


def test_wup_f01_repairs_only_omitted_northern_america_parent(tmp_path) -> None:
    source = pd.DataFrame(
        {
            "LocID": [905, 840],
            "ISO3_Code": [None, "USA"],
            "Location": ["NORTHERN AMERICA", "United States of America"],
            "LocType": [2, 4],
            "LocTypeName": ["Geographic region", "Country/Area"],
            "ParentID": [5505, 918],
            "1950": [10.0, 5.0],
            "2025": [20.0, 10.0],
            "2050": [30.0, 15.0],
        }
    )
    path = tmp_path / "f01.xlsx"
    with pd.ExcelWriter(path) as writer:
        source.to_excel(writer, sheet_name="Cities", index=False)
    result = read_f01_country_city_population(path)
    hierarchy = result[
        ["country_code", "subregion_id", "subregion_name", "region_id", "region_name"]
    ].drop_duplicates()
    assert hierarchy.to_dict("records") == [
        {
            "country_code": "USA",
            "subregion_id": 918,
            "subregion_name": "Northern America",
            "region_id": 905,
            "region_name": "NORTHERN AMERICA",
        }
    ]


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


def test_wup_metric_zero_rule_is_explicit() -> None:
    source = pd.DataFrame({"ID": [1], "2025": [0.0]})
    result = city_metric_panel(
        source, city_id_column="ID", value_name="built_up_area_m2_per_capita",
        allow_zero=True,
    )
    assert result["built_up_area_m2_per_capita"].tolist() == [0.0]
    assert result["reported_zero"].all()
    with pytest.raises(SourceSchemaError, match="positive"):
        city_metric_panel(
            source, city_id_column="ID", value_name="population_density_per_km2",
            allow_zero=False,
        )


def test_wup_density_identity_allows_publisher_rounding() -> None:
    population = pd.DataFrame({"city_id": [1], "year": [2025], "population": [60_000]})
    area = pd.DataFrame({"city_id": [1], "year": [2025], "land_area_km2": [12.0]})
    density = pd.DataFrame(
        {"city_id": [1], "year": [2025], "population_density_per_km2": [5_000.005]}
    )
    result = validate_density_identity(population, area, density)
    assert result["density_difference"].abs().max() == pytest.approx(0.005)


def test_wup_density_identity_scales_population_rounding_by_area() -> None:
    population = pd.DataFrame({"city_id": [1], "year": [2025], "population": [50_000]})
    area = pd.DataFrame({"city_id": [1], "year": [2025], "land_area_km2": [1.0]})
    density = pd.DataFrame(
        {"city_id": [1], "year": [2025], "population_density_per_km2": [49_999.6]}
    )
    result = validate_density_identity(population, area, density)
    assert result["density_difference"].tolist() == pytest.approx([0.4])

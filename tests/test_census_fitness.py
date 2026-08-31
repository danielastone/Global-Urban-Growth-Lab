import pandas as pd

from urban_growth.census_fitness import apply_us_census_place_fitness, us_census_headline_sample


def cohort_row(**overrides) -> dict[str, object]:
    row = {
        "settlement_id": "US_PLACE_2010_0100001",
        "geography_status": "stable",
        "origin_land_overlap": 1.0,
        "endpoint_land_overlap": 1.0,
        "origin_population_status": "direct_decennial_enumeration",
        "endpoint_population_status": "direct_decennial_enumeration",
        "crossed_50000": True,
    }
    row.update(overrides)
    return row


def test_us_census_fitness_accepts_registered_stable_growth_row() -> None:
    result = apply_us_census_place_fitness(pd.DataFrame([cohort_row()]))
    assert result.loc[0, "level_eligible"]
    assert result.loc[0, "growth_eligible"]
    assert result.loc[0, "headline_eligible"]
    assert not result.loc[0, "spatial_eligible"]
    assert "coordinates_not_validated" in result.loc[0, "spatial_exclusion_reasons"]


def test_us_census_fitness_accepts_official_crosswalk_for_growth() -> None:
    result = apply_us_census_place_fitness(
        pd.DataFrame([cohort_row(geography_status="official_crosswalk")])
    )
    assert result.loc[0, "growth_eligible"]
    assert result.loc[0, "headline_eligible"]
    assert not result.loc[0, "boundary_temporally_fixed"]
    assert result.loc[0, "concordance_status"] == "official_crosswalk"


def test_us_census_fitness_fails_bad_overlap_if_upstream_contract_is_bypassed() -> None:
    result = apply_us_census_place_fitness(
        pd.DataFrame([cohort_row(origin_land_overlap=0.90)])
    )
    assert not result.loc[0, "growth_eligible"]
    assert not result.loc[0, "headline_eligible"]
    assert result.loc[0, "validation_status"] == "failed"


def test_us_census_headline_sample_cannot_bypass_gate() -> None:
    cohort = pd.DataFrame(
        [
            cohort_row(),
            cohort_row(
                settlement_id="US_PLACE_2010_0100002",
                origin_population_status="modeled_estimate",
            ),
        ]
    )
    result = us_census_headline_sample(cohort)
    assert result["settlement_id"].tolist() == ["US_PLACE_2010_0100001"]


def test_us_census_fitness_preserves_original_fields() -> None:
    original = pd.DataFrame([cohort_row(custom_raw_field="raw-audit-value")])
    result = apply_us_census_place_fitness(original)
    assert result.loc[0, "custom_raw_field"] == "raw-audit-value"
    assert original.columns.tolist() == list(cohort_row(custom_raw_field="x").keys())

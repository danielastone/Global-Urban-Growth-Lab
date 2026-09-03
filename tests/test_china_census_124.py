from urban_growth.china_census_124 import (
    china_issue_124_source_register,
    qualify_china_issue_124_sources,
)


def test_three_censuses_do_not_supply_two_forecast_origins_or_stable_localities() -> None:
    qualified, status = qualify_china_issue_124_sources(china_issue_124_source_register())
    census = qualified.set_index("candidate_id").loc["china_census_county_2000_2020"]
    assert census["exclusion_reason"] == "administrative_unit_not_comparable_locality"
    assert census["usable_forecast_origins"] == 1
    assert not status.iloc[0]["benchmark_estimable"]


def test_prefecture_totals_are_not_treated_as_city_locality_counts() -> None:
    qualified, _ = qualify_china_issue_124_sources(china_issue_124_source_register())
    prefecture = qualified.set_index("candidate_id").loc["china_prefecture_city_totals"]
    assert prefecture["exclusion_reason"] == "not_direct_enumeration"
    assert not prefecture["issue_124_qualified"]


def test_candidate_requires_population_weighted_crosswave_concordance() -> None:
    candidate = china_issue_124_source_register().iloc[[1]].copy()
    candidate["locality_concept_comparable"] = True
    candidate["usable_forecast_origins"] = 2
    candidate["release_status"] = "released"
    qualified, _ = qualify_china_issue_124_sources(candidate)
    assert qualified.iloc[0]["exclusion_reason"] == (
        "official_population_weighted_concordance_unresolved"
    )


def test_candidate_passes_only_when_all_identification_requirements_pass() -> None:
    candidate = china_issue_124_source_register().iloc[[1]].copy()
    candidate["locality_concept_comparable"] = True
    candidate["official_population_weighted_concordance"] = True
    candidate["usable_forecast_origins"] = 2
    candidate["release_status"] = "released"
    qualified, status = qualify_china_issue_124_sources(candidate)
    assert qualified.iloc[0]["issue_124_qualified"]
    assert status.iloc[0]["benchmark_estimable"]

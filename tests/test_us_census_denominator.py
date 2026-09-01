import pandas as pd
import pytest

from urban_growth.adapters.us_census import (
    build_us_place_boundary_cohort,
    build_us_place_origin_denominator,
    us_place_concordance_coverage,
)


def _population_2010() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "geoid": ["0100001", "0100002", "0100003", "0100004"],
            "place_name": ["Stable", "Split", "Renamed", "Too Large"],
            "population": [30_000, 40_000, 50_000, 110_000],
        }
    )


def _population_2020() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "geoid": ["0100001", "0100201", "0100202", "0100300", "0100004"],
            "place_name": ["Stable", "Split A", "Split B", "Renamed New", "Too Large"],
            "population": [35_000, 22_000, 25_000, 60_000, 120_000],
        }
    )


def _relationship() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "GEOID_PLACE_10": ["0100001", "0100002", "0100002", "0100003", "0100004"],
            "GEOID_PLACE_20": ["0100001", "0100201", "0100202", "0100300", "0100004"],
            "AREALAND_PLACE_10": [100.0, 100.0, 100.0, 100.0, 100.0],
            "AREALAND_PLACE_20": [100.0, 50.0, 50.0, 100.0, 100.0],
            "AREALAND_PART": [100.0, 50.0, 50.0, 100.0, 100.0],
        }
    )


def test_origin_denominator_retains_unresolved_places() -> None:
    result = build_us_place_origin_denominator(
        _population_2010(), _population_2020(), _relationship()
    )
    assert result["GEOID_PLACE_10"].tolist() == ["0100001", "0100002", "0100003"]
    assert result["cohort_defined_at_origin"].all()
    assert result["cohort_uses_endpoint_population"].eq(False).all()

    split = result.loc[result["GEOID_PLACE_10"].eq("0100002")].iloc[0]
    assert not split["concordance_resolved"]
    assert not split["analysis_eligible"]
    assert split["concordance_exclusion_reason"] == "origin_to_multiple_endpoints"
    assert split["geography_status"] == "unresolved"

    renamed = result.loc[result["GEOID_PLACE_10"].eq("0100003")].iloc[0]
    assert renamed["concordance_resolved"]
    assert renamed["geography_status"] == "official_crosswalk"


def test_origin_denominator_membership_does_not_depend_on_endpoint_population() -> None:
    endpoint = _population_2020()
    first = build_us_place_origin_denominator(_population_2010(), endpoint, _relationship())
    changed = endpoint.copy()
    changed["population"] = changed["population"] * 100
    second = build_us_place_origin_denominator(_population_2010(), changed, _relationship())
    assert first["settlement_id"].tolist() == second["settlement_id"].tolist()


def test_concordance_coverage_uses_full_origin_denominator() -> None:
    denominator = build_us_place_origin_denominator(
        _population_2010(), _population_2020(), _relationship()
    )
    coverage = us_place_concordance_coverage(denominator).iloc[0]
    assert coverage["origin_denominator_rows"] == 3
    assert coverage["origin_denominator_population"] == 120_000
    assert coverage["concordance_resolved_rows"] == 2
    assert coverage["concordance_count_coverage"] == pytest.approx(2 / 3)
    assert coverage["concordance_population_coverage"] == pytest.approx(80_000 / 120_000)
    assert coverage["analysis_eligible_rows"] == 2
    assert coverage["future_outcome_used_for_membership"] == False
    assert coverage["coverage_threshold_registered"] == False


def test_analysis_cohort_is_filtered_only_after_denominator_is_fixed() -> None:
    cohort = build_us_place_boundary_cohort(
        _population_2010(), _population_2020(), _relationship()
    )
    assert cohort["GEOID_PLACE_10"].tolist() == ["0100001", "0100003"]
    assert cohort["population_origin"].tolist() == [30_000, 50_000]

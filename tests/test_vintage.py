import pandas as pd

from urban_growth.vintage import (
    evaluate_wup2018_vintage,
    reciprocal_nearest_crosswalk,
    vintage_country_weighting_diagnostics,
    vintage_crosswalk_coverage,
    vintage_revision_decomposition,
)


def _vintage_panel() -> pd.DataFrame:
    rows = []
    for city_id, country, latitude, growth in [(1, 10, 0.0, 1.1), (2, 20, 10.0, 1.2)]:
        for year, population in [(2013, 100), (2018, 100 * growth), (2023, 130)]:
            rows.append(
                {
                    "city_id": city_id,
                    "country_location_id": country,
                    "country_name": f"Country {country}",
                    "city_name": f"Vintage {city_id}",
                    "latitude": latitude,
                    "longitude": 0.0,
                    "year": year,
                    "population": population,
                }
            )
    return pd.DataFrame(rows)


def _current_panel() -> pd.DataFrame:
    rows = []
    for city_id, country, latitude in [(101, 10, 0.01), (102, 20, 10.01)]:
        for year, population in [(2013, 100), (2018, 110), (2023, 130)]:
            rows.append(
                {
                    "city_id": city_id,
                    "LocID": country,
                    "City_Name": f"Current {city_id}",
                    "PWCent_Latitude": latitude,
                    "PWCent_Longitude": 0.0,
                    "year": year,
                    "population": population,
                }
            )
    return pd.DataFrame(rows)


def test_vintage_crosswalk_requires_reciprocal_nearest_city() -> None:
    crosswalk = reciprocal_nearest_crosswalk(_vintage_panel(), _current_panel())
    assert crosswalk[["vintage_city_id", "current_city_id"]].values.tolist() == [
        [1, 101], [2, 102]
    ]
    assert crosswalk["distance_km"].max() < 2


def test_vintage_evaluation_separates_published_and_retrospective_inputs() -> None:
    vintage = _vintage_panel()
    current = _current_panel()
    crosswalk = reciprocal_nearest_crosswalk(vintage, current)
    metrics, bootstrap = evaluate_wup2018_vintage(
        vintage,
        current,
        crosswalk,
        distance_thresholds=(5.0,),
        population_agreement_thresholds=(None, 0.2),
    )
    unrestricted = metrics.loc[metrics["origin_population_agreement"].eq("unrestricted")]
    assert set(unrestricted["model"]) == {
        "published_projection", "vintage_persistence", "retrospective_persistence"
    }
    assert unrestricted["n"].unique().tolist() == [2]
    published = unrestricted.loc[unrestricted["model"].eq("published_projection"), "mae"]
    assert published.iloc[0] >= 0
    assert set(bootstrap["origin_population_agreement"]) == {
        "unrestricted", "within_20pct"
    }
    assert bootstrap["distance_threshold_km"].unique().tolist() == [5.0]
    assert bootstrap["clusters"].eq(2).all()


def test_vintage_revision_decomposition_closes_identity_without_overclaim() -> None:
    vintage = _vintage_panel()
    current = _current_panel()
    crosswalk = reciprocal_nearest_crosswalk(vintage, current)
    detail, summary = vintage_revision_decomposition(
        vintage, current, crosswalk, maximum_distance_km=5.0
    )
    assert detail["decomposition_identity_residual"].abs().max() < 1e-12
    assert summary.loc[0, "identity_residual_max_abs"] < 1e-12
    assert detail["comparison_status"].eq(
        "cross_revision_cross_definition_not_clean_forecast_error"
    ).all()
    assert summary.loc[0, "target_component_identification"] == (
        "forecast_error_plus_target_revision_plus_definition_change"
    )


def test_vintage_metrics_label_hindsight_benchmark() -> None:
    vintage = _vintage_panel()
    current = _current_panel()
    crosswalk = reciprocal_nearest_crosswalk(vintage, current)
    metrics, _ = evaluate_wup2018_vintage(
        vintage,
        current,
        crosswalk,
        distance_thresholds=(5.0,),
        population_agreement_thresholds=(None,),
    )
    hindsight = metrics.loc[metrics["model"].eq("retrospective_persistence")].iloc[0]
    assert hindsight["predictor_information_set"] == "revised_2025_hindsight"
    assert not hindsight["eligible_for_like_for_like_2018_ranking"]
    assert metrics["target_comparability"].eq("cross_revision_cross_definition").all()


def test_vintage_crosswalk_coverage_reports_excluded_universe() -> None:
    vintage = _vintage_panel()
    crosswalk = reciprocal_nearest_crosswalk(vintage, _current_panel())
    crosswalk = crosswalk.loc[crosswalk["vintage_city_id"].eq(1)]
    summary, country = vintage_crosswalk_coverage(vintage, crosswalk)
    assert summary["cities"].sum() == 2
    excluded = summary.loc[
        summary["match_status"].eq("no_reciprocal_match_within_10km"), "cities"
    ]
    assert excluded.tolist() == [1]
    assert country["primary_matches"].sum() == 1


def test_vintage_country_weighting_reports_influence() -> None:
    vintage = _vintage_panel()
    current = _current_panel()
    crosswalk = reciprocal_nearest_crosswalk(vintage, current)
    summary, country = vintage_country_weighting_diagnostics(
        vintage, current, crosswalk, repetitions=100
    )
    assert summary.loc[0, "cities"] == 2
    assert summary.loc[0, "countries"] == 2
    assert (
        summary.loc[0, "countries_published_projection_wins"]
        + summary.loc[0, "countries_vintage_persistence_wins"]
        == 2
    )
    assert country["cities"].eq(1).all()
    assert country["leave_country_out_city_weighted_difference"].notna().all()

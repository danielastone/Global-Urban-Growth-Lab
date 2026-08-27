import pandas as pd

from urban_growth.vintage import evaluate_wup2018_vintage, reciprocal_nearest_crosswalk


def _vintage_panel() -> pd.DataFrame:
    rows = []
    for city_id, country, latitude, growth in [(1, 10, 0.0, 1.1), (2, 20, 10.0, 1.2)]:
        for year, population in [(2013, 100), (2018, 100 * growth), (2023, 130)]:
            rows.append(
                {
                    "city_id": city_id,
                    "country_location_id": country,
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

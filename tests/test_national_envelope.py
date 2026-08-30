import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.national_envelope import (
    national_envelope_feature_registry,
    national_envelope_forecast_features,
    national_envelope_intervals,
    national_envelope_summaries,
)


def envelope_panel() -> pd.DataFrame:
    values = {
        2000: {"city": 400.0, "town_and_semi_dense": 300.0, "rural": 300.0},
        2005: {"city": 500.0, "town_and_semi_dense": 320.0, "rural": 280.0},
        2010: {"city": 600.0, "town_and_semi_dense": 330.0, "rural": 270.0},
        2030: {"city": 900.0, "town_and_semi_dense": 350.0, "rural": 250.0},
    }
    rows = []
    for year, categories in values.items():
        for category, population in categories.items():
            rows.append(
                {
                    "country_code": "X", "year": year, "category": category,
                    "population": population, "subregion_name": "Example subregion",
                    "region_name": "Example region",
                    "observation_type": "estimate" if year <= 2025 else "projection",
                    "revision_semantics": "WUP_2025_revised_history",
                }
            )
    return pd.DataFrame(rows)


def test_national_envelope_decomposes_growth_and_reallocation() -> None:
    result = national_envelope_intervals(envelope_panel())
    assert result["period_start"].tolist() == [2000, 2005]
    first = result.iloc[0]
    assert first["total_population_start"] == 1000.0
    assert first["total_population_end"] == 1100.0
    assert first["city_population_change"] == 100.0
    assert first["city_reallocation_change"] == pytest.approx(60.0)
    assert sum(first[f"{category}_share_change"] for category in (
        "city", "town_and_semi_dense", "rural"
    )) == pytest.approx(0.0)
    assert sum(first[f"{category}_reallocation_change"] for category in (
        "city", "town_and_semi_dense", "rural"
    )) == pytest.approx(0.0)
    assert result["interval_observation_status"].eq("retrospective_revised_estimate").all()
    assert not result["composition_discontinuity_flag"].any()


def test_national_envelope_rejects_incomplete_composition() -> None:
    source = envelope_panel()
    source = source.loc[~(source["category"].eq("rural") & source["year"].eq(2005))]
    with pytest.raises(SourceSchemaError, match="incomplete"):
        national_envelope_intervals(source)


def test_feature_registry_forbids_realized_future_values() -> None:
    registry = national_envelope_feature_registry().set_index("feature_family")
    assert not registry.loc["realized_envelope_growth", "future_usable_at_origin"]
    assert not registry.loc["realized_share_change", "future_usable_at_origin"]
    assert registry.loc["lagged_envelope_growth", "future_usable_at_origin"]
    assert registry.loc["origin_settlement_shares", "future_usable_at_origin"]


def test_forecast_features_use_only_completed_prior_interval() -> None:
    intervals = national_envelope_intervals(envelope_panel())
    features = national_envelope_forecast_features(intervals)
    first, second = features.iloc[0], features.iloc[1]
    assert not first["lagged_envelope_available"]
    assert second["lagged_total_annualized_log_growth"] == pytest.approx(
        intervals.iloc[0]["total_annualized_log_growth"]
    )
    assert not features["uses_outcome_period_value"].any()


def test_summaries_separate_country_equal_and_population_weights() -> None:
    intervals = national_envelope_intervals(envelope_panel())
    second_country = intervals.assign(
        country_code="Y", total_population_start=intervals["total_population_start"] * 10,
        total_annualized_log_growth=intervals["total_annualized_log_growth"] * 2,
    )
    summaries = national_envelope_summaries(pd.concat([intervals, second_country]))
    global_first = summaries.loc[
        summaries["sample"].eq("all") & summaries["aggregation_level"].eq("global")
        & summaries["period_start"].eq(2000)
    ].set_index("weighting")
    assert global_first.loc["population_start", "total_annualized_log_growth"] > global_first.loc[
        "country_equal", "total_annualized_log_growth"
    ]
    assert global_first["country_count"].eq(2).all()


def test_origin_grid_is_nonoverlapping_and_discontinuities_are_flagged() -> None:
    source = envelope_panel()
    extra_start = source.loc[source["year"].eq(2005)].assign(year=2001)
    extra_end = source.loc[source["year"].eq(2010)].assign(year=2006)
    result = national_envelope_intervals(pd.concat([source, extra_start, extra_end]))
    assert 2001 not in result["period_start"].tolist()
    source.loc[source["year"].eq(2005) & source["category"].eq("city"), "population"] = 1000
    source.loc[
        source["year"].eq(2005) & source["category"].eq("town_and_semi_dense"), "population"
    ] = 0
    flagged = national_envelope_intervals(source).iloc[0]
    assert flagged["category_presence_transition"]
    assert flagged["large_share_change_flag"]
    assert flagged["composition_discontinuity_flag"]

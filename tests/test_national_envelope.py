import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.national_envelope import (
    extent_density_reconciliation,
    national_envelope_feature_registry,
    national_envelope_forecast_features,
    national_envelope_intervals,
    national_envelope_summaries,
)


def reconciliation_inputs(validated: bool = True):
    fixed = pd.DataFrame([
        {"country_code": "X", "polygon_id": "a", "period_start": 2000,
         "period_end": 2005, "built_surface_start": 10.0, "built_surface_end": 12.0,
         "density_start": 4.0, "density_end": 5.0,
         "density_metric_id": "census_pop_per_built_surface",
         "density_lineage_status": "clean"},
        {"country_code": "X", "polygon_id": "b", "period_start": 2000,
         "period_end": 2005, "built_surface_start": 5.0, "built_surface_end": 6.0,
         "density_start": 2.0, "density_end": 2.0,
         "density_metric_id": "census_pop_per_built_surface",
         "density_lineage_status": "clean"},
    ])
    national = pd.DataFrame([{
        "country_code": "X", "period_start": 2000, "period_end": 2005,
        "city_population_start": 50.0, "city_population_end": 80.0,
        "category_presence_transition": False, "large_share_change_flag": False,
        "large_share_change_threshold": 0.25, "composition_discontinuity_flag": False,
        "interval_observation_status": "retrospective_revised_estimate",
    }])
    membership = pd.DataFrame([{
        "country_code": "X", "period_start": 2000, "period_end": 2005,
        "f21_population_start": 50.0, "f21_population_end": 72.0,
        "constant_membership_validated": validated,
        "membership_semantics_source": "publisher-methodology" if validated else None,
    }])
    return fixed, national, membership


def test_extent_density_reconciliation_is_exact_and_inherits_flags() -> None:
    result = extent_density_reconciliation(*reconciliation_inputs()).iloc[0]
    assert result["fixed_polygon_population_change"] == pytest.approx(22.0)
    assert result["horizontal_extent_change"] == pytest.approx(11.0)
    assert result["in_place_densification_change"] == pytest.approx(11.0)
    assert result["f01_composition_residual"] == pytest.approx(8.0)
    assert result["net_reclassification_change"] == pytest.approx(8.0)
    assert result["residual_interpretation"] == "net_reclassification"
    assert result["f01_reconciliation_error"] == pytest.approx(0.0)
    assert not result["composition_discontinuity_flag"]


def test_extent_density_reconciliation_fails_closed_on_unvalidated_membership() -> None:
    result = extent_density_reconciliation(*reconciliation_inputs(validated=False)).iloc[0]
    assert result["residual_interpretation"] == "unidentified_composition_residual"
    assert pd.isna(result["net_reclassification_change"])


def test_extent_density_reconciliation_fails_closed_when_f21_does_not_close() -> None:
    fixed, national, membership = reconciliation_inputs()
    membership["f21_population_end"] = 60.0
    result = extent_density_reconciliation(fixed, national, membership).iloc[0]
    assert not result["f21_crosscheck_within_tolerance"]
    assert result["residual_interpretation"] == "unidentified_composition_residual"


def test_extent_density_reconciliation_rejects_duplicate_polygons() -> None:
    fixed, national, membership = reconciliation_inputs()
    with pytest.raises(SourceSchemaError, match="duplicate"):
        extent_density_reconciliation(pd.concat([fixed, fixed.iloc[[0]]]), national, membership)


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

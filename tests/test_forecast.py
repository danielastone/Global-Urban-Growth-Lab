import numpy as np
import pandas as pd
import pytest

from urban_growth.forecast import (
    attach_national_city_category_baseline,
    balanced_origin_cohort,
    baseline_predictions,
    build_forecast_intervals,
    build_ghsl_dynamic_forecast_intervals,
    build_ghsl_fixed_forecast_intervals,
    cluster_bootstrap_paired_difference,
    equal_country_forecast_metrics,
    equal_country_origin_forecast_metrics,
    equal_origin_forecast_metrics,
    evaluate_rolling_baselines,
    evaluate_rolling_hierarchy_models,
    leave_one_cluster_out_paired_difference,
    locked_origin_model_evaluation,
    matched_boundary_forecast_panels,
    paired_error_comparison,
    registered_sequential_interval_calibration,
    rolling_baseline_errors,
    rolling_origin_splits,
    score_forecast,
    sequential_interval_calibration,
    temporal_reversal_diagnostics,
    two_way_cluster_bootstrap_paired_difference,
)
from urban_growth.io import SourceSchemaError


def test_rolling_origin_prevents_future_outcomes_in_training() -> None:
    panel = pd.DataFrame(
        {"period_start": [1995, 2000, 2005], "period_end": [2000, 2005, 2010]}
    )
    origin, train, test = next(rolling_origin_splits(panel, [2005]))
    assert origin == 2005
    assert train.tolist() == [0, 1]
    assert test.tolist() == [2]


def test_score_forecast_uses_matched_rows() -> None:
    actual = pd.Series([0.01, -0.02, None])
    predicted = pd.Series([0.02, -0.01, 0.5])
    metrics = score_forecast(actual, predicted)
    assert metrics.n == 2
    assert metrics.mae == pytest.approx(0.01)
    assert metrics.bias == pytest.approx(0.01)
    assert metrics.directional_accuracy == 1.0


def city_year_source() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": [1, 1, 1, 1], "year": [2015, 2020, 2025, 2030],
            "population": [80_000, 90_000, 100_000, 120_000],
            "observation_type": ["estimate", "estimate", "estimate", "projection"],
            "ISO3_Code": ["EXP"] * 4, "City_Name": ["Example"] * 4,
            "built_up_share_of_land": [0.2, 0.3, 0.4, 0.9],
            "population_density_per_km2": [1_000, 1_100, 1_200, 1_300],
        }
    )


def test_forecast_intervals_use_only_origin_predictors() -> None:
    result = build_forecast_intervals(city_year_source(), [2020])
    assert result["period_end"].tolist() == [2025]
    assert result["built_up_share_at_origin"].tolist() == [0.3]
    assert result["population_density_at_origin"].tolist() == [1_100]
    assert result["outcome_observation_type"].tolist() == ["estimate"]


def test_forecast_intervals_exclude_projection_outcomes_by_default() -> None:
    with pytest.raises(SourceSchemaError, match="No complete"):
        build_forecast_intervals(city_year_source(), [2025])
    result = build_forecast_intervals(
        city_year_source(), [2025], allowed_outcome_types={"projection"}
    )
    assert result["period_end"].tolist() == [2030]
    assert result["outcome_observation_type"].tolist() == ["projection"]


def test_forecast_intervals_require_exact_lag_year() -> None:
    source = city_year_source().loc[lambda x: x.year.ne(2015)]
    with pytest.raises(SourceSchemaError, match="No complete"):
        build_forecast_intervals(source, [2020])


def test_gapped_interval_has_no_shared_population_endpoint() -> None:
    source = city_year_source()
    result = build_forecast_intervals(
        source,
        [2020],
        outcome_gap_years=5,
        allowed_outcome_types={"estimate", "projection"},
    )
    assert result["outcome_start_year"].tolist() == [2025]
    assert result["period_end"].tolist() == [2030]
    assert result["outcome_gap_years"].tolist() == [5]
    assert result["future_growth"].iloc[0] == pytest.approx(0.03646431136)


def test_country_rank_uses_full_origin_universe_before_future_filter() -> None:
    complete = city_year_source()
    incomplete = complete.loc[complete["year"].le(2020)].copy()
    incomplete["city_id"] = 2
    incomplete["City_Name"] = "Larger but incomplete"
    incomplete["population"] = [100_000, 110_000]
    source = pd.concat([complete, incomplete], ignore_index=True)
    result = build_forecast_intervals(source, [2020])
    assert result["city_id"].tolist() == [1]
    assert result["country_rank_origin"].tolist() == [2.0]
    assert result["country_city_count_origin"].tolist() == [2]


def test_ghsl_forecast_requires_and_preserves_fixed_boundary_semantics() -> None:
    source = pd.DataFrame(
        {
            "city_id": [1, 1, 1], "year": [2015, 2020, 2025],
            "population": [80_000, 90_000, 100_000],
            "built_up_area_m2": [10_000_000, 11_000_000, 12_000_000],
            "urban_centre_area_km2": [20, 20, 20],
            "boundary_mode": ["fixed"] * 3,
            "boundary_product": ["ucdb_fixed_2025_boundary"] * 3,
            "GC_UCN_MAI_2025": ["Example"] * 3,
            "GC_CNT_GAD_2025": ["Exampleland"] * 3,
        }
    )
    result = build_ghsl_fixed_forecast_intervals(source, [2020])
    assert result["boundary_temporally_fixed"].all()
    assert result["boundary_reference_year"].unique().tolist() == [2025]
    assert result["boundary_history_uses_future_reference"].all()
    assert result["cross_stream_reconciled"].eq(False).all()
    assert result["boundary_mode"].unique().tolist() == ["fixed"]
    reconciliation = pd.DataFrame(
        {
            "city_id": [1], "population_difference": [0.25],
            "built_up_area_difference_m2": [0],
            "urban_centre_area_difference_km2": [0],
        }
    )
    checked = build_ghsl_fixed_forecast_intervals(
        source, [2020], reconciliation=reconciliation
    )
    assert checked["cross_stream_reconciled"].all()
    with pytest.raises(SourceSchemaError, match="entity universe"):
        build_ghsl_fixed_forecast_intervals(
            source, [2020], reconciliation=reconciliation.iloc[0:0]
        )
    source.loc[source["year"].eq(2015), "boundary_mode"] = "dynamic"
    with pytest.raises(SourceSchemaError, match="fixed boundaries only"):
        build_ghsl_fixed_forecast_intervals(source, [2020])


def test_dynamic_ghsl_intervals_and_boundary_matching() -> None:
    years = [2015, 2020, 2025]
    dynamic = pd.DataFrame(
        {
            "city_id": [1] * 3, "year": years, "population": [80_000, 90_000, 100_000],
            "built_up_area_m2": [10_000_000, 11_000_000, 12_000_000],
            "urban_centre_area_km2": [18, 19, 20], "boundary_mode": ["dynamic"] * 3,
            "boundary_product": ["ucdb_multitemporal_boundaries"] * 3,
            "GC_UCN_MAI_2025": ["Example"] * 3,
            "GC_CNT_GAD_2025": ["Exampleland"] * 3,
            "quality_controlled_2025": [True] * 3,
        }
    )
    dynamic_intervals = build_ghsl_dynamic_forecast_intervals(dynamic, [2020])
    assert dynamic_intervals["boundary_temporally_fixed"].eq(False).all()
    fixed_source = dynamic.assign(
        boundary_mode="fixed", boundary_product="ucdb_fixed_2025_boundary",
        urban_centre_area_km2=20,
    )
    fixed_intervals = build_ghsl_fixed_forecast_intervals(fixed_source, [2020])
    fixed_matched, dynamic_matched = matched_boundary_forecast_panels(
        fixed_intervals, dynamic_intervals
    )
    assert fixed_matched[["city_id", "period_start"]].equals(
        dynamic_matched[["city_id", "period_start"]]
    )


def test_baselines_use_training_country_mean_and_global_fallback() -> None:
    train = pd.DataFrame(
        {
            "city_id": [1, 2, 3], "country_code": ["A", "A", "B"],
            "future_growth": [0.01, 0.03, -0.01],
        }
    )
    test = pd.DataFrame(
        {
            "city_id": [1, 4], "country_code": ["A", "C"],
            "recent_growth": [0.04, -0.02],
        },
        index=[10, 11],
    )
    result = baseline_predictions(train, test)
    assert result["country_mean"].tolist() == pytest.approx([0.02, 0.01])
    assert result["country_mean_leave_city_out"].tolist() == pytest.approx([0.03, 0.01])
    assert result["global_mean"].tolist() == pytest.approx([0.01, 0.01])
    assert result["persistence"].tolist() == [0.04, -0.02]


def test_national_city_category_baseline_uses_only_pre_origin_values() -> None:
    intervals = pd.DataFrame(
        {
            "country_code": ["A"],
            "period_start": [2020],
            "population_lag": [10.0],
            "population_start": [20.0],
            "future_growth": [0.01],
        }
    )
    national = pd.DataFrame(
        {
            "country_code": ["A", "A", "A"],
            "year": [2015, 2020, 2025],
            "national_city_category_population": [100.0, 110.0, 9999.0],
            "revision_semantics": ["WUP_2025_revised_history"] * 3,
            "subregion_id": [10] * 3,
            "subregion_name": ["Example subregion"] * 3,
            "region_id": [1] * 3,
            "region_name": ["Example region"] * 3,
        }
    )
    attached = attach_national_city_category_baseline(intervals, national)
    expected = (np.log(110.0) - np.log(100.0)) / 5
    assert attached["national_city_category_recent_growth"].iloc[0] == pytest.approx(
        expected
    )
    expected_loo = (np.log(90.0) - np.log(90.0)) / 5
    assert attached[
        "national_city_category_recent_growth_leave_city_out"
    ].iloc[0] == pytest.approx(expected_loo)
    assert attached["national_focal_share_lag"].iloc[0] == pytest.approx(0.10)
    assert attached["national_focal_share_origin"].iloc[0] == pytest.approx(20 / 110)
    assert attached["national_baseline_focal_city_excluded"].iloc[0]
    assert attached["national_focal_component_membership_assumed"].iloc[0]
    assert not attached["national_baseline_uses_future_value"].iloc[0]
    assert attached["subregion_id"].tolist() == [10]
    assert attached["region_id"].tolist() == [1]




def test_national_leave_city_out_rejects_invalid_component_subtraction() -> None:
    intervals = pd.DataFrame(
        {
            "country_code": ["A"],
            "period_start": [2020],
            "population_lag": [100.0],
            "population_start": [120.0],
        }
    )
    national = pd.DataFrame(
        {
            "country_code": ["A", "A"],
            "year": [2015, 2020],
            "national_city_category_population": [100.0, 110.0],
            "revision_semantics": ["WUP_2025_revised_history"] * 2,
            "subregion_id": [10] * 2,
            "subregion_name": ["Example subregion"] * 2,
            "region_id": [1] * 2,
            "region_name": ["Example region"] * 2,
        }
    )
    with pytest.raises(SourceSchemaError, match="strictly smaller positive component"):
        attach_national_city_category_baseline(intervals, national)

def test_baselines_include_attached_national_demographic_comparator() -> None:
    train = pd.DataFrame({"country_code": ["A"], "future_growth": [0.01]})
    test = pd.DataFrame(
        {
            "country_code": ["A"],
            "recent_growth": [0.02],
            "national_city_category_recent_growth": [0.03],
            "national_city_category_recent_growth_leave_city_out": [0.025],
        }
    )
    result = baseline_predictions(train, test)
    assert result["national_city_category_persistence_inclusive"].tolist() == [0.03]
    assert result[
        "national_city_category_persistence_leave_city_out"
    ].tolist() == [0.025]


def test_baselines_include_leave_city_out_region_ladder() -> None:
    train = pd.DataFrame(
        {
            "city_id": [1, 2, 3],
            "country_code": ["A", "B", "C"],
            "region_id": [10, 10, 20],
            "subregion_id": [11, 11, 21],
            "future_growth": [0.01, 0.03, -0.01],
        }
    )
    test = pd.DataFrame(
        {
            "city_id": [1],
            "country_code": ["A"],
            "region_id": [10],
            "subregion_id": [11],
            "recent_growth": [0.02],
        }
    )
    result = baseline_predictions(train, test)
    assert result["region_mean"].tolist() == pytest.approx([0.02])
    assert result["subregion_mean"].tolist() == pytest.approx([0.02])
    assert result["region_mean_leave_city_out"].tolist() == pytest.approx([0.03])
    assert result["subregion_mean_leave_city_out"].tolist() == pytest.approx([0.03])
    assert result["global_mean_leave_city_out"].tolist() == pytest.approx([0.01])


def test_rolling_baselines_use_identical_test_rows() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 2, 1, 2],
            "period_start": [2000, 2000, 2005, 2005],
            "period_end": [2005, 2005, 2010, 2010],
            "country_code": ["A", "B", "A", "B"],
            "future_growth": [0.01, -0.01, 0.02, -0.02],
            "recent_growth": [0.00, 0.00, 0.01, -0.01],
        }
    )
    result = evaluate_rolling_baselines(panel, [2005])
    assert set(result["model"]) == {
        "zero_growth", "global_mean", "country_mean", "country_mean_leave_city_out",
        "persistence",
    }
    assert result["n"].unique().tolist() == [2]


def test_hierarchy_models_compare_origin_and_frozen_features() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 2, 1, 2], "country_code": ["A"] * 4,
            "period_start": [2000, 2000, 2005, 2005],
            "period_end": [2005, 2005, 2010, 2010],
            "future_growth": [0.01, -0.01, 0.02, -0.02],
            "recent_growth": [0.00, 0.01, 0.01, -0.01],
            "population_lag": [80_000, 60_000, 85_000, 65_000],
            "population_start": [85_000, 65_000, 90_000, 70_000],
            "country_rank_percentile_lag": [0.25, 0.75, 0.25, 0.75],
            "country_rank_percentile_origin": [0.25, 0.75, 0.25, 0.75],
        }
    )
    result = evaluate_rolling_hierarchy_models(panel, [2005])
    assert set(result["model"]) == {
        "country_loo_plus_recent_growth", "origin_hierarchy", "frozen_hierarchy"
    }
    assert result["n"].unique().tolist() == [2]


def test_row_errors_support_paired_size_comparison() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 2, 1, 2],
            "period_start": [2000, 2000, 2005, 2005],
            "period_end": [2005, 2005, 2010, 2010],
            "country_code": ["A", "B", "A", "B"],
            "population_start": [100_000, 2_000_000, 110_000, 2_100_000],
            "future_growth": [0.01, -0.01, 0.02, -0.02],
            "recent_growth": [0.00, 0.00, 0.01, -0.01],
        }
    )
    errors = rolling_baseline_errors(panel, [2005])
    result = paired_error_comparison(errors)
    assert set(result["size_bin"].astype(str)) == {"50–150k", "2m+"}
    assert result["n"].tolist() == [1, 1]


def test_balanced_cohort_and_equal_country_weighting() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 1, 2], "period_start": [2000, 2005, 2005],
            "period_end": [2005, 2010, 2010],
        }
    )
    balanced = balanced_origin_cohort(panel, [2000, 2005])
    assert balanced["city_id"].unique().tolist() == [1]
    errors = pd.DataFrame(
        {
            "model": ["m", "m", "m"], "country_code": ["A", "A", "B"],
            "error": [0.01, 0.03, 0.10], "absolute_error": [0.01, 0.03, 0.10],
        }
    )
    result = equal_country_forecast_metrics(errors)
    assert result.loc[0, "equal_country_mae"] == pytest.approx(0.06)
    assert result.loc[0, "countries"] == 2


def test_equal_origin_metrics_do_not_let_larger_origins_dominate() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000, 2000, 2005],
            "model": ["m", "m", "m"],
            "country_code": ["A", "B", "A"],
            "error": [0.10, 0.10, 0.30],
            "absolute_error": [0.10, 0.10, 0.30],
        }
    )
    result = equal_origin_forecast_metrics(errors)
    assert result.loc[0, "equal_origin_mae"] == pytest.approx(0.20)
    assert result.loc[0, "origins"] == 2
    assert result.loc[0, "minimum_origin_rows"] == 1
    assert result.loc[0, "maximum_origin_rows"] == 2


def test_equal_country_origin_metrics_apply_both_weighting_stages() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000, 2000, 2000, 2005],
            "model": ["m"] * 4,
            "country_code": ["A", "A", "B", "A"],
            "error": [0.10, 0.30, 0.50, 0.10],
            "absolute_error": [0.10, 0.30, 0.50, 0.10],
        }
    )
    result = equal_country_origin_forecast_metrics(errors)
    assert result.loc[0, "equal_country_origin_mae"] == pytest.approx(0.225)
    assert result.loc[0, "minimum_countries_per_origin"] == 1
    assert result.loc[0, "maximum_countries_per_origin"] == 2
    assert result.loc[0, "estimand"] == (
        "origins_equal_countries_equal_within_origin"
    )


def test_country_cluster_bootstrap_is_reproducible() -> None:
    rows = []
    for city_id, country, persistence_error, country_error in [
        (1, "A", 0.01, 0.02), (2, "A", 0.02, 0.03),
        (3, "B", 0.03, 0.02), (4, "B", 0.04, 0.03),
    ]:
        for model, error in [("persistence", persistence_error), ("country_mean", country_error)]:
            rows.append(
                {
                    "city_id": city_id, "origin": 2020, "country_code": country,
                    "size_bin": "50–150k", "model": model, "absolute_error": error,
                }
            )
    errors = pd.DataFrame(rows)
    first = cluster_bootstrap_paired_difference(errors, repetitions=200, seed=7)
    second = cluster_bootstrap_paired_difference(errors, repetitions=200, seed=7)
    pd.testing.assert_frame_equal(first, second)
    assert first.loc[0, "clusters"] == 2
    assert first.loc[0, "observed_mean_difference"] == pytest.approx(0.0)


def test_two_way_cluster_bootstrap_resamples_country_and_time() -> None:
    rows = []
    for origin in [2000, 2005, 2010]:
        for city_id, country, difference in [(1, "A", -0.01), (2, "B", 0.02), (3, "C", -0.02)]:
            for model, error in [
                ("persistence", 0.05 + difference),
                ("country_mean_leave_city_out", 0.05),
            ]:
                rows.append(
                    {
                        "city_id": city_id, "country_code": country, "origin": origin,
                        "model": model, "absolute_error": error,
                    }
                )
    errors = pd.DataFrame(rows)
    first = two_way_cluster_bootstrap_paired_difference(errors, repetitions=200, seed=9)
    second = two_way_cluster_bootstrap_paired_difference(errors, repetitions=200, seed=9)
    pd.testing.assert_frame_equal(first, second)
    assert first.loc[0, "countries"] == 3
    assert first.loc[0, "time_clusters"] == 3


def test_temporal_diagnostics_detect_reversal() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 2, 3, 4], "country_code": ["A", "A", "B", "B"],
            "period_start": [2020] * 4,
            "recent_growth": [0.01, 0.02, -0.01, -0.02],
            "future_growth": [-0.01, -0.02, 0.01, 0.02],
        }
    )
    result = temporal_reversal_diagnostics(panel)
    assert result.loc[0, "pearson_correlation"] == pytest.approx(-1.0)
    assert result.loc[0, "within_country_correlation"] == pytest.approx(-1.0)
    assert result.loc[0, "reversal_rate_nonzero"] == 1.0


def test_leave_one_country_out_identifies_influential_cluster() -> None:
    rows = []
    for city_id, country, difference in [(1, "A", 0.01), (2, "A", 0.01), (3, "B", -0.03)]:
        for model, error in [
            ("persistence", 0.10 + difference), ("country_mean", 0.10)
        ]:
            rows.append(
                {
                    "city_id": city_id, "origin": 2020, "country_code": country,
                    "model": model, "absolute_error": error,
                }
            )
    result = leave_one_cluster_out_paired_difference(pd.DataFrame(rows), origin=2020)
    assert result.loc[0, "country_code"] == "A"
    assert result.loc[0, "excluded_mean_difference"] == pytest.approx(-0.03)
    assert result.loc[0, "exclusion_shift"] == pytest.approx(-0.0266666667)


def test_locked_origin_selection_does_not_choose_on_locked_outcome() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000, 2005, 2010] * 2,
            "model": ["stable"] * 3 + ["shock_winner"] * 3,
            "absolute_error": [0.10, 0.10, 0.30, 0.20, 0.20, 0.01],
        }
    )
    result = locked_origin_model_evaluation(errors, locked_origin=2010)
    assert result.loc[0, "selected_model"] == "stable"
    assert result.loc[0, "hindsight_best_model"] == "shock_winner"
    assert result.loc[0, "locked_rank"] == 2
    assert result.loc[0, "selection_regret"] == pytest.approx(0.29)
    assert result.loc[0, "hindsight_best_is_diagnostic_only"]


def test_locked_origin_cannot_enter_development_set() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2005, 2010],
            "model": ["m", "m"],
            "absolute_error": [0.10, 0.20],
        }
    )
    with pytest.raises(SourceSchemaError, match="cannot be used"):
        locked_origin_model_evaluation(
            errors, locked_origin=2010, development_origins=[2005, 2010]
        )


def test_sequential_intervals_use_only_prior_origins() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000, 2000, 2005, 2005, 2010, 2010],
            "model": ["m"] * 6,
            "country_code": ["A", "B"] * 3,
            "error": [0.10, -0.20, 0.20, -0.30, 99.0, -99.0],
            "absolute_error": [0.10, 0.20, 0.20, 0.30, 99.0, 99.0],
        }
    )
    result = sequential_interval_calibration(
        errors,
        miscoverage=0.50,
        minimum_calibration_rows=2,
        minimum_calibration_origins=1,
    )
    at_2005 = result.loc[result["origin"].eq(2005)].iloc[0]
    assert at_2005["interval_radius"] == pytest.approx(0.20)
    assert at_2005["calibration_origin_end"] == 2000
    assert not at_2005["calibration_uses_current_or_future_origin"]


def test_sequential_intervals_report_city_and_equal_country_coverage() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000] * 4 + [2005] * 3,
            "model": ["m"] * 7,
            "country_code": ["A", "A", "B", "B", "A", "A", "B"],
            "error": [0.10, -0.10, 0.10, -0.10, 0.05, 0.20, -0.20],
            "absolute_error": [0.10, 0.10, 0.10, 0.10, 0.05, 0.20, 0.20],
        }
    )
    result = sequential_interval_calibration(
        errors,
        miscoverage=0.50,
        minimum_calibration_rows=4,
        minimum_calibration_origins=1,
    )
    row = result.iloc[0]
    assert row["interval_radius"] == pytest.approx(0.10)
    assert row["empirical_city_coverage"] == pytest.approx(1 / 3)
    assert row["equal_country_coverage"] == pytest.approx(0.25)
    assert row["interval_width"] == pytest.approx(0.20)
    assert row["lower_tail_miss_rate"] == pytest.approx(1 / 3)
    assert row["upper_tail_miss_rate"] == pytest.approx(1 / 3)
    assert row["tail_miss_imbalance"] == pytest.approx(0.0)
    assert row["equal_country_lower_tail_miss_rate"] == pytest.approx(0.25)
    assert row["equal_country_upper_tail_miss_rate"] == pytest.approx(0.50)


def test_sequential_interval_uses_exact_conformal_order_statistic() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000] * 4 + [2005],
            "model": ["m"] * 5,
            "country_code": ["A", "B", "C", "D", "A"],
            "error": [0.10, -0.20, 0.30, -0.40, 0.25],
            "absolute_error": [0.10, 0.20, 0.30, 0.40, 0.25],
        }
    )
    result = sequential_interval_calibration(
        errors,
        miscoverage=0.50,
        minimum_calibration_rows=4,
        minimum_calibration_origins=1,
    )
    assert result.loc[0, "calibration_order_statistic_rank"] == 3
    assert result.loc[0, "interval_radius"] == pytest.approx(0.30)


def test_registered_interval_policy_freezes_strata_and_parameters() -> None:
    rows = []
    for origin in [2000, 2005, 2010]:
        for city_id in range(120):
            rows.append(
                {
                    "origin": origin,
                    "model": "m",
                    "country_code": f"C{city_id % 10}",
                    "size_bin": "50–150k",
                    "error": 0.01 + city_id / 100_000,
                    "absolute_error": 0.01 + city_id / 100_000,
                }
            )
    result = registered_sequential_interval_calibration(
        pd.DataFrame(rows), policy_id="size_bin_90_v1"
    )
    assert result["calibration_policy_id"].eq("size_bin_90_v1").all()
    assert result["stratification_prespecified"].all()
    assert result["nominal_coverage"].eq(0.90).all()
    assert result["size_bin"].eq("50–150k").all()


def test_registered_interval_policy_rejects_analyst_defined_name() -> None:
    errors = pd.DataFrame(
        {
            "origin": [2000],
            "model": ["m"],
            "country_code": ["A"],
            "absolute_error": [0.10],
        }
    )
    with pytest.raises(SourceSchemaError, match="Unknown registered"):
        registered_sequential_interval_calibration(
            errors, policy_id="post_hoc_underperforming_region"
        )


def test_recent_origin_calibration_excludes_stale_residuals() -> None:
    rows = []
    for origin, error in [
        (1990, 9.0),
        (1995, 8.0),
        (2000, 0.10),
        (2005, 0.20),
        (2010, 0.30),
        (2015, 0.25),
    ]:
        for city_id in range(100):
            rows.append(
                {
                    "origin": origin,
                    "model": "m",
                    "country_code": f"C{city_id % 10}",
                    "error": error,
                    "absolute_error": error,
                }
            )
    result = registered_sequential_interval_calibration(
        pd.DataFrame(rows), policy_id="overall_90_recent3_v1"
    )
    final = result.loc[result["origin"].eq(2015)].iloc[0]
    assert final["calibration_origin_start"] == 2000
    assert final["calibration_origin_end"] == 2010
    assert final["calibration_origins"] == 3
    assert final["maximum_calibration_origins"] == 3
    assert final["interval_radius"] == pytest.approx(0.30)


def test_equal_country_calibration_prevents_large_country_dominance() -> None:
    rows = []
    for origin in [2000, 2005]:
        for city_id in range(50):
            rows.append(
                {
                    "origin": origin,
                    "model": "m",
                    "country_code": "LARGE",
                    "error": 0.10,
                    "absolute_error": 0.10,
                }
            )
        rows.append(
            {
                "origin": origin,
                "model": "m",
                "country_code": "SMALL",
                "error": 1.00,
                "absolute_error": 1.00,
            }
        )
    rows.extend(
        [
            {
                "origin": 2010,
                "model": "m",
                "country_code": country,
                "error": 0.20,
                "absolute_error": 0.20,
            }
            for country in ["LARGE", "SMALL"]
        ]
    )
    errors = pd.DataFrame(rows)
    city = registered_sequential_interval_calibration(
        errors, policy_id="overall_90_v1"
    )
    country = registered_sequential_interval_calibration(
        errors, policy_id="overall_90_equal_country_v1"
    )
    city_final = city.loc[city["origin"].eq(2010)].iloc[0]
    country_final = country.loc[country["origin"].eq(2010)].iloc[0]
    assert city_final["interval_radius"] == pytest.approx(0.10)
    assert country_final["interval_radius"] == pytest.approx(1.00)
    assert country_final["calibration_weighting"] == "equal_country"
    assert not country_final["finite_sample_conformal_rank_applied"]

"""Generate WUP rolling-origin baseline metrics from registered local workbooks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.adapters.wup import (
    read_f01_country_city_population,
    read_f21_city_population,
    read_f25_city_land_area,
    read_f30_built_up_area_per_capita,
    read_f34_population_density,
)
from urban_growth.forecast import (
    attach_national_city_category_baseline,
    balanced_origin_cohort,
    build_forecast_intervals,
    cluster_bootstrap_paired_difference,
    equal_country_forecast_metrics,
    equal_country_origin_forecast_metrics,
    equal_origin_forecast_metrics,
    evaluate_rolling_baselines,
    evaluate_rolling_hierarchy_models,
    leave_one_cluster_out_paired_difference,
    locked_origin_model_evaluation,
    paired_error_comparison,
    registered_sequential_interval_calibration,
    rolling_baseline_errors,
    temporal_reversal_diagnostics,
    two_way_cluster_bootstrap_paired_difference,
)
from urban_growth.selection import (
    outcome_attrition_summary,
    selection_summary,
    wup_forecast_selection_ledger,
)
from urban_growth.wup_lineage import classify_wup_city_population_lineage
from urban_growth.wup_panel import build_wup_city_year_panel

OBSERVED_PANEL_ORIGINS = list(range(1980, 2020, 5))
OBSERVED_SCORING_ORIGINS = list(range(1985, 2020, 5))
ALL_PUBLISHED_ORIGINS = list(range(1980, 2025, 5))


def _label_projection_sensitivity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["outcome_empirical_lineage"] = "crisp_projection"
    out["headline_eligible"] = False
    out["interpretation"] = (
        "2020-to-2025 WUP projection sensitivity; not an observed-outcome forecast test"
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/wup_baseline_metrics.csv")
    )
    parser.add_argument(
        "--selection-ledger-output",
        type=Path,
        default=Path("outputs/wup_selection_ledger.csv"),
    )
    parser.add_argument(
        "--selection-summary-output",
        type=Path,
        default=Path("outputs/wup_selection_summary.csv"),
    )
    parser.add_argument(
        "--outcome-attrition-output",
        type=Path,
        default=Path("outputs/wup_outcome_attrition.csv"),
    )
    parser.add_argument(
        "--paired-output",
        type=Path,
        default=Path("outputs/wup_persistence_vs_country_by_size.csv"),
    )
    parser.add_argument(
        "--bootstrap-output",
        type=Path,
        default=Path("outputs/wup_country_cluster_bootstrap_by_size.csv"),
    )
    parser.add_argument(
        "--pooled-paired-output",
        type=Path,
        default=Path("outputs/wup_persistence_vs_country_pooled_by_size.csv"),
    )
    parser.add_argument(
        "--pooled-bootstrap-output",
        type=Path,
        default=Path("outputs/wup_country_cluster_bootstrap_pooled_by_size.csv"),
    )
    parser.add_argument(
        "--temporal-output",
        type=Path,
        default=Path("outputs/wup_temporal_reversal_diagnostics.csv"),
    )
    parser.add_argument(
        "--country-influence-output",
        type=Path,
        default=Path("outputs/wup_2020_country_influence.csv"),
    )
    parser.add_argument(
        "--city-influence-output",
        type=Path,
        default=Path("outputs/wup_2020_city_influence.csv"),
    )
    parser.add_argument(
        "--gapped-metrics-output",
        type=Path,
        default=Path("outputs/wup_gapped_baseline_metrics.csv"),
    )
    parser.add_argument(
        "--gapped-temporal-output",
        type=Path,
        default=Path("outputs/wup_gapped_temporal_diagnostics.csv"),
    )
    parser.add_argument(
        "--hierarchy-output",
        type=Path,
        default=Path("outputs/wup_hierarchy_model_metrics.csv"),
    )
    parser.add_argument(
        "--balanced-metrics-output",
        type=Path,
        default=Path("outputs/wup_balanced_cohort_metrics.csv"),
    )
    parser.add_argument(
        "--equal-country-output",
        type=Path,
        default=Path("outputs/wup_equal_country_metrics.csv"),
    )
    parser.add_argument(
        "--balanced-equal-country-output",
        type=Path,
        default=Path("outputs/wup_balanced_equal_country_metrics.csv"),
    )
    parser.add_argument(
        "--pooled-equal-country-output",
        type=Path,
        default=Path("outputs/wup_equal_country_pooled_metrics.csv"),
    )
    parser.add_argument(
        "--equal-origin-output",
        type=Path,
        default=Path("outputs/wup_equal_origin_metrics.csv"),
    )
    parser.add_argument(
        "--equal-country-origin-output",
        type=Path,
        default=Path("outputs/wup_equal_country_origin_metrics.csv"),
    )
    parser.add_argument(
        "--balanced-pooled-equal-country-output",
        type=Path,
        default=Path("outputs/wup_balanced_equal_country_pooled_metrics.csv"),
    )
    parser.add_argument(
        "--interval-calibration-output",
        type=Path,
        default=Path("outputs/wup_sequential_interval_calibration.csv"),
    )
    parser.add_argument(
        "--interval-calibration-by-size-output",
        type=Path,
        default=Path("outputs/wup_sequential_interval_calibration_by_size.csv"),
    )
    parser.add_argument(
        "--country-time-bootstrap-output",
        type=Path,
        default=Path("outputs/wup_country_time_bootstrap_overall.csv"),
    )
    parser.add_argument(
        "--country-time-size-bootstrap-output",
        type=Path,
        default=Path("outputs/wup_country_time_bootstrap_by_size.csv"),
    )
    parser.add_argument(
        "--balanced-country-time-bootstrap-output",
        type=Path,
        default=Path("outputs/wup_balanced_country_time_bootstrap_overall.csv"),
    )
    parser.add_argument(
        "--locked-origin-output",
        type=Path,
        default=Path("outputs/wup_2020_locked_origin_evaluation.csv"),
    )
    parser.add_argument(
        "--aggregation-bootstrap-output",
        type=Path,
        default=Path("outputs/wup_aggregation_bootstrap_by_origin.csv"),
    )
    parser.add_argument(
        "--aggregation-country-time-output",
        type=Path,
        default=Path("outputs/wup_aggregation_country_time_bootstrap.csv"),
    )
    args = parser.parse_args()
    raw = args.raw_dir
    national = read_f01_country_city_population(
        raw / "WUP2025-F01-Degree-of-Urbanization_Pop_by_category.xlsx"
    )
    population = classify_wup_city_population_lineage(
        read_f21_city_population(raw / "WUP2025-F21-DEGURBA-Cities_Pop.xlsx")
    )
    area = read_f25_city_land_area(raw / "WUP2025-F25-DEGURBA-Cities_AREA_km2.xlsx")
    built = read_f30_built_up_area_per_capita(
        raw / "WUP2025-F30-DEGURBA-Cities_BU_m2_per_capita.xlsx"
    )
    density = read_f34_population_density(
        raw / "WUP2025-F34-DEGURBA-Cities_Pop_density.xlsx"
    )
    city_year = build_wup_city_year_panel(population, area, built, density)

    selection_ledger = wup_forecast_selection_ledger(
        population, city_year, ALL_PUBLISHED_ORIGINS
    )
    selection_audit_summary = selection_summary(selection_ledger)
    attrition = outcome_attrition_summary(selection_ledger)

    # Headline/observed path: 2025 is excluded because it is a CRISP projection.
    intervals = build_forecast_intervals(city_year, OBSERVED_PANEL_ORIGINS)
    intervals = attach_national_city_category_baseline(intervals, national)
    metrics = evaluate_rolling_baselines(intervals, OBSERVED_SCORING_ORIGINS)
    errors = rolling_baseline_errors(intervals, OBSERVED_SCORING_ORIGINS)
    paired = paired_error_comparison(errors)
    bootstrap = cluster_bootstrap_paired_difference(errors)
    pooled_paired = paired_error_comparison(errors, group_columns=["size_bin"])
    pooled_bootstrap = cluster_bootstrap_paired_difference(
        errors, group_columns=["size_bin"]
    )
    temporal = temporal_reversal_diagnostics(intervals)

    # Preserve the former 2020 apparatus only as an explicitly non-headline
    # projection sensitivity. It scores 2020->2025 against the CRISP endpoint.
    projection_intervals = build_forecast_intervals(
        city_year,
        ALL_PUBLISHED_ORIGINS,
        allowed_outcome_types={"estimate", "projection"},
    )
    projection_intervals = attach_national_city_category_baseline(
        projection_intervals, national
    )
    projection_errors = rolling_baseline_errors(projection_intervals, [2020])
    country_influence = _label_projection_sensitivity(
        leave_one_cluster_out_paired_difference(projection_errors, origin=2020)
    )
    city_influence = _label_projection_sensitivity(
        leave_one_cluster_out_paired_difference(
            projection_errors,
            origin=2020,
            cluster_columns=["country_code", "city_id", "city_name"],
        )
    )
    locked_origin = _label_projection_sensitivity(
        locked_origin_model_evaluation(projection_errors, locked_origin=2020)
    )

    gapped_intervals = build_forecast_intervals(
        city_year, OBSERVED_PANEL_ORIGINS, outcome_gap_years=5
    )
    gapped_intervals = attach_national_city_category_baseline(gapped_intervals, national)
    gapped_metrics = evaluate_rolling_baselines(
        gapped_intervals, list(range(1990, 2020, 5))
    )
    gapped_temporal = temporal_reversal_diagnostics(gapped_intervals)
    hierarchy = evaluate_rolling_hierarchy_models(intervals, OBSERVED_SCORING_ORIGINS)
    balanced = balanced_origin_cohort(intervals, OBSERVED_PANEL_ORIGINS)
    balanced_metrics = evaluate_rolling_baselines(balanced, OBSERVED_SCORING_ORIGINS)
    balanced_errors = rolling_baseline_errors(balanced, OBSERVED_SCORING_ORIGINS)
    equal_country = equal_country_forecast_metrics(errors, group_columns=["origin"])
    balanced_equal_country = equal_country_forecast_metrics(
        balanced_errors, group_columns=["origin"]
    )
    pooled_equal_country = equal_country_forecast_metrics(errors)
    equal_origin = equal_origin_forecast_metrics(errors)
    equal_country_origin = equal_country_origin_forecast_metrics(errors)
    balanced_pooled_equal_country = equal_country_forecast_metrics(balanced_errors)
    interval_calibration = pd.concat(
        [
            registered_sequential_interval_calibration(errors, policy_id="overall_90_v1"),
            registered_sequential_interval_calibration(
                errors, policy_id="overall_90_recent3_v1"
            ),
            registered_sequential_interval_calibration(
                errors, policy_id="overall_90_equal_country_v1"
            ),
        ],
        ignore_index=True,
    )
    interval_calibration_by_size = pd.concat(
        [
            registered_sequential_interval_calibration(errors, policy_id="size_bin_90_v1"),
            registered_sequential_interval_calibration(
                errors, policy_id="size_bin_90_recent3_v1"
            ),
            registered_sequential_interval_calibration(
                errors, policy_id="size_bin_90_equal_country_v1"
            ),
        ],
        ignore_index=True,
    )
    country_time_bootstrap = two_way_cluster_bootstrap_paired_difference(errors)
    country_time_size_bootstrap = two_way_cluster_bootstrap_paired_difference(
        errors,
        model_b="country_mean",
        group_columns=["size_bin"],
    )
    balanced_country_time_bootstrap = two_way_cluster_bootstrap_paired_difference(
        balanced_errors
    )
    aggregation_pairs = [
        ("country_mean_leave_city_out", "subregion_mean_leave_city_out"),
        ("subregion_mean_leave_city_out", "region_mean_leave_city_out"),
        ("region_mean_leave_city_out", "global_mean_leave_city_out"),
    ]
    aggregation_bootstrap = pd.concat(
        [
            cluster_bootstrap_paired_difference(
                errors, model_a=model_a, model_b=model_b, group_columns=["origin"]
            )
            for model_a, model_b in aggregation_pairs
        ],
        ignore_index=True,
    )
    aggregation_country_time = pd.concat(
        [
            two_way_cluster_bootstrap_paired_difference(
                errors, model_a=model_a, model_b=model_b
            )
            for model_a, model_b in aggregation_pairs
        ],
        ignore_index=True,
    )

    outputs = [
        (args.output, metrics),
        (args.selection_ledger_output, selection_ledger),
        (args.selection_summary_output, selection_audit_summary),
        (args.outcome_attrition_output, attrition),
        (args.paired_output, paired),
        (args.bootstrap_output, bootstrap),
        (args.pooled_paired_output, pooled_paired),
        (args.pooled_bootstrap_output, pooled_bootstrap),
        (args.temporal_output, temporal),
        (args.country_influence_output, country_influence),
        (args.city_influence_output, city_influence),
        (args.gapped_metrics_output, gapped_metrics),
        (args.gapped_temporal_output, gapped_temporal),
        (args.hierarchy_output, hierarchy),
        (args.balanced_metrics_output, balanced_metrics),
        (args.equal_country_output, equal_country),
        (args.balanced_equal_country_output, balanced_equal_country),
        (args.pooled_equal_country_output, pooled_equal_country),
        (args.equal_origin_output, equal_origin),
        (args.equal_country_origin_output, equal_country_origin),
        (args.balanced_pooled_equal_country_output, balanced_pooled_equal_country),
        (args.locked_origin_output, locked_origin),
        (args.interval_calibration_output, interval_calibration),
        (args.interval_calibration_by_size_output, interval_calibration_by_size),
        (args.country_time_bootstrap_output, country_time_bootstrap),
        (args.country_time_size_bootstrap_output, country_time_size_bootstrap),
        (args.balanced_country_time_bootstrap_output, balanced_country_time_bootstrap),
        (args.aggregation_bootstrap_output, aggregation_bootstrap),
        (args.aggregation_country_time_output, aggregation_country_time),
    ]
    for path, frame in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

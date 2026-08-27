"""Generate WUP rolling-origin baseline metrics from registered local workbooks."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f25_city_land_area,
    read_f30_built_up_area_per_capita,
    read_f34_population_density,
)
from urban_growth.forecast import (
    build_forecast_intervals,
    cluster_bootstrap_paired_difference,
    evaluate_rolling_baselines,
    leave_one_cluster_out_paired_difference,
    paired_error_comparison,
    rolling_baseline_errors,
    temporal_reversal_diagnostics,
)
from urban_growth.wup_panel import build_wup_city_year_panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/wup_baseline_metrics.csv")
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
    args = parser.parse_args()
    raw = args.raw_dir
    population = read_f21_city_population(raw / "WUP2025-F21-DEGURBA-Cities_Pop.xlsx")
    area = read_f25_city_land_area(raw / "WUP2025-F25-DEGURBA-Cities_AREA_km2.xlsx")
    built = read_f30_built_up_area_per_capita(
        raw / "WUP2025-F30-DEGURBA-Cities_BU_m2_per_capita.xlsx"
    )
    density = read_f34_population_density(
        raw / "WUP2025-F34-DEGURBA-Cities_Pop_density.xlsx"
    )
    city_year = build_wup_city_year_panel(population, area, built, density)
    intervals = build_forecast_intervals(city_year, list(range(1980, 2025, 5)))
    metrics = evaluate_rolling_baselines(intervals, list(range(1985, 2025, 5)))
    errors = rolling_baseline_errors(intervals, list(range(1985, 2025, 5)))
    paired = paired_error_comparison(errors)
    bootstrap = cluster_bootstrap_paired_difference(errors)
    temporal = temporal_reversal_diagnostics(intervals)
    country_influence = leave_one_cluster_out_paired_difference(errors, origin=2020)
    city_influence = leave_one_cluster_out_paired_difference(
        errors, origin=2020, cluster_columns=["country_code", "city_id", "city_name"]
    )
    gapped_intervals = build_forecast_intervals(
        city_year, list(range(1980, 2020, 5)), outcome_gap_years=5
    )
    gapped_metrics = evaluate_rolling_baselines(
        gapped_intervals, list(range(1990, 2020, 5))
    )
    gapped_temporal = temporal_reversal_diagnostics(gapped_intervals)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.output, index=False)
    args.paired_output.parent.mkdir(parents=True, exist_ok=True)
    paired.to_csv(args.paired_output, index=False)
    args.bootstrap_output.parent.mkdir(parents=True, exist_ok=True)
    bootstrap.to_csv(args.bootstrap_output, index=False)
    args.temporal_output.parent.mkdir(parents=True, exist_ok=True)
    temporal.to_csv(args.temporal_output, index=False)
    args.country_influence_output.parent.mkdir(parents=True, exist_ok=True)
    country_influence.to_csv(args.country_influence_output, index=False)
    args.city_influence_output.parent.mkdir(parents=True, exist_ok=True)
    city_influence.to_csv(args.city_influence_output, index=False)
    args.gapped_metrics_output.parent.mkdir(parents=True, exist_ok=True)
    gapped_metrics.to_csv(args.gapped_metrics_output, index=False)
    args.gapped_temporal_output.parent.mkdir(parents=True, exist_ok=True)
    gapped_temporal.to_csv(args.gapped_temporal_output, index=False)
    print(args.output)
    print(args.paired_output)
    print(args.bootstrap_output)
    print(args.temporal_output)
    print(args.country_influence_output)
    print(args.city_influence_output)
    print(args.gapped_metrics_output)
    print(args.gapped_temporal_output)


if __name__ == "__main__":
    main()

"""Evaluate persistence against same-origin leave-city-out country recent growth."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f25_city_land_area,
    read_f30_built_up_area_per_capita,
    read_f34_population_density,
)
from urban_growth.contemporaneous_baseline import (
    contemporaneous_country_baseline_errors,
    evaluate_contemporaneous_country_baseline,
    evaluate_contemporaneous_country_h1_hierarchy,
)
from urban_growth.forecast import (
    build_forecast_intervals,
    cluster_bootstrap_paired_difference,
    two_way_cluster_bootstrap_paired_difference,
)
from urban_growth.wup_lineage import classify_wup_city_population_lineage
from urban_growth.wup_panel import build_wup_city_year_panel

OBSERVED_PANEL_ORIGINS = list(range(1980, 2020, 5))
OBSERVED_SCORING_ORIGINS = list(range(1985, 2020, 5))
PEER_MODEL = "country_contemporaneous_recent_growth_leave_city_out"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("outputs/wup_contemporaneous_country_metrics.csv"),
    )
    parser.add_argument(
        "--bootstrap-output",
        type=Path,
        default=Path("outputs/wup_contemporaneous_country_bootstrap.csv"),
    )
    parser.add_argument(
        "--country-time-bootstrap-output",
        type=Path,
        default=Path("outputs/wup_contemporaneous_country_time_bootstrap.csv"),
    )
    parser.add_argument(
        "--hierarchy-output",
        type=Path,
        default=Path("outputs/wup_contemporaneous_country_h1_hierarchy.csv"),
    )
    args = parser.parse_args()
    raw = args.raw_dir
    population = classify_wup_city_population_lineage(
        read_f21_city_population(raw / "WUP2025-F21-DEGURBA-Cities_Pop.xlsx")
    )
    city_year = build_wup_city_year_panel(
        population,
        read_f25_city_land_area(raw / "WUP2025-F25-DEGURBA-Cities_AREA_km2.xlsx"),
        read_f30_built_up_area_per_capita(raw / "WUP2025-F30-DEGURBA-Cities_BU_m2_per_capita.xlsx"),
        read_f34_population_density(raw / "WUP2025-F34-DEGURBA-Cities_Pop_density.xlsx"),
    )
    intervals = build_forecast_intervals(city_year, OBSERVED_PANEL_ORIGINS)
    scoring = intervals.loc[intervals["period_start"].isin(OBSERVED_SCORING_ORIGINS)].copy()
    metrics = evaluate_contemporaneous_country_baseline(scoring)
    hierarchy = evaluate_contemporaneous_country_h1_hierarchy(
        intervals,
        OBSERVED_SCORING_ORIGINS,
    )
    errors = contemporaneous_country_baseline_errors(scoring)
    bootstrap = cluster_bootstrap_paired_difference(
        errors,
        model_a="persistence",
        model_b=PEER_MODEL,
        group_columns=["origin"],
    )
    country_time = two_way_cluster_bootstrap_paired_difference(
        errors,
        model_a="persistence",
        model_b=PEER_MODEL,
    )
    for path, frame in [
        (args.metrics_output, metrics),
        (args.bootstrap_output, bootstrap),
        (args.country_time_bootstrap_output, country_time),
        (args.hierarchy_output, hierarchy),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

"""Evaluate the archived WUP 2018 city forecast against WUP 2025 estimates."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f22_2018_city_population,
)
from urban_growth.vintage import (
    evaluate_wup2018_vintage,
    reciprocal_nearest_crosswalk,
    vintage_country_weighting_diagnostics,
    vintage_crosswalk_coverage,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--metrics-output", type=Path, default=Path("outputs/wup2018_vintage_metrics.csv")
    )
    parser.add_argument(
        "--bootstrap-output",
        type=Path,
        default=Path("outputs/wup2018_vintage_country_bootstrap.csv"),
    )
    parser.add_argument(
        "--crosswalk-output",
        type=Path,
        default=Path("outputs/wup2018_vintage_crosswalk.csv"),
    )
    parser.add_argument(
        "--coverage-output",
        type=Path,
        default=Path("outputs/wup2018_vintage_match_coverage.csv"),
    )
    parser.add_argument(
        "--country-coverage-output",
        type=Path,
        default=Path("outputs/wup2018_vintage_country_coverage.csv"),
    )
    parser.add_argument(
        "--country-weighting-output",
        type=Path,
        default=Path("outputs/wup2018_vintage_country_weighting.csv"),
    )
    parser.add_argument(
        "--country-influence-output",
        type=Path,
        default=Path("outputs/wup2018_vintage_country_influence.csv"),
    )
    args = parser.parse_args()
    vintage = read_f22_2018_city_population(
        args.raw_dir / "WUP2018-F22-Cities_Over_300K_Annual.xls"
    )
    current = read_f21_city_population(
        args.raw_dir / "WUP2025-F21-DEGURBA-Cities_Pop.xlsx"
    )
    crosswalk = reciprocal_nearest_crosswalk(vintage, current)
    coverage, country_coverage = vintage_crosswalk_coverage(vintage, crosswalk)
    country_weighting, country_influence = vintage_country_weighting_diagnostics(
        vintage, current, crosswalk
    )
    metric_frames = []
    bootstrap_frames = []
    for horizon in range(1, 6):
        horizon_metrics, horizon_bootstrap = evaluate_wup2018_vintage(
            vintage, current, crosswalk, horizon_years=horizon
        )
        horizon_bootstrap.insert(0, "horizon_years", horizon)
        horizon_bootstrap.insert(0, "target_end", 2018 + horizon)
        horizon_bootstrap.insert(0, "origin", 2018)
        metric_frames.append(horizon_metrics)
        bootstrap_frames.append(horizon_bootstrap)
    metrics = pd.concat(metric_frames, ignore_index=True)
    bootstrap = pd.concat(bootstrap_frames, ignore_index=True)
    for path, frame in [
        (args.metrics_output, metrics),
        (args.bootstrap_output, bootstrap),
        (args.crosswalk_output, crosswalk),
        (args.coverage_output, coverage),
        (args.country_coverage_output, country_coverage),
        (args.country_weighting_output, country_weighting),
        (args.country_influence_output, country_influence),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

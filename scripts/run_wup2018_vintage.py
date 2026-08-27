"""Evaluate the archived WUP 2018 city forecast against WUP 2025 estimates."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f22_2018_city_population,
)
from urban_growth.vintage import evaluate_wup2018_vintage, reciprocal_nearest_crosswalk


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
    args = parser.parse_args()
    vintage = read_f22_2018_city_population(
        args.raw_dir / "WUP2018-F22-Cities_Over_300K_Annual.xls"
    )
    current = read_f21_city_population(
        args.raw_dir / "WUP2025-F21-DEGURBA-Cities_Pop.xlsx"
    )
    crosswalk = reciprocal_nearest_crosswalk(vintage, current)
    metrics, bootstrap = evaluate_wup2018_vintage(vintage, current, crosswalk)
    for path, frame in [
        (args.metrics_output, metrics),
        (args.bootstrap_output, bootstrap),
        (args.crosswalk_output, crosswalk),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

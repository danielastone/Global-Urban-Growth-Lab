"""Build direct WUP national settlement-envelope tables."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.adapters.wup import read_f01_country_degurb_population
from urban_growth.national_envelope import (
    national_envelope_feature_registry,
    national_envelope_forecast_features,
    national_envelope_intervals,
    national_envelope_summaries,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    panel = read_f01_country_degurb_population(
        args.raw_dir / "WUP2025-F01-Degree-of-Urbanization_Pop_by_category.xlsx"
    )
    intervals = national_envelope_intervals(panel)
    outputs = {
        "national_envelope_panel.csv": panel,
        "national_envelope_intervals.csv": intervals,
        "national_envelope_forecast_features.csv": national_envelope_forecast_features(intervals),
        "national_envelope_summaries.csv": national_envelope_summaries(intervals),
        "national_envelope_feature_registry.csv": national_envelope_feature_registry(),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, frame in outputs.items():
        path = args.output_dir / filename
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

"""Stratify the WUP H1 re-test by documented country population-input basis."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f25_city_land_area,
    read_f30_built_up_area_per_capita,
    read_f34_population_density,
)
from urban_growth.forecast import build_forecast_intervals
from urban_growth.wup_lineage import classify_wup_city_population_lineage
from urban_growth.wup_panel import build_wup_city_year_panel
from urban_growth.wup_source_basis import (
    attach_wup_source_basis,
    evaluate_wup_h1_by_source_basis,
    read_wup_m01_source_metadata,
    source_basis_classification_rows,
)

OBSERVED_PANEL_ORIGINS = list(range(1980, 2020, 5))
OBSERVED_SCORING_ORIGINS = list(range(1985, 2020, 5))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--classification-output",
        type=Path,
        default=Path("outputs/wup_h1_source_basis_classification.csv"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("outputs/wup_h1_source_basis_metrics.csv"),
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
    metadata = read_wup_m01_source_metadata(
        raw / "WUP2025-M01-DataSources-Degree-of-Urbanization.xlsx"
    )
    classified = attach_wup_source_basis(intervals, metadata)
    scoring = classified.loc[classified["period_start"].isin(OBSERVED_SCORING_ORIGINS)].copy()
    classification = source_basis_classification_rows(scoring)
    metrics = evaluate_wup_h1_by_source_basis(
        classified,
        OBSERVED_SCORING_ORIGINS,
    )
    for path, frame in [
        (args.classification_output, classification),
        (args.metrics_output, metrics),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

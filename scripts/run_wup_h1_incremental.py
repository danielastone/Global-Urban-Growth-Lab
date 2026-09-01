"""Evaluate whether recent city growth adds information beyond country context in WUP."""

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
from urban_growth.h1_information import evaluate_country_adjusted_recent_growth_information
from urban_growth.wup_lineage import classify_wup_city_population_lineage
from urban_growth.wup_panel import build_wup_city_year_panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/wup_h1_incremental_recent_growth_by_origin.csv"),
    )
    args = parser.parse_args()

    raw = args.raw_dir
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
    intervals = build_forecast_intervals(city_year, list(range(1980, 2025, 5)))
    result = evaluate_country_adjusted_recent_growth_information(
        intervals,
        list(range(1985, 2025, 5)),
    )
    result["outcome_lineage"] = "WUP_reference_estimate_only"
    result["headline_eligible"] = False
    result["headline_limitation"] = (
        "retrospective WUP revised-history test; changing city definitions and no vintage-correct data"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)


if __name__ == "__main__":
    main()

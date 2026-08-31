"""Build and fitness-gate the strict 2010-2020 U.S. Census place threshold cohort."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.adapters.us_census import (
    build_us_place_boundary_cohort,
    read_2020_place_relationship,
    read_place_population_snapshot,
)
from urban_growth.census_fitness import apply_us_census_place_fitness, us_census_headline_sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--cohort-output",
        type=Path,
        default=Path("outputs/us_census_threshold_cohort.csv"),
    )
    parser.add_argument(
        "--headline-output",
        type=Path,
        default=Path("outputs/us_census_threshold_headline_sample.csv"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("outputs/us_census_threshold_summary.csv"),
    )
    args = parser.parse_args()
    population_2010 = read_place_population_snapshot(
        args.raw_dir / "us_census_2010_place_population.json", year=2010
    )
    population_2020 = read_place_population_snapshot(
        args.raw_dir / "us_census_2020_place_population.json", year=2020
    )
    relationship = read_2020_place_relationship(args.raw_dir / "tab20_place20_place10_natl.txt")
    raw_cohort = build_us_place_boundary_cohort(population_2010, population_2020, relationship)
    cohort = apply_us_census_place_fitness(raw_cohort)
    headline = us_census_headline_sample(raw_cohort)
    summary = pd.DataFrame(
        [
            {
                "country_code": "USA",
                "origin_year": 2010,
                "endpoint_year": 2020,
                "cohort_rows": len(cohort),
                "headline_eligible_rows": int(cohort["headline_eligible"].sum()),
                "growth_eligible_rows": int(cohort["growth_eligible"].sum()),
                "spatial_eligible_rows": int(cohort["spatial_eligible"].sum()),
                "stable_geography_rows": int(cohort["geography_status"].eq("stable").sum()),
                "official_crosswalk_rows": int(
                    cohort["geography_status"].eq("official_crosswalk").sum()
                ),
                "crossed_50000_rows": int(cohort["crossed_50000"].sum()),
                "headline_crossed_50000_rows": int(headline["crossed_50000"].sum()),
                "origin_threshold_uncertain_rows": int(
                    cohort["origin_threshold_band"].eq("threshold_uncertain").sum()
                ),
                "minimum_land_overlap": 0.995,
                "fitness_scope": "us_census_place_2010_2020_threshold_pilot",
                "gate_g2_satisfied": False,
                "gate_note": "US pipeline validation does not satisfy Global South pilot gate",
            }
        ]
    )
    for path, frame in [
        (args.cohort_output, cohort),
        (args.headline_output, headline),
        (args.summary_output, summary),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

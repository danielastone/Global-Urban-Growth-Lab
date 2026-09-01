"""Run the point-estimate dynamic hierarchy on one empirical WUP sample."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f25_city_land_area,
    read_f30_built_up_area_per_capita,
    read_f34_population_density,
)
from urban_growth.dynamic_estimators import (
    common_dynamic_sample,
    estimator_disagreement_report,
    fit_dynamic_hierarchy,
)
from urban_growth.forecast import build_forecast_intervals
from urban_growth.wup_lineage import classify_wup_city_population_lineage
from urban_growth.wup_panel import build_wup_city_year_panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--estimates-output", type=Path,
        default=Path("outputs/wup_dynamic_hierarchy_estimates.csv"),
    )
    parser.add_argument(
        "--disagreement-output", type=Path,
        default=Path("outputs/wup_dynamic_hierarchy_disagreement.csv"),
    )
    parser.add_argument(
        "--sample-audit-output", type=Path,
        default=Path("outputs/wup_dynamic_hierarchy_sample_audit.csv"),
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
    panel = build_wup_city_year_panel(population, area, built, density)
    intervals = build_forecast_intervals(panel, list(range(1980, 2020, 5)))
    if intervals["period_start"].max() >= 2020:
        raise RuntimeError("Observed WUP hierarchy must not include the 2020->2025 CRISP outcome")
    intervals["log_population_start"] = np.log(intervals["population_start"])
    covariates = ["log_population_start", "country_rank_percentile_origin"]
    sample = common_dynamic_sample(
        intervals, outcome="future_growth", lagged_outcome="recent_growth",
        covariates=covariates, period="period_start",
    )
    estimates = fit_dynamic_hierarchy(
        sample, outcome="future_growth", lagged_outcome="recent_growth",
        covariates=covariates, period="period_start",
    )
    estimates["data_revision"] = "WUP_2025_revised_history"
    estimates["outcome_lineage"] = "GHS-WUP-POP_reference_estimate_through_2020"
    estimates["crisp_2025_outcome_excluded"] = True
    estimates["boundary_semantics"] = "WUP changing city definitions"
    estimates["causal_interpretation_permitted"] = False
    estimates["validated_inference"] = False
    estimates["uncertainty_status"] = (
        "point estimates only; corrected-estimator production coverage gate failed"
    )
    disagreement = estimator_disagreement_report(estimates)
    by_period = sample.groupby("period_start", as_index=False).agg(
        rows=("city_id", "size"), cities=("city_id", "nunique"),
        countries=("country_code", "nunique"),
    )
    by_period.insert(0, "scope", "period")
    overall = pd.DataFrame(
        [{
            "scope": "overall", "period_start": pd.NA, "rows": len(sample),
            "cities": sample["city_id"].nunique(),
            "countries": sample["country_code"].nunique(),
        }]
    )
    audit = pd.concat([overall, by_period], ignore_index=True)
    audit["candidate_rows"] = len(intervals)
    audit["candidate_cities"] = intervals["city_id"].nunique()
    audit["candidate_countries"] = intervals["country_code"].nunique()
    audit["row_retention_rate"] = len(sample) / len(intervals)
    audit["city_retention_rate"] = sample["city_id"].nunique() / intervals["city_id"].nunique()
    audit["minimum_periods_per_city"] = sample.groupby("city_id").size().min()
    audit["maximum_periods_per_city"] = sample.groupby("city_id").size().max()
    audit["common_sample_across_estimators"] = True
    audit["crisp_2025_outcome_excluded"] = True
    audit["selection_semantics"] = (
        "requires at least two observations in each forecast-origin half"
    )
    for path, frame in (
        (args.estimates_output, estimates),
        (args.disagreement_output, disagreement),
        (args.sample_audit_output, audit),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

"""Run the persistence-only benchmark on fitness-qualified GHSL fixed histories."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.adapters.ghsl_ucdb import (
    fixed_2025_theme_panel,
    multitemporal_boundary_panel,
    read_ghsl_mtuc_csv,
    read_ghsl_theme_csv,
    reconcile_2025_streams,
)
from urban_growth.forecast import build_ghsl_fixed_forecast_intervals
from urban_growth.forecast_fitness import (
    evaluate_fitness_gated_persistence_baselines,
    fitness_gated_persistence_errors,
)
from urban_growth.ghsl_fitness import apply_ghsl_fixed_forecast_fitness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/GHS_UCDB_THEME_GHSL_GLOBE_R2024A.csv"),
    )
    parser.add_argument(
        "--dynamic-input",
        type=Path,
        default=Path("data/raw/GHS_UCDB_MTUC_GLOBE_R2024A.csv"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_fitness_persistence_metrics.csv"),
    )
    parser.add_argument(
        "--errors-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_fitness_persistence_errors.csv"),
    )
    parser.add_argument(
        "--fitness-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_forecast_fitness.csv"),
    )
    args = parser.parse_args()

    fixed = fixed_2025_theme_panel(read_ghsl_theme_csv(str(args.input)))
    dynamic = multitemporal_boundary_panel(read_ghsl_mtuc_csv(str(args.dynamic_input)))
    reconciliation = reconcile_2025_streams(fixed, dynamic)
    intervals = build_ghsl_fixed_forecast_intervals(
        fixed,
        list(range(1980, 2025, 5)),
        reconciliation=reconciliation,
    )
    fitted = apply_ghsl_fixed_forecast_fitness(intervals)
    origins = list(range(1985, 2025, 5))
    metrics = evaluate_fitness_gated_persistence_baselines(fitted, origins)
    errors = fitness_gated_persistence_errors(fitted, origins)

    for frame in (metrics, errors):
        frame["source_id"] = "ghsl_ucdb_r2024a_v1_2_fixed"
        frame["result_class"] = "retrospective_stable_footprint_sensitivity"
        frame["deployable_at_origin"] = False
        frame["headline_result"] = False
        frame["boundary_information_leakage"] = True

    for path, frame in [
        (args.fitness_output, fitted),
        (args.metrics_output, metrics),
        (args.errors_output, errors),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

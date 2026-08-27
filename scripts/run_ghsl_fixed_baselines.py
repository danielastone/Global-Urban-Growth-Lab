"""Generate rolling baselines only on GHSL fixed-2025 urban-centre polygons."""

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
from urban_growth.forecast import (
    build_ghsl_fixed_forecast_intervals,
    evaluate_rolling_baselines,
    rolling_baseline_errors,
    temporal_reversal_diagnostics,
)


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
        default=Path("outputs/ghsl_fixed_baseline_metrics.csv"),
    )
    parser.add_argument(
        "--errors-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_baseline_errors.csv"),
    )
    parser.add_argument(
        "--temporal-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_temporal_diagnostics.csv"),
    )
    parser.add_argument(
        "--reconciliation-output",
        type=Path,
        default=Path("outputs/ghsl_2025_boundary_reconciliation.csv"),
    )
    args = parser.parse_args()
    fixed = fixed_2025_theme_panel(read_ghsl_theme_csv(str(args.input)))
    dynamic = multitemporal_boundary_panel(read_ghsl_mtuc_csv(str(args.dynamic_input)))
    reconciliation = reconcile_2025_streams(fixed, dynamic)
    intervals = build_ghsl_fixed_forecast_intervals(fixed, list(range(1980, 2025, 5)))
    origins = list(range(1985, 2025, 5))
    metrics = evaluate_rolling_baselines(intervals, origins)
    errors = rolling_baseline_errors(intervals, origins)
    temporal = temporal_reversal_diagnostics(intervals)
    for path, frame in [
        (args.metrics_output, metrics),
        (args.errors_output, errors),
        (args.temporal_output, temporal),
        (args.reconciliation_output, reconciliation),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

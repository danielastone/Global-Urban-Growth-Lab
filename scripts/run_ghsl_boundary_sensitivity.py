"""Compare GHSL fixed and dynamic boundaries on identical city-origin rows."""

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
    build_ghsl_dynamic_forecast_intervals,
    build_ghsl_fixed_forecast_intervals,
    evaluate_rolling_baselines,
    matched_boundary_forecast_panels,
    temporal_reversal_diagnostics,
)
from urban_growth.selection import ghsl_forecast_selection_ledger, selection_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixed-input",
        type=Path,
        default=Path("data/raw/GHS_UCDB_THEME_GHSL_GLOBE_R2024A.csv"),
    )
    parser.add_argument(
        "--dynamic-input",
        type=Path,
        default=Path("data/raw/GHS_UCDB_MTUC_GLOBE_R2024A.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    fixed = fixed_2025_theme_panel(read_ghsl_theme_csv(str(args.fixed_input)))
    dynamic = multitemporal_boundary_panel(read_ghsl_mtuc_csv(str(args.dynamic_input)))
    reconciliation = reconcile_2025_streams(fixed, dynamic)
    origins = list(range(1980, 2025, 5))
    fixed_intervals = build_ghsl_fixed_forecast_intervals(
        fixed, origins, reconciliation=reconciliation
    )
    dynamic_intervals = build_ghsl_dynamic_forecast_intervals(dynamic, origins)
    fixed_selection = ghsl_forecast_selection_ledger(
        fixed, origins, boundary_mode="fixed"
    )
    dynamic_selection = ghsl_forecast_selection_ledger(
        dynamic, origins, boundary_mode="dynamic"
    )
    fixed_matched, dynamic_matched = matched_boundary_forecast_panels(
        fixed_intervals, dynamic_intervals
    )
    evaluation_origins = list(range(1985, 2025, 5))
    results = {
        "ghsl_boundary_fixed_matched_metrics.csv": evaluate_rolling_baselines(
            fixed_matched, evaluation_origins
        ),
        "ghsl_boundary_dynamic_matched_metrics.csv": evaluate_rolling_baselines(
            dynamic_matched, evaluation_origins
        ),
        "ghsl_boundary_fixed_matched_temporal.csv": temporal_reversal_diagnostics(
            fixed_matched
        ),
        "ghsl_boundary_dynamic_matched_temporal.csv": temporal_reversal_diagnostics(
            dynamic_matched
        ),
        "ghsl_boundary_matched_coverage.csv": fixed_matched.groupby("period_start").agg(
            matched_rows=("city_id", "size"), countries=("country_code", "nunique")
        ).reset_index(),
        "ghsl_boundary_fixed_selection_ledger.csv": fixed_selection,
        "ghsl_boundary_fixed_selection_summary.csv": selection_summary(fixed_selection),
        "ghsl_boundary_dynamic_selection_ledger.csv": dynamic_selection,
        "ghsl_boundary_dynamic_selection_summary.csv": selection_summary(dynamic_selection),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in results.items():
        path = args.output_dir / name
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

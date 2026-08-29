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
    evaluate_rolling_hierarchy_models,
    rolling_baseline_errors,
    temporal_reversal_diagnostics,
)
from urban_growth.selection import ghsl_forecast_selection_ledger, selection_summary


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
    parser.add_argument(
        "--gapped-metrics-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_gapped_baseline_metrics.csv"),
    )
    parser.add_argument(
        "--gapped-temporal-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_gapped_temporal_diagnostics.csv"),
    )
    parser.add_argument(
        "--hierarchy-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_hierarchy_model_metrics.csv"),
    )
    parser.add_argument(
        "--selection-ledger-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_selection_ledger.csv"),
    )
    parser.add_argument(
        "--selection-summary-output",
        type=Path,
        default=Path("outputs/ghsl_fixed_selection_summary.csv"),
    )
    args = parser.parse_args()
    fixed = fixed_2025_theme_panel(read_ghsl_theme_csv(str(args.input)))
    dynamic = multitemporal_boundary_panel(read_ghsl_mtuc_csv(str(args.dynamic_input)))
    reconciliation = reconcile_2025_streams(fixed, dynamic)
    construction_origins = list(range(1980, 2025, 5))
    selection_ledger = ghsl_forecast_selection_ledger(
        fixed, construction_origins, boundary_mode="fixed"
    )
    selection_audit_summary = selection_summary(selection_ledger)
    intervals = build_ghsl_fixed_forecast_intervals(
        fixed, construction_origins, reconciliation=reconciliation
    )
    origins = list(range(1985, 2025, 5))
    metrics = evaluate_rolling_baselines(intervals, origins)
    errors = rolling_baseline_errors(intervals, origins)
    temporal = temporal_reversal_diagnostics(intervals)
    gapped_intervals = build_ghsl_fixed_forecast_intervals(
        fixed,
        list(range(1980, 2020, 5)),
        outcome_gap_years=5,
        reconciliation=reconciliation,
    )
    gapped_metrics = evaluate_rolling_baselines(
        gapped_intervals, list(range(1990, 2020, 5))
    )
    gapped_temporal = temporal_reversal_diagnostics(gapped_intervals)
    hierarchy = evaluate_rolling_hierarchy_models(intervals, origins)
    for path, frame in [
        (args.metrics_output, metrics),
        (args.errors_output, errors),
        (args.temporal_output, temporal),
        (args.reconciliation_output, reconciliation),
        (args.gapped_metrics_output, gapped_metrics),
        (args.gapped_temporal_output, gapped_temporal),
        (args.hierarchy_output, hierarchy),
        (args.selection_ledger_output, selection_ledger),
        (args.selection_summary_output, selection_audit_summary),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

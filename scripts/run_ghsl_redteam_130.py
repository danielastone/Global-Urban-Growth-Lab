"""Run GHSL red-team issue #130 diagnostics without replacing historical outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.adapters.ghsl_ucdb import (
    fixed_2025_theme_panel,
    multitemporal_boundary_panel,
    read_ghsl_mtuc_csv,
    read_ghsl_theme_csv,
    reconcile_2025_streams,
)
from urban_growth.adapters.wup import (
    read_f21_city_population,
    read_f25_city_land_area,
    read_f30_built_up_area_per_capita,
    read_f34_population_density,
)
from urban_growth.forecast import (
    build_forecast_intervals,
    build_ghsl_dynamic_forecast_intervals,
    build_ghsl_fixed_forecast_intervals,
    evaluate_rolling_baselines,
    matched_boundary_forecast_panels,
)
from urban_growth.ghsl_redteam import (
    built_up_entanglement_diagnostic,
    origin_defined_fixed_risk_set,
    restrict_pre_projection_origins,
)
from urban_growth.wup_lineage import classify_wup_city_population_lineage
from urban_growth.wup_panel import build_wup_city_year_panel


def _persistence_rows(metrics: pd.DataFrame) -> pd.DataFrame:
    return metrics.loc[metrics["model"].eq("persistence")].copy()


def _persistence_vs_country(metrics: pd.DataFrame, *, source: str) -> pd.DataFrame:
    """Compare persistence with the leave-city-out historical country baseline by origin."""
    models = ["persistence", "country_mean_leave_city_out"]
    subset = metrics.loc[metrics["model"].isin(models), ["origin", "model", "mae", "rmse"]]
    mae = subset.pivot(index="origin", columns="model", values="mae")
    rmse = subset.pivot(index="origin", columns="model", values="rmse")
    if any(model not in mae.columns or model not in rmse.columns for model in models):
        raise ValueError(f"{source} lacks matched persistence/country model metrics")
    out = pd.DataFrame(
        {
            "origin": mae.index.astype(int),
            "source": source,
            "persistence_mae": mae["persistence"].to_numpy(),
            "country_loo_mae": mae["country_mean_leave_city_out"].to_numpy(),
            "persistence_rmse": rmse["persistence"].to_numpy(),
            "country_loo_rmse": rmse["country_mean_leave_city_out"].to_numpy(),
        }
    )
    out["mae_delta_persistence_minus_country"] = (
        out["persistence_mae"] - out["country_loo_mae"]
    )
    out["rmse_delta_persistence_minus_country"] = (
        out["persistence_rmse"] - out["country_loo_rmse"]
    )
    out["persistence_beats_country_mae"] = out[
        "mae_delta_persistence_minus_country"
    ].lt(0)
    out["persistence_beats_country_rmse"] = out[
        "rmse_delta_persistence_minus_country"
    ].lt(0)
    return restrict_pre_projection_origins(out)


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
    parser.add_argument("--wup-raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/ghsl_redteam_130"))
    args = parser.parse_args()

    fixed = fixed_2025_theme_panel(read_ghsl_theme_csv(str(args.fixed_input)))
    dynamic = multitemporal_boundary_panel(read_ghsl_mtuc_csv(str(args.dynamic_input)))
    reconciliation = reconcile_2025_streams(fixed, dynamic)
    origins = list(range(1980, 2025, 5))
    evaluation_origins = list(range(1985, 2025, 5))
    pre_projection_origins = list(range(1985, 2020, 5))

    fixed_intervals = build_ghsl_fixed_forecast_intervals(
        fixed, origins, reconciliation=reconciliation
    )
    dynamic_intervals = build_ghsl_dynamic_forecast_intervals(dynamic, origins)
    fixed_matched, dynamic_matched = matched_boundary_forecast_panels(
        fixed_intervals, dynamic_intervals
    )

    # Finding 14: isolate pre-2020 observed/reference-estimate WUP and GHSL behavior.
    fixed_matched_metrics = evaluate_rolling_baselines(fixed_matched, evaluation_origins)
    dynamic_matched_metrics = evaluate_rolling_baselines(dynamic_matched, evaluation_origins)
    fixed_pre2020 = restrict_pre_projection_origins(_persistence_rows(fixed_matched_metrics))
    dynamic_pre2020 = restrict_pre_projection_origins(_persistence_rows(dynamic_matched_metrics))
    raw = args.wup_raw_dir
    wup_population = classify_wup_city_population_lineage(
        read_f21_city_population(raw / "WUP2025-F21-DEGURBA-Cities_Pop.xlsx")
    )
    wup_city_year = build_wup_city_year_panel(
        wup_population,
        read_f25_city_land_area(raw / "WUP2025-F25-DEGURBA-Cities_AREA_km2.xlsx"),
        read_f30_built_up_area_per_capita(
            raw / "WUP2025-F30-DEGURBA-Cities_BU_m2_per_capita.xlsx"
        ),
        read_f34_population_density(raw / "WUP2025-F34-DEGURBA-Cities_Pop_density.xlsx"),
    )
    wup_intervals = build_forecast_intervals(wup_city_year, list(range(1980, 2020, 5)))
    wup_metrics = evaluate_rolling_baselines(wup_intervals, pre_projection_origins)
    wup_pre2020 = restrict_pre_projection_origins(_persistence_rows(wup_metrics))
    cross_source = (
        wup_pre2020[["origin", "mae", "rmse"]]
        .rename(columns={"mae": "wup_persistence_mae", "rmse": "wup_persistence_rmse"})
        .merge(
            fixed_pre2020[["origin", "mae", "rmse"]].rename(
                columns={"mae": "ghsl_fixed_persistence_mae", "rmse": "ghsl_fixed_persistence_rmse"}
            ),
            on="origin",
            validate="one_to_one",
        )
        .merge(
            dynamic_pre2020[["origin", "mae", "rmse"]].rename(
                columns={"mae": "ghsl_dynamic_persistence_mae", "rmse": "ghsl_dynamic_persistence_rmse"}
            ),
            on="origin",
            validate="one_to_one",
        )
    )
    cross_source["includes_2020_to_2025"] = False
    cross_source["comparison_semantics"] = "source_level_not_city_matched"
    ranking = pd.concat(
        [
            _persistence_vs_country(wup_metrics, source="wup_2025_reference_estimates"),
            _persistence_vs_country(fixed_matched_metrics, source="ghsl_fixed_2025_footprint"),
            _persistence_vs_country(dynamic_matched_metrics, source="ghsl_dynamic_boundaries"),
        ],
        ignore_index=True,
    ).sort_values(["origin", "source"]).reset_index(drop=True)

    # Finding 12: rebuild the fixed risk set from information at the origin.
    fixed_origin_eligible, risk_coverage = origin_defined_fixed_risk_set(
        fixed_intervals, dynamic, minimum_population=50_000
    )
    fixed_origin_metrics = evaluate_rolling_baselines(
        fixed_origin_eligible, pre_projection_origins
    )

    # Compare the origin-defined fixed sample with dynamic rows on the same keys.
    origin_fixed_matched, origin_dynamic_matched = matched_boundary_forecast_panels(
        fixed_origin_eligible, dynamic_intervals
    )
    origin_fixed_matched_metrics = evaluate_rolling_baselines(
        origin_fixed_matched, pre_projection_origins
    )
    origin_dynamic_matched_metrics = evaluate_rolling_baselines(
        origin_dynamic_matched, pre_projection_origins
    )
    common_coverage = origin_fixed_matched.groupby("period_start").agg(
        matched_rows=("city_id", "size"),
        matched_population=("population_start", "sum"),
        countries=("country_code", "nunique"),
    ).reset_index()

    # Finding 13: source-process diagnostic on the origin-defined fixed sample.
    entanglement = built_up_entanglement_diagnostic(fixed_origin_eligible, fixed)
    entanglement = entanglement.loc[entanglement["origin"].isin(pre_projection_origins)].copy()

    results = {
        "wup_persistence_pre2020.csv": wup_pre2020,
        "fixed_matched_persistence_pre2020.csv": fixed_pre2020,
        "dynamic_matched_persistence_pre2020.csv": dynamic_pre2020,
        "cross_source_persistence_pre2020.csv": cross_source,
        "cross_source_model_ranking_pre2020.csv": ranking,
        "fixed_origin_risk_set_coverage.csv": risk_coverage,
        "fixed_origin_defined_metrics.csv": fixed_origin_metrics,
        "fixed_origin_defined_matched_metrics.csv": origin_fixed_matched_metrics,
        "dynamic_origin_defined_matched_metrics.csv": origin_dynamic_matched_metrics,
        "origin_defined_common_coverage.csv": common_coverage,
        "fixed_origin_built_up_entanglement.csv": entanglement,
        "reconciliation_integrity_check.csv": reconciliation.assign(
            reconciliation_semantics="current_epoch_file_integrity_not_temporal_comparability"
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in results.items():
        path = args.output_dir / name
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()

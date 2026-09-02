"""Lineage-clean census density validation with regional-cluster inference."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.density_metrics import attach_density_metric_references
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def census_density_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute census and GHS-POP log densities only on identical supports."""
    required = {
        "city_id", "year", "pilot_region", "census_population", "ghs_population",
        "built_up_surface_m2", "built_up_volume_m3",
        "built_up_surface_annualized_growth", "census_population_support_id",
        "denominator_support_id", "population_status", "geography_status",
    }
    require_columns(frame, required, source_name="census density validation input")
    reject_duplicate_keys(frame, ["city_id", "year"], source_name="census density input")
    out = frame.copy()
    if not out["population_status"].eq("direct_enumeration").all():
        raise SourceSchemaError("Clean census density requires direct enumeration")
    if not out["census_population_support_id"].eq(out["denominator_support_id"]).all():
        raise SourceSchemaError("Census population and built denominator supports must match")
    if not out["geography_status"].isin({"stable", "official_crosswalk"}).all():
        raise SourceSchemaError("Census density requires stable or official-crosswalk geography")
    measures = [
        "census_population", "ghs_population", "built_up_surface_m2", "built_up_volume_m3"
    ]
    numeric = out[measures].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or (numeric <= 0).any().any():
        raise SourceSchemaError("Census density measures must be positive and numeric")
    for column in measures:
        out[column] = numeric[column]
    out["census_pop_per_built_surface"] = np.log(
        out["census_population"] / out["built_up_surface_m2"]
    )
    out["census_pop_per_built_volume"] = np.log(
        out["census_population"] / out["built_up_volume_m3"]
    )
    out["ghs_pop_per_built_surface"] = np.log(
        out["ghs_population"] / out["built_up_surface_m2"]
    )
    out["ghs_pop_per_built_volume"] = np.log(
        out["ghs_population"] / out["built_up_volume_m3"]
    )
    out["ghs_census_log_population_discrepancy"] = np.log(
        out["ghs_population"] / out["census_population"]
    )
    out["city_size_bin"] = pd.cut(
        out["census_population"], [0, 50_000, 100_000, 500_000, np.inf],
        labels=["under_50k", "50k_100k", "100k_500k", "500k_plus"], right=False,
    ).astype("string")
    try:
        out["built_growth_tercile"] = pd.qcut(
            out["built_up_surface_annualized_growth"], 3,
            labels=["low", "middle", "high"], duplicates="raise",
        ).astype("string")
    except ValueError as error:
        raise SourceSchemaError("Built-up growth cannot form three distinct terciles") from error
    return attach_density_metric_references(
        out,
        {
            "census_pop_per_built_surface": "census_pop_per_built_surface",
            "census_pop_per_built_volume": "census_pop_per_built_volume",
            "ghs_pop_per_built_surface": "pop_per_built_surface",
            "ghs_pop_per_built_volume": "pop_per_built_volume",
        },
    )


def _residualize(values: np.ndarray, control: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(control)), control])
    return values - design @ np.linalg.lstsq(design, values, rcond=None)[0]


def _safe_correlation(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 3 or np.std(left) == 0 or np.std(right) == 0:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def _correlations(group: pd.DataFrame, denominator: str) -> tuple[float, float]:
    census = np.log(group["census_population"].to_numpy() / group[denominator].to_numpy())
    ghs = np.log(group["ghs_population"].to_numpy() / group[denominator].to_numpy())
    log_denominator = np.log(group[denominator].to_numpy())
    raw = _safe_correlation(census, ghs)
    partial = _safe_correlation(
        _residualize(census, log_denominator), _residualize(ghs, log_denominator)
    )
    return raw, partial


def density_discrepancy_bootstrap(
    panel: pd.DataFrame,
    *,
    repetitions: int = 2_000,
    seed: int = 20260902,
    confidence: float = 0.95,
    partial_correlation_floor: float = 0.2,
) -> pd.DataFrame:
    """Register discrepancy and correlation intervals resampling pilot regions."""
    required = {
        "city_id", "pilot_region", "city_size_bin", "built_growth_tercile",
        "census_population", "ghs_population", "built_up_surface_m2", "built_up_volume_m3",
        "ghs_census_log_population_discrepancy",
    }
    require_columns(panel, required, source_name="census density panel")
    if repetitions < 100 or not 0 < confidence < 1:
        raise SourceSchemaError("Density bootstrap requires >=100 draws and valid confidence")
    regions = sorted(panel["pilot_region"].dropna().unique())
    if len(regions) < 2:
        raise SourceSchemaError("Density bootstrap requires at least two pilot-region clusters")
    rng = np.random.default_rng(seed)
    alpha = (1 - confidence) / 2
    rows = []
    grouped_samples = [("overall", "all", panel)]
    for stratum in ["city_size_bin", "built_growth_tercile"]:
        grouped_samples.extend(
            (stratum, str(label), group)
            for label, group in panel.groupby(stratum, observed=True)
        )
    for stratum, label, group in grouped_samples:
        group_regions = sorted(group["pilot_region"].unique())
        if len(group_regions) < 2 or len(group) < 4:
            continue
        for metric_id, denominator in [
            ("census_pop_per_built_surface", "built_up_surface_m2"),
            ("census_pop_per_built_volume", "built_up_volume_m3"),
        ]:
            raw, partial = _correlations(group, denominator)
            estimates = []
            raw_draws = []
            partial_draws = []
            for _ in range(repetitions):
                selected = rng.choice(group_regions, len(group_regions), replace=True)
                draw = pd.concat(
                    [group.loc[group["pilot_region"].eq(region)] for region in selected],
                    ignore_index=True,
                )
                estimates.append(draw["ghs_census_log_population_discrepancy"].mean())
                draw_raw, draw_partial = _correlations(draw, denominator)
                raw_draws.append(draw_raw)
                partial_draws.append(draw_partial)
            values = np.asarray(estimates)
            collapse = (
                np.isfinite(raw)
                and np.isfinite(partial)
                and abs(partial) < partial_correlation_floor
                and abs(raw) - abs(partial) >= 0.3
            )
            rows.append({
                "stratification": stratum, "stratum": label, "metric_id": metric_id,
                "n": len(group), "pilot_region_clusters": len(group_regions),
                "mean_log_discrepancy": group[
                    "ghs_census_log_population_discrepancy"
                ].mean(),
                "mean_log_discrepancy_ci_lower": np.quantile(values, alpha),
                "mean_log_discrepancy_ci_upper": np.quantile(values, 1 - alpha),
                "raw_density_correlation": raw,
                "raw_density_correlation_ci_lower": np.nanquantile(raw_draws, alpha),
                "raw_density_correlation_ci_upper": np.nanquantile(raw_draws, 1 - alpha),
                "denominator_partial_correlation": partial,
                "denominator_partial_correlation_ci_lower": np.nanquantile(
                    partial_draws, alpha
                ),
                "denominator_partial_correlation_ci_upper": np.nanquantile(
                    partial_draws, 1 - alpha
                ),
                "denominator_driven": collapse,
                "entangled_metric_evidence_role": (
                    "construction_sensitive_robustness" if collapse else "sensitivity_only"
                ),
                "bootstrap_cluster": "pilot_region", "repetitions": repetitions,
                "seed": seed,
            })
    if not rows:
        raise SourceSchemaError("No density discrepancy stratum has adequate clustered support")
    return pd.DataFrame(rows)


def clean_c3_leave_region_out(intervals: pd.DataFrame) -> pd.DataFrame:
    """Compare prior surface, prior height-proxy, and intercept-only C3 predictions."""
    required = {
        "city_id", "pilot_region", "census_density_annualized_log_change",
        "prior_built_surface_annualized_log_growth", "prior_log_volume_per_surface",
    }
    require_columns(intervals, required, source_name="clean C3 census intervals")
    regions = sorted(intervals["pilot_region"].unique())
    if len(regions) < 3:
        raise SourceSchemaError("Clean C3 leave-region-out requires at least three regions")
    y_column = "census_density_annualized_log_change"
    specifications = {
        "neither_intercept_only": [],
        "prior_built_surface_growth": ["prior_built_surface_annualized_log_growth"],
        "prior_volume_per_surface": ["prior_log_volume_per_surface"],
    }
    rows = []
    for model, predictors in specifications.items():
        errors = []
        for region in regions:
            train = intervals.loc[~intervals["pilot_region"].eq(region)]
            test = intervals.loc[intervals["pilot_region"].eq(region)]
            x_train = np.column_stack([np.ones(len(train)), train[predictors].to_numpy()])
            x_test = np.column_stack([np.ones(len(test)), test[predictors].to_numpy()])
            coefficients = np.linalg.lstsq(x_train, train[y_column].to_numpy(), rcond=None)[0]
            errors.extend(test[y_column].to_numpy() - x_test @ coefficients)
        errors = np.asarray(errors)
        rows.append({
            "model": model, "n": len(errors), "pilot_region_clusters": len(regions),
            "rmse": float(np.sqrt(np.mean(errors**2))),
            "mae": float(np.mean(np.abs(errors))),
            "evaluation": "leave_one_pilot_region_out",
        })
    result = pd.DataFrame(rows)
    baseline = result.loc[result["model"].eq("neither_intercept_only"), "rmse"].iloc[0]
    result["rmse_improvement_vs_neither"] = baseline - result["rmse"]
    return result

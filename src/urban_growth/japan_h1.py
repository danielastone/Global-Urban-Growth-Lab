"""Chronological H1 benchmark on direct Japan Population Census DID counts."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

MODELS = ("prior_origin_mean", "size_only", "persistence", "recent_growth_fitted")
BASELINES = ("prior_origin_mean", "size_only")
RECENT_MODELS = ("persistence", "recent_growth_fitted")
EXCLUSIONS: dict[str, tuple[int, int] | None] = {
    "none": None,
    "exclude_47500_52500": (47_500, 52_500),
    "exclude_45000_55000": (45_000, 55_000),
    "exclude_40000_60000": (40_000, 60_000),
}


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def add_lineage_ids(denominator: pd.DataFrame) -> pd.DataFrame:
    """Connect resolved adjacent DID rows into bootstrap lineages."""
    require_columns(
        denominator,
        {"lag_row_id", "origin_row_id", "endpoint_row_id", "analysis_eligible"},
        source_name="Japan direct-count H1 denominator",
    )
    union = _UnionFind()
    for _, row in denominator.loc[denominator["analysis_eligible"]].iterrows():
        lag = str(row["lag_row_id"])
        origin = str(row["origin_row_id"])
        endpoint = str(row["endpoint_row_id"])
        union.union(lag, origin)
        union.union(origin, endpoint)
    out = denominator.copy()
    out["lineage_id"] = out["origin_row_id"].astype(str).map(union.find)
    return out


def _fit_linear(train: pd.DataFrame, feature: str) -> np.ndarray:
    design = np.column_stack([np.ones(len(train)), train[feature].to_numpy(dtype=float)])
    return np.linalg.lstsq(design, train["future_growth"].to_numpy(dtype=float), rcond=None)[0]


def chronological_predictions(denominator: pd.DataFrame) -> pd.DataFrame:
    """Fit only on earlier forecast origins and predict 2010 and 2015 on common rows."""
    require_columns(
        denominator,
        {
            "locality_id", "lineage_id", "period_start", "population_start",
            "recent_growth", "future_growth", "analysis_eligible",
        },
        source_name="Japan direct-count H1 denominator",
    )
    eligible = denominator.loc[denominator["analysis_eligible"]].copy()
    eligible = eligible.loc[
        np.isfinite(
            eligible[["population_start", "recent_growth", "future_growth"]].to_numpy(dtype=float)
        ).all(axis=1)
    ]
    eligible["log_population_start"] = np.log(eligible["population_start"])
    rows: list[dict[str, object]] = []
    origins = sorted(int(value) for value in eligible["period_start"].unique())
    for origin in origins[1:]:
        train = eligible.loc[eligible["period_start"].lt(origin)]
        test = eligible.loc[eligible["period_start"].eq(origin)]
        if train.empty or test.empty:
            continue
        mean_prediction = float(train["future_growth"].mean())
        size_beta = _fit_linear(train, "log_population_start")
        recent_beta = _fit_linear(train, "recent_growth")
        for _, test_row in test.iterrows():
            predictions = {
                "prior_origin_mean": mean_prediction,
                "size_only": float(
                    size_beta[0] + size_beta[1] * float(test_row["log_population_start"])
                ),
                "persistence": float(test_row["recent_growth"]),
                "recent_growth_fitted": float(
                    recent_beta[0] + recent_beta[1] * float(test_row["recent_growth"])
                ),
            }
            for model, predicted in predictions.items():
                rows.append(
                    {
                        "locality_id": test_row["locality_id"],
                        "lineage_id": test_row["lineage_id"],
                        "origin": origin,
                        "model": model,
                        "actual": float(test_row["future_growth"]),
                        "predicted": predicted,
                        "error": predicted - float(test_row["future_growth"]),
                        "train_origins": ";".join(
                            str(value) for value in sorted(train["period_start"].unique())
                        ),
                        "train_n": len(train),
                    }
                )
    result = pd.DataFrame(rows)
    if result.empty or set(result["origin"].unique()) != set(origins[1:]):
        raise SourceSchemaError("Japan H1 did not produce every chronological test origin")
    reject_duplicate_keys(
        result, ["locality_id", "origin", "model"], source_name="Japan H1 predictions"
    )
    counts = result.pivot_table(index="origin", columns="model", values="locality_id", aggfunc="count")
    if counts.nunique(axis=1).gt(1).any():
        raise SourceSchemaError("Japan H1 models do not share identical test rows")
    return result


def prediction_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (origin, model), group in predictions.groupby(["origin", "model"]):
        error = group["error"].to_numpy(dtype=float)
        rows.append(
            {
                "origin": int(origin),
                "model": model,
                "n": len(group),
                "mae": float(np.mean(np.abs(error))),
                "rmse": float(np.sqrt(np.mean(error**2))),
                "bias": float(np.mean(error)),
                "directional_accuracy": float(
                    np.mean(np.sign(group["predicted"]) == np.sign(group["actual"]))
                ),
            }
        )
    return pd.DataFrame(rows)


def two_way_h1_contrasts(
    predictions: pd.DataFrame, *, draws: int = 2_000, seed: int = 124
) -> pd.DataFrame:
    """Compare fitted recent growth with each baseline by lineage and origin resampling."""
    wide = predictions.pivot(
        index=["locality_id", "lineage_id", "origin", "actual"],
        columns="model",
        values="predicted",
    ).reset_index()
    rng = np.random.default_rng(seed)
    lineages = wide["lineage_id"].unique()
    origins = wide["origin"].unique()
    rows: list[dict[str, object]] = []
    inference_adequate = len(origins) >= 4
    for recent_model in RECENT_MODELS:
        for baseline in BASELINES:
            recent_error = wide[recent_model] - wide["actual"]
            baseline_error = wide[baseline] - wide["actual"]
            recent_rmse = float(np.sqrt(np.mean(recent_error**2)))
            baseline_rmse = float(np.sqrt(np.mean(baseline_error**2)))
            rmse_gain = 1 - recent_rmse / baseline_rmse
            mae_gain = float(np.mean(np.abs(baseline_error)) - np.mean(np.abs(recent_error)))
            bootstrap: list[float] = []
            for _ in range(draws):
                lineage_draw = rng.choice(lineages, size=len(lineages), replace=True)
                origin_draw = rng.choice(origins, size=len(origins), replace=True)
                lineage_weights = pd.Series(lineage_draw).value_counts()
                origin_weights = pd.Series(origin_draw).value_counts()
                weights = (
                    wide["lineage_id"].map(lineage_weights).fillna(0).to_numpy()
                    * wide["origin"].map(origin_weights).fillna(0).to_numpy()
                )
                if weights.sum() == 0:
                    continue
                recent_draw_rmse = np.sqrt(np.average(recent_error**2, weights=weights))
                baseline_draw_rmse = np.sqrt(np.average(baseline_error**2, weights=weights))
                if baseline_draw_rmse > 0:
                    bootstrap.append(float(1 - recent_draw_rmse / baseline_draw_rmse))
            lower, upper = np.quantile(bootstrap, [0.025, 0.975])
            numerical_gate = bool(lower >= 0.05 and mae_gain >= 0)
            rows.append(
                {
                    "recent_model": recent_model,
                    "baseline_model": baseline,
                    "test_n": len(wide),
                    "lineage_clusters": len(lineages),
                    "origin_clusters": len(origins),
                    "origin_cluster_inference_adequate": inference_adequate,
                    "rmse_relative_improvement": rmse_gain,
                    "rmse_relative_improvement_lower_95": float(lower),
                    "rmse_relative_improvement_upper_95": float(upper),
                    "mae_absolute_improvement": mae_gain,
                    "numerical_gate_without_cluster_adequacy": numerical_gate,
                    "registered_gate_pass": bool(inference_adequate and numerical_gate),
                    "gate_status": (
                        "pass"
                        if inference_adequate and numerical_gate
                        else (
                            "insufficient_independent_origin_clusters"
                            if not inference_adequate
                            else "fail"
                        )
                    ),
                    "bootstrap_draws": len(bootstrap),
                    "bootstrap_seed": seed,
                }
            )
    return pd.DataFrame(rows)


def run_japan_h1_hierarchy(
    denominators: dict[str, pd.DataFrame], *, draws: int = 2_000
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames = []
    metric_frames = []
    contrast_frames = []
    coverage_rows = []
    for rule, denominator in denominators.items():
        with_lineage = add_lineage_ids(denominator)
        for exclusion, bounds in EXCLUSIONS.items():
            selected = with_lineage.copy()
            if bounds is not None:
                selected = selected.loc[~selected["population_start"].between(*bounds)]
            coverage_rows.append(
                {
                    "concordance_rule": rule,
                    "threshold_exclusion": exclusion,
                    "origin_denominator_rows": len(selected),
                    "analysis_eligible_rows": int(selected["analysis_eligible"].sum()),
                    "analysis_coverage": float(selected["analysis_eligible"].mean()),
                }
            )
            predictions = chronological_predictions(selected)
            metrics = prediction_metrics(predictions)
            contrasts = two_way_h1_contrasts(predictions, draws=draws)
            for frame in [predictions, metrics, contrasts]:
                frame.insert(0, "threshold_exclusion", exclusion)
                frame.insert(0, "concordance_rule", rule)
            prediction_frames.append(predictions)
            metric_frames.append(metrics)
            contrast_frames.append(contrasts)
    contrasts = pd.concat(contrast_frames, ignore_index=True)
    primary = contrasts.loc[
        contrasts["concordance_rule"].eq("strict_stable_resolved")
        & contrasts["threshold_exclusion"].eq("none")
        & contrasts["recent_model"].eq("persistence")
    ]
    dynamic = contrasts.loc[
        contrasts["concordance_rule"].eq("dynamic_identity_resolved")
        & contrasts["threshold_exclusion"].eq("none")
        & contrasts["recent_model"].eq("persistence")
    ]
    decision = pd.DataFrame(
        [
            {
                "issue": 191,
                "primary_concordance": "strict_stable_resolved",
                "primary_threshold_exclusion": "none",
                "required_baselines": len(BASELINES),
                "baselines_passing_registered_gate": int(primary["registered_gate_pass"].sum()),
                "dynamic_diagnostic_baselines_passing": int(
                    dynamic["registered_gate_pass"].sum()
                ),
                "origin_cluster_inference_adequate": bool(
                    primary["origin_cluster_inference_adequate"].all()
                ),
                "japan_h1_confirmed": bool(primary["registered_gate_pass"].all()),
                "support_boundary_selection_sensitive": bool(
                    primary["registered_gate_pass"].all()
                    and not dynamic["registered_gate_pass"].all()
                ),
                "universal_h1_confirmed": False,
                "decision": (
                    "japan_specific_strict_stability_support_dynamic_not_confirmed"
                    if primary["registered_gate_pass"].all()
                    else (
                        "japan_h1_unresolved_insufficient_independent_origins"
                        if not primary["origin_cluster_inference_adequate"].all()
                        else "japan_h1_not_confirmed_under_registered_gate"
                    )
                ),
            }
        ]
    )
    return (
        pd.DataFrame(coverage_rows),
        pd.concat(prediction_frames, ignore_index=True),
        pd.concat(metric_frames, ignore_index=True),
        contrasts,
        decision,
    )

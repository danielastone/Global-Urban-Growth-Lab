"""Matched direct-count/GHSL diagnostics for the construction-smoothing red team."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

KEYS = ["country_code", "locality_id", "period_start"]
REQUIRED = {
    *KEYS,
    "source",
    "recent_growth",
    "future_growth",
    "analysis_eligible",
    "concordance_quality",
    "census_recency_years",
    "boundary_mode",
}


def _validate(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    require_columns(frame, REQUIRED, source_name=source)
    reject_duplicate_keys(frame, KEYS, source_name=source)
    out = frame.copy()
    if out["source"].nunique() != 1:
        raise SourceSchemaError(f"{source} must contain exactly one source label")
    for column in ["recent_growth", "future_growth", "census_recency_years"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    if out["analysis_eligible"].isna().any():
        raise SourceSchemaError(f"{source} has unknown analysis eligibility")
    out["analysis_eligible"] = out["analysis_eligible"].astype(bool)
    return out


def _metrics(values: pd.DataFrame) -> dict[str, float | int]:
    x = values["recent_growth"].to_numpy(dtype=float)
    y = values["future_growth"].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    intercept, beta = np.linalg.lstsq(design, y, rcond=None)[0]
    persistence_error = y - x
    zero_error = y
    curvature = y - x
    return {
        "matched_analysis_rows": len(values),
        "persistence_intercept": float(intercept),
        "persistence_beta": float(beta),
        "persistence_mae": float(np.mean(np.abs(persistence_error))),
        "persistence_rmse": float(np.sqrt(np.mean(persistence_error**2))),
        "zero_growth_mae": float(np.mean(np.abs(zero_error))),
        "zero_growth_rmse": float(np.sqrt(np.mean(zero_error**2))),
        "mae_improvement_vs_zero": float(
            np.mean(np.abs(zero_error)) - np.mean(np.abs(persistence_error))
        ),
        "rmse_improvement_vs_zero": float(
            np.sqrt(np.mean(zero_error**2)) - np.sqrt(np.mean(persistence_error**2))
        ),
        "sign_reversal_rate": float(np.mean(np.sign(x) != np.sign(y))),
        "mean_growth_curvature": float(np.mean(curvature)),
        "mean_absolute_growth_curvature": float(np.mean(np.abs(curvature))),
    }


def compare_direct_counts_with_ghsl(
    direct: pd.DataFrame,
    ghsl: pd.DataFrame,
    *,
    minimum_periods: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return denominator coverage, source diagnostics, and GHSL-minus-direct contrasts.

    Matching is performed only after each supplied origin denominator is retained. A
    locality-period enters diagnostics only when both sources are eligible and finite.
    At least two distinct forecast origins are required; a two-wave census pilot has
    only one growth interval and cannot identify recent-to-future persistence.
    """
    if minimum_periods < 2:
        raise SourceSchemaError("Construction-smoothing comparison requires at least two origins")
    direct = _validate(direct, "direct-count origin denominator")
    ghsl = _validate(ghsl, "GHSL origin denominator")
    if not direct["source"].eq("direct_count").all():
        raise SourceSchemaError("Direct-count rows must use source=direct_count")
    if ghsl["source"].eq("direct_count").any():
        raise SourceSchemaError("GHSL rows cannot use the direct-count source label")

    coverage_rows: list[dict[str, object]] = []
    for frame in [direct, ghsl]:
        for (source, boundary), group in frame.groupby(["source", "boundary_mode"], dropna=False):
            eligible = group["analysis_eligible"]
            coverage_rows.append(
                {
                    "source": source,
                    "boundary_mode": boundary,
                    "origin_denominator_rows": len(group),
                    "analysis_eligible_rows": int(eligible.sum()),
                    "unresolved_rows": int((~eligible).sum()),
                    "analysis_coverage": float(eligible.mean()),
                    "denominator_defined_before_concordance": True,
                }
            )
    coverage = pd.DataFrame(coverage_rows)

    direct_columns = KEYS + [
        "recent_growth", "future_growth", "analysis_eligible", "concordance_quality",
        "census_recency_years",
    ]
    direct_match = direct[direct_columns].rename(
        columns={column: f"direct_{column}" for column in direct_columns if column not in KEYS}
    )
    matched_parts: list[pd.DataFrame] = []
    for (source, boundary), group in ghsl.groupby(["source", "boundary_mode"], dropna=False):
        joined = direct_match.merge(group, on=KEYS, how="inner", validate="one_to_one")
        usable = (
            joined["direct_analysis_eligible"]
            & joined["analysis_eligible"]
            & joined[["direct_recent_growth", "direct_future_growth", "recent_growth", "future_growth"]]
            .notna().all(axis=1)
        )
        joined = joined.loc[usable].copy()
        joined["ghsl_source"] = source
        joined["ghsl_boundary_mode"] = boundary
        matched_parts.append(joined)
    matched = pd.concat(matched_parts, ignore_index=True) if matched_parts else pd.DataFrame()
    if matched.empty or matched["period_start"].nunique() < minimum_periods:
        periods = 0 if matched.empty else int(matched["period_start"].nunique())
        raise SourceSchemaError(
            f"Direct-count benchmark is not estimable: {periods} matched forecast origins; "
            f"at least {minimum_periods} are required"
        )

    diagnostics: list[dict[str, object]] = []
    strata = [([], "overall")]
    for column in ["direct_concordance_quality", "direct_census_recency_years"]:
        strata.append(([column], column.removeprefix("direct_")))
    for (ghsl_source, boundary), source_rows in matched.groupby(
        ["ghsl_source", "ghsl_boundary_mode"], dropna=False
    ):
        for group_columns, stratum_name in strata:
            groups = [((), source_rows)] if not group_columns else source_rows.groupby(group_columns, dropna=False)
            for key, group in groups:
                key = key if isinstance(key, tuple) else (key,)
                for label, recent, future in [
                    ("direct_count", "direct_recent_growth", "direct_future_growth"),
                    (str(ghsl_source), "recent_growth", "future_growth"),
                ]:
                    values = group[[recent, future]].rename(
                        columns={recent: "recent_growth", future: "future_growth"}
                    )
                    row: dict[str, object] = {
                        "ghsl_source": ghsl_source,
                        "boundary_mode": boundary,
                        "stratum": stratum_name,
                        "stratum_value": "overall" if not key else str(key[0]),
                        "measured_source": label,
                    }
                    row.update(_metrics(values))
                    diagnostics.append(row)
    metrics = pd.DataFrame(diagnostics)
    index = ["ghsl_source", "boundary_mode", "stratum", "stratum_value"]
    direct_metrics = metrics.loc[metrics["measured_source"].eq("direct_count")].set_index(index)
    ghsl_metrics = metrics.loc[~metrics["measured_source"].eq("direct_count")].set_index(index)
    contrast_columns = [
        "persistence_beta", "mae_improvement_vs_zero", "rmse_improvement_vs_zero",
        "sign_reversal_rate", "mean_growth_curvature", "mean_absolute_growth_curvature",
    ]
    contrasts = ghsl_metrics[contrast_columns].subtract(direct_metrics[contrast_columns])
    contrasts = contrasts.add_suffix("_ghsl_minus_direct").reset_index()
    contrasts["construction_smoothing_interpretation"] = np.where(
        (contrasts["persistence_beta_ghsl_minus_direct"] > 0)
        & (contrasts["sign_reversal_rate_ghsl_minus_direct"] < 0),
        "consistent_with_stronger_ghsl_persistence",
        "no_materially_stronger_ghsl_pattern_established",
    )
    return coverage, metrics, contrasts

"""Tests of whether recent city growth adds information beyond country context."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.forecast import baseline_predictions, rolling_origin_splits, score_forecast
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def evaluate_country_adjusted_recent_growth_information(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Compare country context alone with country context plus recent city growth.

    The comparison is nested and matched by construction. For each rolling origin,
    the recent-growth coefficient is estimated only from training rows whose outcomes
    end by the forecast origin. Country means are removed before estimating the
    coefficient. Both models are then scored on the identical test rows.

    Negative MAE/RMSE deltas mean recent growth improves the country-context forecast.
    """
    require_columns(
        panel,
        {
            "city_id",
            "country_code",
            "period_start",
            "period_end",
            "recent_growth",
            outcome_column,
        },
        source_name="H1 recent-growth information panel",
    )
    reject_duplicate_keys(
        panel,
        ["city_id", "period_start", "period_end"],
        source_name="H1 recent-growth information panel",
    )
    if not origins or len(set(origins)) != len(origins):
        raise SourceSchemaError("H1 forecast origins must be unique and non-empty")

    rows: list[dict[str, object]] = []
    for origin, train_index, test_index in rolling_origin_splits(panel, sorted(origins)):
        candidate_train = panel.loc[train_index].copy()
        candidate_test = panel.loc[test_index].copy()
        needed = ["city_id", "country_code", "recent_growth", outcome_column]
        train = candidate_train.dropna(subset=needed).copy()
        test = candidate_test.dropna(subset=needed).copy()
        train = train.loc[
            np.isfinite(train[["recent_growth", outcome_column]]).all(axis=1)
        ]
        test = test.loc[
            np.isfinite(test[["recent_growth", outcome_column]]).all(axis=1)
        ]
        if train.empty or test.empty:
            continue

        baseline = baseline_predictions(train, test, outcome_column=outcome_column)
        country_only = baseline["country_mean_leave_city_out"]
        matched = pd.DataFrame(
            {
                "actual": test[outcome_column],
                "recent_growth": test["recent_growth"],
                "country_only": country_only,
            },
            index=test.index,
        ).dropna()
        if matched.empty:
            continue

        fit = train[["country_code", outcome_column, "recent_growth"]].copy()
        group_means = fit.groupby("country_code")[[outcome_column, "recent_growth"]].transform(
            "mean"
        )
        demeaned = fit[[outcome_column, "recent_growth"]] - group_means
        x = demeaned[["recent_growth"]].to_numpy()
        y = demeaned[outcome_column].to_numpy()
        beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        beta_recent = float(beta[0])

        country_recent_means = fit.groupby("country_code")["recent_growth"].mean()
        global_recent_mean = float(fit["recent_growth"].mean())
        matched["country_recent_mean"] = (
            test.loc[matched.index, "country_code"]
            .map(country_recent_means)
            .fillna(global_recent_mean)
        )
        matched["country_plus_recent"] = matched["country_only"] + beta_recent * (
            matched["recent_growth"] - matched["country_recent_mean"]
        )

        country_metrics = score_forecast(matched["actual"], matched["country_only"])
        recent_metrics = score_forecast(matched["actual"], matched["country_plus_recent"])
        if country_metrics.n != recent_metrics.n:
            raise SourceSchemaError("H1 nested models were not scored on identical rows")

        mae_delta = recent_metrics.mae - country_metrics.mae
        rmse_delta = recent_metrics.rmse - country_metrics.rmse
        rows.append(
            {
                "origin": origin,
                "n": recent_metrics.n,
                "candidate_train_n": len(candidate_train),
                "matched_train_n": len(train),
                "candidate_test_n": len(candidate_test),
                "matched_test_n": recent_metrics.n,
                "recent_growth_beta_within_country": beta_recent,
                "country_only_mae": country_metrics.mae,
                "country_plus_recent_mae": recent_metrics.mae,
                "mae_delta_recent_minus_country": mae_delta,
                "mae_improvement_fraction": (
                    -mae_delta / country_metrics.mae if country_metrics.mae > 0 else np.nan
                ),
                "country_only_rmse": country_metrics.rmse,
                "country_plus_recent_rmse": recent_metrics.rmse,
                "rmse_delta_recent_minus_country": rmse_delta,
                "rmse_improvement_fraction": (
                    -rmse_delta / country_metrics.rmse if country_metrics.rmse > 0 else np.nan
                ),
                "recent_growth_improves_mae": bool(mae_delta < 0),
                "recent_growth_improves_rmse": bool(rmse_delta < 0),
                "recent_growth_improves_both": bool(mae_delta < 0 and rmse_delta < 0),
                "comparison": "country_loo_only_vs_country_loo_plus_recent_growth",
                "training_precedes_origin": True,
                "test_rows_identical_across_nested_models": True,
            }
        )

    if not rows:
        raise SourceSchemaError("No H1 incremental recent-growth evaluations were produced")
    return pd.DataFrame(rows).sort_values("origin").reset_index(drop=True)

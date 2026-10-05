"""Origin-available contemporaneous country peer-growth diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.forecast import (
    baseline_predictions,
    rolling_origin_splits,
    score_forecast,
)
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def attach_contemporaneous_country_recent_growth(
    intervals: pd.DataFrame,
    *,
    growth_column: str = "recent_growth",
) -> pd.DataFrame:
    """Attach leave-city-out same-country recent growth at each forecast origin.

    The predictor uses only other cities' recent growth measured at the same origin.
    Singleton-country rows fall back to the contemporaneous global leave-city-out mean.
    """
    required = {"city_id", "country_code", "period_start", growth_column}
    require_columns(intervals, required, source_name="forecast intervals")
    reject_duplicate_keys(
        intervals,
        ["city_id", "period_start"],
        source_name="contemporaneous country baseline intervals",
    )
    working = intervals.copy()
    growth = pd.to_numeric(working[growth_column], errors="coerce")
    if growth.isna().any() or not np.isfinite(growth).all():
        raise SourceSchemaError("Contemporaneous country baseline requires finite recent growth")
    working["_recent_growth"] = growth

    origin_totals = working.groupby("period_start")["_recent_growth"].agg(["sum", "count"])
    country_totals = working.groupby(["period_start", "country_code"])["_recent_growth"].agg(
        ["sum", "count"]
    )
    origin_sum = working["period_start"].map(origin_totals["sum"]).to_numpy()
    origin_count = working["period_start"].map(origin_totals["count"]).to_numpy()
    keys = pd.MultiIndex.from_frame(working[["period_start", "country_code"]])
    country_sum = country_totals["sum"].reindex(keys).to_numpy()
    country_count = country_totals["count"].reindex(keys).to_numpy()
    focal = working["_recent_growth"].to_numpy()

    global_loo_count = origin_count - 1
    if (global_loo_count <= 0).any():
        raise SourceSchemaError("Contemporaneous baseline needs at least two cities per origin")
    global_loo = (origin_sum - focal) / global_loo_count
    country_loo_count = country_count - 1
    prediction = np.divide(
        country_sum - focal,
        country_loo_count,
        out=global_loo.copy(),
        where=country_loo_count > 0,
    )
    working["country_contemporaneous_recent_growth_leave_city_out"] = prediction
    working["contemporaneous_country_peer_count"] = country_loo_count
    working["contemporaneous_country_fallback_global_loo"] = country_loo_count <= 0
    working["contemporaneous_country_uses_future_outcome"] = False
    working["contemporaneous_country_information_time"] = "forecast_origin"
    return working.drop(columns="_recent_growth")


def evaluate_contemporaneous_country_baseline(
    intervals: pd.DataFrame,
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Compare persistence with the contemporaneous country peer-growth baseline by origin."""
    working = attach_contemporaneous_country_recent_growth(intervals)
    require_columns(
        working,
        {outcome_column, "recent_growth", "period_start"},
        source_name="contemporaneous baseline evaluation",
    )
    rows: list[dict[str, object]] = []
    peer = "country_contemporaneous_recent_growth_leave_city_out"
    for origin, group in working.groupby("period_start", sort=True):
        actual = group[outcome_column]
        persistence = score_forecast(actual, group["recent_growth"])
        contemporary = score_forecast(actual, group[peer])
        if persistence.n != contemporary.n:
            raise SourceSchemaError("Contemporaneous comparator was not scored on identical rows")
        rows.append(
            {
                "origin": int(origin),
                "n": persistence.n,
                "persistence_mae": persistence.mae,
                "contemporaneous_country_mae": contemporary.mae,
                "mae_delta_persistence_minus_contemporaneous": (persistence.mae - contemporary.mae),
                "persistence_rmse": persistence.rmse,
                "contemporaneous_country_rmse": contemporary.rmse,
                "rmse_delta_persistence_minus_contemporaneous": (
                    persistence.rmse - contemporary.rmse
                ),
                "persistence_beats_contemporaneous_mae": persistence.mae < contemporary.mae,
                "persistence_beats_contemporaneous_rmse": persistence.rmse < contemporary.rmse,
                "fallback_rows": int(group["contemporaneous_country_fallback_global_loo"].sum()),
                "comparator_information_time": "forecast_origin",
                "comparator_leave_city_out": True,
            }
        )
    if not rows:
        raise SourceSchemaError("No contemporaneous country baseline evaluations were produced")
    return pd.DataFrame(rows)


def contemporaneous_country_baseline_errors(
    intervals: pd.DataFrame,
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Return matched row errors for persistence and contemporaneous country peer growth."""
    working = attach_contemporaneous_country_recent_growth(intervals)
    peer = "country_contemporaneous_recent_growth_leave_city_out"
    required = {"city_id", "country_code", "period_start", outcome_column, "recent_growth", peer}
    require_columns(working, required, source_name="contemporaneous baseline errors")
    id_columns = [
        c for c in ["city_id", "country_code", "city_name", "period_start"] if c in working
    ]
    rows = []
    for model, column in [
        ("persistence", "recent_growth"),
        ("country_contemporaneous_recent_growth_leave_city_out", peer),
    ]:
        frame = working[id_columns].copy()
        frame["origin"] = working["period_start"].to_numpy()
        frame["model"] = model
        frame["actual"] = working[outcome_column].to_numpy()
        frame["predicted"] = working[column].to_numpy()
        frame["error"] = frame["predicted"] - frame["actual"]
        frame["absolute_error"] = frame["error"].abs()
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def _country_balanced_losses(
    actual: pd.Series,
    predicted: pd.Series,
    country: pd.Series,
) -> tuple[float, float]:
    errors = pd.DataFrame(
        {
            "country_code": country.to_numpy(),
            "error": predicted.to_numpy() - actual.to_numpy(),
        }
    )
    by_country = (
        errors.assign(
            absolute_error=lambda frame: frame["error"].abs(),
            squared_error=lambda frame: frame["error"].pow(2),
        )
        .groupby("country_code")[["absolute_error", "squared_error"]]
        .mean()
    )
    return float(by_country["absolute_error"].mean()), float(
        np.sqrt(by_country["squared_error"].mean())
    )


def _weighted_slope(x: pd.Series, y: pd.Series, weights: pd.Series) -> float:
    denominator = float(np.sum(weights * x.pow(2)))
    if denominator <= 0:
        raise SourceSchemaError("H1 contemporaneous deviation has no estimable variation")
    return float(np.sum(weights * x * y) / denominator)


def evaluate_contemporaneous_country_h1_hierarchy(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Evaluate the H1 model hierarchy per origin without future information.

    The primary nested comparison adds the focal city's deviation from its
    same-origin, leave-city-out country peer signal. Coefficients are estimated
    only on prior-origin rows. Row-weighted and equal-country fits and losses are
    reported separately. Historical country-context models are retained only as
    continuity sensitivities.
    """
    required = {
        "city_id",
        "country_code",
        "period_start",
        "period_end",
        "recent_growth",
        outcome_column,
    }
    require_columns(panel, required, source_name="H1 contemporaneous hierarchy panel")
    reject_duplicate_keys(
        panel,
        ["city_id", "period_start", "period_end"],
        source_name="H1 contemporaneous hierarchy panel",
    )
    if not origins or len(origins) != len(set(origins)):
        raise SourceSchemaError("H1 contemporaneous origins must be unique and non-empty")

    working = attach_contemporaneous_country_recent_growth(panel)
    peer = "country_contemporaneous_recent_growth_leave_city_out"
    rows: list[dict[str, object]] = []
    for origin, train_index, test_index in rolling_origin_splits(working, sorted(origins)):
        needed = ["country_code", "recent_growth", peer, outcome_column]
        train = working.loc[train_index].dropna(subset=needed).copy()
        test = working.loc[test_index].dropna(subset=needed).copy()
        train = train.loc[np.isfinite(train[["recent_growth", peer, outcome_column]]).all(axis=1)]
        test = test.loc[np.isfinite(test[["recent_growth", peer, outcome_column]]).all(axis=1)]
        if train.empty or test.empty:
            continue

        historical = baseline_predictions(train, test, outcome_column=outcome_column)
        matched = pd.DataFrame(
            {
                "actual": test[outcome_column],
                "country_code": test["country_code"],
                "recent_growth": test["recent_growth"],
                "contemporaneous_country": test[peer],
                "historical_country": historical["country_mean_leave_city_out"],
            },
            index=test.index,
        ).dropna()
        if matched.empty:
            continue

        train_deviation = train["recent_growth"] - train[peer]
        train_residual = train[outcome_column] - train[peer]
        country_sizes = train.groupby("country_code")["city_id"].transform("size")
        fit_weights = {
            "row_weighted": pd.Series(1.0, index=train.index),
            "country_balanced": 1.0 / country_sizes,
        }

        historical_means = train.groupby("country_code")[
            [outcome_column, "recent_growth"]
        ].transform("mean")
        historical_x = train["recent_growth"] - historical_means["recent_growth"]
        historical_y = train[outcome_column] - historical_means[outcome_column]

        for weighting, weights in fit_weights.items():
            beta = _weighted_slope(train_deviation, train_residual, weights)
            historical_beta = _weighted_slope(historical_x, historical_y, weights)
            country_recent = train.groupby("country_code")["recent_growth"].mean()
            global_recent = float(train["recent_growth"].mean())
            test_country_recent = matched["country_code"].map(country_recent).fillna(global_recent)
            predictions = {
                "contemporaneous_country_only": matched["contemporaneous_country"],
                "contemporaneous_country_plus_city_deviation": matched["contemporaneous_country"]
                + beta * (matched["recent_growth"] - matched["contemporaneous_country"]),
                "historical_country_loo_only": matched["historical_country"],
                "historical_country_loo_plus_recent_growth": matched["historical_country"]
                + historical_beta * (matched["recent_growth"] - test_country_recent),
            }
            metrics: dict[str, tuple[float, float]] = {}
            for model, prediction in predictions.items():
                if weighting == "row_weighted":
                    score = score_forecast(matched["actual"], prediction)
                    metrics[model] = (score.mae, score.rmse)
                else:
                    metrics[model] = _country_balanced_losses(
                        matched["actual"], prediction, matched["country_code"]
                    )
            winner_mae = min(metrics, key=lambda model: metrics[model][0])
            winner_rmse = min(metrics, key=lambda model: metrics[model][1])
            baseline_mae, baseline_rmse = metrics["contemporaneous_country_only"]
            for model, (mae, rmse) in metrics.items():
                model_beta = (
                    beta
                    if model == "contemporaneous_country_plus_city_deviation"
                    else historical_beta
                    if model == "historical_country_loo_plus_recent_growth"
                    else np.nan
                )
                rows.append(
                    {
                        "origin": int(origin),
                        "weighting": weighting,
                        "model": model,
                        "n": len(matched),
                        "country_count": int(matched["country_code"].nunique()),
                        "candidate_train_n": len(working.loc[train_index]),
                        "matched_train_n": len(train),
                        "beta": model_beta,
                        "mae": mae,
                        "rmse": rmse,
                        "mae_delta_vs_contemporaneous_country": mae - baseline_mae,
                        "rmse_delta_vs_contemporaneous_country": rmse - baseline_rmse,
                        "mae_winner": model == winner_mae,
                        "rmse_winner": model == winner_rmse,
                        "test_rows_identical_across_models": True,
                        "training_precedes_origin": True,
                        "contemporaneous_country_leave_city_out": True,
                        "contemporaneous_country_uses_future_outcome": False,
                    }
                )
    if not rows:
        raise SourceSchemaError("No H1 contemporaneous hierarchy evaluations were produced")
    return pd.DataFrame(rows).sort_values(["origin", "weighting", "model"]).reset_index(drop=True)

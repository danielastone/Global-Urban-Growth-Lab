"""Origin-available contemporaneous country peer-growth diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.forecast import score_forecast
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
                "mae_delta_persistence_minus_contemporaneous": (
                    persistence.mae - contemporary.mae
                ),
                "persistence_rmse": persistence.rmse,
                "contemporaneous_country_rmse": contemporary.rmse,
                "rmse_delta_persistence_minus_contemporaneous": (
                    persistence.rmse - contemporary.rmse
                ),
                "persistence_beats_contemporaneous_mae": persistence.mae < contemporary.mae,
                "persistence_beats_contemporaneous_rmse": persistence.rmse < contemporary.rmse,
                "fallback_rows": int(
                    group["contemporaneous_country_fallback_global_loo"].sum()
                ),
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
    id_columns = [c for c in ["city_id", "country_code", "city_name", "period_start"] if c in working]
    rows = []
    for model, column in [("persistence", "recent_growth"), ("country_contemporaneous_recent_growth_leave_city_out", peer)]:
        frame = working[id_columns].copy()
        frame["origin"] = working["period_start"].to_numpy()
        frame["model"] = model
        frame["actual"] = working[outcome_column].to_numpy()
        frame["predicted"] = working[column].to_numpy()
        frame["error"] = frame["predicted"] - frame["actual"]
        frame["absolute_error"] = frame["error"].abs()
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)

"""Leakage-resistant forecast evaluation primitives."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


@dataclass(frozen=True)
class ForecastMetrics:
    n: int
    mae: float
    rmse: float
    median_absolute_error: float
    bias: float
    directional_accuracy: float


def rolling_origin_splits(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    start_column: str = "period_start",
    end_column: str = "period_end",
) -> Iterator[tuple[int, pd.Index, pd.Index]]:
    """Yield train/test indices where training outcomes predate each origin."""
    for origin in origins:
        train = panel.index[panel[end_column] <= origin]
        test = panel.index[panel[start_column] == origin]
        if len(train) and len(test):
            yield origin, train, test


def build_forecast_intervals(
    city_year_panel: pd.DataFrame,
    origins: list[int],
    *,
    lookback_years: int = 5,
    horizon_years: int = 5,
    allowed_outcome_types: set[str] | None = None,
) -> pd.DataFrame:
    """Create lagged predictors and later outcomes from exact source years.

    The default permits estimate outcomes only. Callers must explicitly opt into
    evaluating publisher projections as outcomes.
    """
    required = {
        "city_id", "year", "population", "observation_type", "ISO3_Code",
        "City_Name", "built_up_share_of_land", "population_density_per_km2",
    }
    require_columns(city_year_panel, required, source_name="WUP city-year forecast source")
    reject_duplicate_keys(city_year_panel, ["city_id", "year"], source_name="WUP forecast")
    if lookback_years <= 0 or horizon_years <= 0:
        raise SourceSchemaError("Forecast lookback and horizon must be positive")
    if not origins or any(not isinstance(year, int) for year in origins):
        raise SourceSchemaError("Forecast origins must be a non-empty list of integer years")
    allowed = {"estimate"} if allowed_outcome_types is None else allowed_outcome_types
    if not allowed:
        raise SourceSchemaError("At least one outcome observation type must be allowed")

    source = city_year_panel.set_index(["city_id", "year"])
    frames: list[pd.DataFrame] = []
    for origin in sorted(set(origins)):
        lag_year = origin - lookback_years
        future_year = origin + horizon_years
        available_cities = source.index.get_level_values("city_id").unique()
        keys = pd.MultiIndex.from_product(
            [available_cities, [lag_year, origin, future_year]], names=["city_id", "year"]
        )
        complete = source.reindex(keys).reset_index()
        wide = complete.pivot(index="city_id", columns="year")
        has_population = wide["population"].notna().all(axis=1)
        if not has_population.any():
            continue
        wide = wide.loc[has_population]
        outcome_type = wide[("observation_type", future_year)]
        wide = wide.loc[outcome_type.isin(allowed)]
        if wide.empty:
            continue
        result = pd.DataFrame(index=wide.index)
        result["country_code"] = wide[("ISO3_Code", origin)]
        result["city_name"] = wide[("City_Name", origin)]
        result["period_start"] = origin
        result["period_end"] = future_year
        result["population_lag"] = wide[("population", lag_year)]
        result["population_start"] = wide[("population", origin)]
        result["population_end"] = wide[("population", future_year)]
        result["recent_growth"] = (
            np.log(result["population_start"]) - np.log(result["population_lag"])
        ) / lookback_years
        result["future_growth"] = (
            np.log(result["population_end"]) - np.log(result["population_start"])
        ) / horizon_years
        result["built_up_share_at_origin"] = wide[("built_up_share_of_land", origin)]
        result["population_density_at_origin"] = wide[
            ("population_density_per_km2", origin)
        ]
        result["lag_observation_type"] = wide[("observation_type", lag_year)]
        result["origin_observation_type"] = wide[("observation_type", origin)]
        result["outcome_observation_type"] = wide[("observation_type", future_year)]
        result["coverage_selection"] = "complete_lag_origin_future"
        frames.append(result.reset_index())
    if not frames:
        raise SourceSchemaError("No complete forecast intervals satisfy the declared rules")
    panel = pd.concat(frames, ignore_index=True)
    reject_duplicate_keys(
        panel, ["city_id", "period_start", "period_end"], source_name="forecast intervals"
    )
    return panel.sort_values(["period_start", "city_id"]).reset_index(drop=True)


def score_forecast(actual: pd.Series, predicted: pd.Series) -> ForecastMetrics:
    """Score matched observations after dropping non-finite pairs."""
    pairs = pd.concat({"actual": actual, "predicted": predicted}, axis=1).dropna()
    finite = np.isfinite(pairs).all(axis=1)
    pairs = pairs.loc[finite]
    if pairs.empty:
        raise ValueError("No finite matched observations to score")
    error = pairs["predicted"] - pairs["actual"]
    return ForecastMetrics(
        n=len(pairs),
        mae=float(error.abs().mean()),
        rmse=float(np.sqrt((error**2).mean())),
        median_absolute_error=float(error.abs().median()),
        bias=float(error.mean()),
        directional_accuracy=float(
            (np.sign(pairs["predicted"]) == np.sign(pairs["actual"])).mean()
        ),
    )


def baseline_predictions(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    outcome_column: str = "future_growth",
    persistence_column: str = "recent_growth",
) -> pd.DataFrame:
    """Predict simple baselines using training outcomes and test-origin information only."""
    required = {"country_code", outcome_column}
    require_columns(train, required, source_name="forecast training set")
    require_columns(
        test, {"country_code", persistence_column}, source_name="forecast test set"
    )
    valid_train = train.loc[np.isfinite(train[outcome_column])].copy()
    if valid_train.empty:
        raise SourceSchemaError("No finite training outcomes for forecast baselines")
    global_mean = float(valid_train[outcome_column].mean())
    country_means = valid_train.groupby("country_code")[outcome_column].mean()
    predictions = pd.DataFrame(index=test.index)
    predictions["zero_growth"] = 0.0
    predictions["global_mean"] = global_mean
    predictions["country_mean"] = test["country_code"].map(country_means).fillna(global_mean)
    predictions["persistence"] = pd.to_numeric(test[persistence_column], errors="coerce")
    return predictions


def evaluate_rolling_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Score matched baseline predictions at chronological rolling origins."""
    require_columns(
        panel,
        {"period_start", "period_end", "country_code", outcome_column, "recent_growth"},
        source_name="forecast interval panel",
    )
    rows: list[dict[str, float | int | str]] = []
    for origin, train_index, test_index in rolling_origin_splits(panel, origins):
        train = panel.loc[train_index]
        test = panel.loc[test_index]
        predictions = baseline_predictions(train, test, outcome_column=outcome_column)
        matched = pd.concat(
            {"actual": test[outcome_column], **{c: predictions[c] for c in predictions}}, axis=1
        ).dropna()
        finite = np.isfinite(matched).all(axis=1)
        matched = matched.loc[finite]
        if matched.empty:
            continue
        for model in predictions.columns:
            metrics = score_forecast(matched["actual"], matched[model])
            rows.append(
                {
                    "origin": origin,
                    "model": model,
                    "n": metrics.n,
                    "mae": metrics.mae,
                    "rmse": metrics.rmse,
                    "median_absolute_error": metrics.median_absolute_error,
                    "bias": metrics.bias,
                    "directional_accuracy": metrics.directional_accuracy,
                }
            )
    if not rows:
        raise SourceSchemaError("No rolling-origin baseline evaluations were produced")
    result = pd.DataFrame(rows)
    counts = result.pivot(index="origin", columns="model", values="n")
    if counts.nunique(axis=1).gt(1).any():
        raise SourceSchemaError("Baseline models were not scored on identical observations")
    return result.sort_values(["origin", "model"]).reset_index(drop=True)

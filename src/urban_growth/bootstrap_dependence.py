"""Dependence-aware bootstrap inference for pooled rolling-origin comparisons."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns


def _circular_block_weights(
    *,
    cluster_count: int,
    block_length: int,
    repetitions: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw circular moving blocks and return cluster multiplicities by repetition."""
    if not 1 <= block_length <= cluster_count:
        raise SourceSchemaError("Time block length must be between one and the origin count")
    if block_length == 1:
        return rng.multinomial(
            cluster_count,
            np.full(cluster_count, 1 / cluster_count),
            size=repetitions,
        )
    blocks_per_draw = math.ceil(cluster_count / block_length)
    starts = rng.integers(0, cluster_count, size=(repetitions, blocks_per_draw))
    offsets = np.arange(block_length)
    sampled = (starts[..., None] + offsets) % cluster_count
    sampled = sampled.reshape(repetitions, -1)[:, :cluster_count]
    weights = np.zeros((repetitions, cluster_count), dtype=int)
    for repetition in range(repetitions):
        weights[repetition] = np.bincount(sampled[repetition], minlength=cluster_count)
    return weights


def block_two_way_cluster_bootstrap_paired_difference(
    errors: pd.DataFrame,
    *,
    forecast_horizon_years: int,
    model_a: str = "persistence",
    model_b: str = "country_mean_leave_city_out",
    group_columns: list[str] | None = None,
    country_column: str = "country_code",
    time_column: str = "origin",
    repetitions: int = 2_000,
    seed: int = 20260827,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Bootstrap paired MAE differences with country clusters and origin blocks.

    Country draws preserve each sampled country's complete city-by-origin contribution.
    Time dependence is handled with circular moving blocks over sorted forecast origins.
    The block length is derived conservatively from the declared forecast horizon and
    the minimum spacing between observed origins: ``ceil(horizon / min_origin_spacing)``.
    Thus overlapping forecast windows cannot be treated as exchangeable one-origin
    clusters merely because their annualized outcomes share a common scale.
    """
    groups = group_columns or []
    required = {
        "city_id",
        "model",
        "absolute_error",
        country_column,
        time_column,
        *groups,
    }
    require_columns(errors, required, source_name="row-level forecast errors")
    if forecast_horizon_years <= 0:
        raise SourceSchemaError("Forecast horizon must be positive")
    if repetitions < 100:
        raise SourceSchemaError("Block two-way bootstrap requires at least 100 repetitions")
    if not 0 < confidence < 1:
        raise SourceSchemaError("Bootstrap confidence must be between zero and one")

    subset = errors.loc[errors["model"].isin([model_a, model_b])]
    index = list(dict.fromkeys(["city_id", country_column, time_column, *groups]))
    paired = subset.pivot(index=index, columns="model", values="absolute_error").dropna()
    if model_a not in paired or model_b not in paired:
        raise SourceSchemaError("Requested models do not have matched row-level errors")
    paired["difference"] = paired[model_a] - paired[model_b]
    paired = paired.reset_index()

    if groups:
        grouper: str | list[str] = groups[0] if len(groups) == 1 else groups
        grouped = paired.groupby(grouper, observed=True, sort=True)
    else:
        grouped = [((), paired)]

    alpha = (1 - confidence) / 2
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int | str | bool]] = []
    for group_key, group in grouped:
        countries = sorted(group[country_column].unique())
        times = sorted(group[time_column].unique())
        if len(countries) < 2 or len(times) < 2:
            continue
        time_array = np.asarray(times, dtype=float)
        spacing = np.diff(time_array)
        if not np.isfinite(spacing).all() or (spacing <= 0).any():
            raise SourceSchemaError("Forecast origins must be strictly increasing numeric values")
        minimum_spacing = float(spacing.min())
        block_length = min(
            len(times),
            max(1, math.ceil(forecast_horizon_years / minimum_spacing)),
        )
        origins_overlap = forecast_horizon_years > minimum_spacing

        cells = group.groupby([country_column, time_column])["difference"].agg(["sum", "count"])
        sums = cells["sum"].unstack(fill_value=0).reindex(
            index=countries, columns=times, fill_value=0
        ).to_numpy()
        counts = cells["count"].unstack(fill_value=0).reindex(
            index=countries, columns=times, fill_value=0
        ).to_numpy()
        country_draws = rng.multinomial(
            len(countries),
            np.full(len(countries), 1 / len(countries)),
            size=repetitions,
        )
        time_draws = _circular_block_weights(
            cluster_count=len(times),
            block_length=block_length,
            repetitions=repetitions,
            rng=rng,
        )
        sampled_sums = np.einsum("rc,ct,rt->r", country_draws, sums, time_draws)
        sampled_counts = np.einsum("rc,ct,rt->r", country_draws, counts, time_draws)
        if (sampled_counts <= 0).any():
            raise SourceSchemaError("Bootstrap draw produced an empty paired sample")
        estimates = sampled_sums / sampled_counts

        keys = (group_key,) if len(groups) == 1 else group_key
        row: dict[str, float | int | str | bool] = dict(zip(groups, keys, strict=True))
        row.update(
            {
                "model_a": model_a,
                "model_b": model_b,
                "n": len(group),
                "countries": len(countries),
                "time_clusters": len(times),
                "forecast_horizon_years": forecast_horizon_years,
                "minimum_origin_spacing_years": minimum_spacing,
                "origins_overlap": origins_overlap,
                "time_block_length": block_length,
                "time_resampling_scheme": (
                    "circular_moving_origin_blocks" if block_length > 1 else "exchangeable_origin_clusters"
                ),
                "adjacent_origin_blocks_preserved": block_length > 1,
                "country_cluster_preserves_nested_city_trajectories": True,
                "observed_mean_difference": float(group["difference"].mean()),
                "ci_lower": float(np.quantile(estimates, alpha)),
                "ci_upper": float(np.quantile(estimates, 1 - alpha)),
                "probability_model_a_better": float((estimates < 0).mean()),
                "repetitions": repetitions,
                "seed": seed,
            }
        )
        rows.append(row)
    if not rows:
        raise SourceSchemaError("No groups had enough country and time clusters")
    return pd.DataFrame(rows)

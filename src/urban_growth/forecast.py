"""Leakage-resistant forecast evaluation primitives."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd


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

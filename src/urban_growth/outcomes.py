"""Prespecified descriptive outcomes for city growth and decline."""

from __future__ import annotations

import numpy as np
import pandas as pd

DECLINE_THRESHOLDS = (-0.0025, -0.005, -0.01)
SIZE_BIN_EDGES = [0, 50_000, 150_000, 250_000, 500_000, 1_000_000, 2_000_000, np.inf]
SIZE_BIN_LABELS = ["<50k", "50–150k", "150–250k", "250–500k", "500k–1m", "1–2m", "2m+"]


def add_decline_indicators(
    panel: pd.DataFrame, *, growth_column: str = "annual_growth"
) -> pd.DataFrame:
    """Add the three prespecified annual decline-state indicators."""
    if growth_column not in panel:
        raise KeyError(growth_column)
    if panel[growth_column].isna().any() or not np.isfinite(panel[growth_column]).all():
        raise ValueError("Growth values must be finite and non-null")
    result = panel.copy()
    for threshold in DECLINE_THRESHOLDS:
        basis_points = int(abs(threshold) * 10_000)
        result[f"decline_{basis_points}bp"] = result[growth_column] <= threshold
    return result


def add_size_bins(
    panel: pd.DataFrame, *, population_column: str = "population_start"
) -> pd.DataFrame:
    """Add presentation bins while retaining continuous population for models."""
    if population_column not in panel:
        raise KeyError(population_column)
    if panel[population_column].isna().any() or (panel[population_column] <= 0).any():
        raise ValueError("Population values must be positive and non-null")
    result = panel.copy()
    result["size_bin"] = pd.cut(
        result[population_column], bins=SIZE_BIN_EDGES, labels=SIZE_BIN_LABELS,
        right=False, include_lowest=True,
    )
    return result

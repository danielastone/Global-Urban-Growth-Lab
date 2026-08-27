"""Validation and transformations for city-period population panels."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "city_id",
    "country_code",
    "period_start",
    "period_end",
    "population_start",
    "population_end",
}


class PanelValidationError(ValueError):
    """Raised when a panel violates the documented data contract."""


def validate_panel(panel: pd.DataFrame) -> None:
    """Validate structural invariants before any model is fit."""
    missing = sorted(REQUIRED_COLUMNS.difference(panel.columns))
    if missing:
        raise PanelValidationError(f"Missing required columns: {', '.join(missing)}")

    keys = ["city_id", "period_start", "period_end"]
    nonnull = [*keys, "country_code", "population_start", "population_end"]
    if panel[nonnull].isna().any().any():
        raise PanelValidationError("Keys, country codes, and population values cannot be null")
    numeric = ["period_start", "period_end", "population_start", "population_end"]
    if any(not pd.api.types.is_numeric_dtype(panel[column]) for column in numeric):
        raise PanelValidationError("Years and population values must be numeric")
    if not np.isfinite(panel[numeric].to_numpy(dtype=float)).all():
        raise PanelValidationError("Years and population values must be finite")
    if not (panel["period_start"] % 1 == 0).all() or not (panel["period_end"] % 1 == 0).all():
        raise PanelValidationError("Period years must be whole numbers")
    if panel.duplicated(keys).any():
        raise PanelValidationError("City-period keys must be unique")
    if (panel["period_end"] <= panel["period_start"]).any():
        raise PanelValidationError("period_end must be greater than period_start")
    if (panel[["population_start", "population_end"]] <= 0).any().any():
        raise PanelValidationError("Population values must be positive")


def add_annualized_log_growth(
    panel: pd.DataFrame, output_column: str = "annual_growth"
) -> pd.DataFrame:
    """Return a validated copy with annualized log population growth."""
    validate_panel(panel)
    result = panel.copy()
    years = result["period_end"] - result["period_start"]
    result[output_column] = (
        np.log(result["population_end"]) - np.log(result["population_start"])
    ) / years
    return result

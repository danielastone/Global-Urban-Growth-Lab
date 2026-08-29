"""Leakage-resistant national demographic and settlement-composition controls."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

DEGURBA_CATEGORIES = ("city", "town_and_semi_dense", "rural")


def attach_national_context(
    intervals: pd.DataFrame,
    national_panel: pd.DataFrame,
    *,
    lookback_years: int = 5,
) -> pd.DataFrame:
    """Attach origin-available, leave-one-city-out national context.

    The national panel must contain one row per country, year, and harmonized
    DEGURBA category. The focal city is removed from both the national total
    and Cities-category population at the lookback and forecast-origin years.
    Values after the forecast origin are never selected.

    A city-state or other row with no positive residual national population is
    retained with national_context_loo_available set false and missing derived
    controls. This avoids changing the forecast sample silently.
    """
    require_columns(
        intervals,
        {
            "city_id",
            "country_code",
            "period_start",
            "population_lag",
            "population_start",
        },
        source_name="forecast intervals",
    )
    require_columns(
        national_panel,
        {"country_code", "year", "category", "population"},
        source_name="national DEGURBA panel",
    )
    if lookback_years <= 0:
        raise SourceSchemaError("National-context lookback must be positive")

    reject_duplicate_keys(
        national_panel,
        ["country_code", "year", "category"],
        source_name="national DEGURBA panel",
    )
    unknown = sorted(set(national_panel["category"].dropna()) - set(DEGURBA_CATEGORIES))
    if unknown:
        raise SourceSchemaError(
            f"National DEGURBA panel has unknown categories: {', '.join(map(str, unknown))}"
        )
    if national_panel[["country_code", "year", "category", "population"]].isna().any().any():
        raise SourceSchemaError("National DEGURBA keys and populations cannot be null")
    population = pd.to_numeric(national_panel["population"], errors="coerce")
    if population.isna().any() or not np.isfinite(population).all():
        raise SourceSchemaError("National DEGURBA population must be finite and numeric")
    if (population < 0).any():
        raise SourceSchemaError("National DEGURBA population cannot be negative")

    normalized = national_panel.assign(population=population)
    wide = normalized.pivot(
        index=["country_code", "year"], columns="category", values="population"
    )
    missing_categories = [category for category in DEGURBA_CATEGORIES if category not in wide]
    if missing_categories or wide[list(DEGURBA_CATEGORIES)].isna().any().any():
        raise SourceSchemaError(
            "National DEGURBA panel requires city, town_and_semi_dense, and rural "
            "for every country-year"
        )
    wide = wide.loc[:, list(DEGURBA_CATEGORIES)]
    wide["total"] = wide.sum(axis=1)
    if (wide["total"] <= 0).any():
        raise SourceSchemaError("National DEGURBA total population must be positive")

    result = intervals.copy()
    origin_year = pd.to_numeric(result["period_start"], errors="coerce")
    if origin_year.isna().any() or not (origin_year % 1 == 0).all():
        raise SourceSchemaError("Forecast origins must be whole numeric years")
    lag_year = origin_year.astype(int) - lookback_years
    origin_index = pd.MultiIndex.from_arrays(
        [result["country_code"], origin_year.astype(int)],
        names=["country_code", "year"],
    )
    lag_index = pd.MultiIndex.from_arrays(
        [result["country_code"], lag_year],
        names=["country_code", "year"],
    )

    origin = wide.reindex(origin_index).reset_index(drop=True)
    lag = wide.reindex(lag_index).reset_index(drop=True)
    if origin.isna().any().any() or lag.isna().any().any():
        raise SourceSchemaError("National DEGURBA panel lacks a required country-year")

    city_origin = pd.to_numeric(result["population_start"], errors="coerce").reset_index(drop=True)
    city_lag = pd.to_numeric(result["population_lag"], errors="coerce").reset_index(drop=True)
    if (
        city_origin.isna().any()
        or city_lag.isna().any()
        or (city_origin <= 0).any()
        or (city_lag <= 0).any()
    ):
        raise SourceSchemaError("Focal-city population endpoints must be positive and numeric")

    # WUP tables display rounded persons. Tolerate at most one person's
    # subtraction discrepancy, then fail rather than manufacture composition.
    origin_city_residual = origin["city"] - city_origin
    lag_city_residual = lag["city"] - city_lag
    if (origin_city_residual < -1).any() or (lag_city_residual < -1).any():
        raise SourceSchemaError("Focal-city population exceeds the national Cities category")
    origin_city_residual = origin_city_residual.clip(lower=0)
    lag_city_residual = lag_city_residual.clip(lower=0)
    origin_total_residual = origin["total"] - city_origin
    lag_total_residual = lag["total"] - city_lag
    available = (origin_total_residual > 0) & (lag_total_residual > 0)

    result["national_context_loo_available"] = available.to_numpy()
    result["national_context_leave_one_city_out"] = True
    result["national_context_uses_future_value"] = False
    result["national_context_lookback_years"] = lookback_years

    def assign_available(column: str, values: pd.Series | np.ndarray) -> None:
        array = np.asarray(values, dtype=float)
        result[column] = np.where(available.to_numpy(), array, np.nan)

    assign_available("national_population_loo_at_origin", origin_total_residual)
    with np.errstate(divide="ignore", invalid="ignore"):
        assign_available("log_national_population_loo_at_origin", np.log(origin_total_residual))
        assign_available(
            "national_population_recent_growth_loo",
            (np.log(origin_total_residual) - np.log(lag_total_residual)) / lookback_years,
        )

    origin_components = {
        "city": origin_city_residual,
        "town": origin["town_and_semi_dense"],
        "rural": origin["rural"],
    }
    lag_components = {
        "city": lag_city_residual,
        "town": lag["town_and_semi_dense"],
        "rural": lag["rural"],
    }
    for label in ("city", "town", "rural"):
        origin_share = origin_components[label] / origin_total_residual
        lag_share = lag_components[label] / lag_total_residual
        assign_available(f"national_{label}_share_loo_at_origin", origin_share)
        assign_available(f"national_{label}_share_change_loo", origin_share - lag_share)

    valid = result["national_context_loo_available"]
    share_columns = [
        "national_city_share_loo_at_origin",
        "national_town_share_loo_at_origin",
        "national_rural_share_loo_at_origin",
    ]
    if valid.any() and not np.allclose(
        result.loc[valid, share_columns].sum(axis=1), 1.0, atol=1e-10
    ):
        raise SourceSchemaError("Leave-one-city-out national shares do not sum to one")
    return result

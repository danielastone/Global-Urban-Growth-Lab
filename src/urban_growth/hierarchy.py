"""Forecast-origin settlement tiers and compositional balances."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

DEFAULT_ABSOLUTE_THRESHOLDS = (50_000, 100_000, 250_000, 500_000, 1_000_000)
DEFAULT_ABSOLUTE_LABELS = ("<50k", "50-100k", "100-250k", "250-500k", "500k-1m", "1m+")


def assign_origin_tiers(
    frame: pd.DataFrame,
    *,
    population_column: str = "population_start",
    city_column: str = "city_id",
    country_column: str = "country_code",
    origin_column: str = "period_start",
    rank_groups: Mapping[str, tuple[int, int | None]] | None = None,
) -> pd.DataFrame:
    """Assign absolute and relative tiers using information at forecast origin only.

    Relative tiers are identity/count based, not population-share based.  Membership
    is copied onto the forecast interval and must not be recomputed at its endpoint.
    """
    require_columns(
        frame,
        {city_column, population_column, country_column, origin_column},
        source_name="tier input",
    )
    if frame[population_column].isna().any() or (frame[population_column] <= 0).any():
        raise SourceSchemaError("Tier population must be positive and non-null")
    result = frame.copy()
    if result.duplicated([city_column, origin_column]).any():
        raise SourceSchemaError("Tier input city-origin keys must be unique")
    result["tier_abs_origin"] = pd.cut(
        result[population_column],
        bins=(-np.inf, *DEFAULT_ABSOLUTE_THRESHOLDS, np.inf),
        labels=DEFAULT_ABSOLUTE_LABELS,
        right=False,
    )
    groups = rank_groups or {
        "primate": (1, 1),
        "other_top5": (2, 5),
        "rank_6_20": (6, 20),
        "rank_21_plus": (21, None),
    }
    ranked = result.sort_values(
        [country_column, origin_column, population_column, city_column],
        ascending=[True, True, False, True],
    )
    ranked["_rank_origin"] = ranked.groupby(
        [country_column, origin_column], observed=True
    ).cumcount() + 1
    rank = ranked["_rank_origin"].reindex(result.index)
    result["rank_origin"] = rank.astype(int)
    result["tier_rel_origin"] = pd.Series(index=result.index, dtype="object")
    for label, (lower, upper) in groups.items():
        mask = rank.ge(lower) if upper is None else rank.between(lower, upper)
        result.loc[mask, "tier_rel_origin"] = label
    if result["tier_rel_origin"].isna().any():
        raise SourceSchemaError("Relative tier registry does not cover every origin rank")
    result["tier_assignment_timing"] = "forecast_origin_fixed"
    return result


def fixed_membership_ilr_balance(
    frame: pd.DataFrame,
    *,
    tier_column: str,
    origin_population_column: str = "population_start",
    endpoint_population_column: str = "population_end",
    country_column: str = "country_code",
    origin_column: str = "period_start",
    balance_name: str = "tier_ilr_change",
) -> pd.DataFrame:
    """Calculate adjacent-tier ILR changes with membership fixed at origin.

    For K ordered tiers this returns K-1 sequential balances. Empty or non-positive
    tier cells are not zero-filled; they are excluded and identified explicitly.
    """
    required = {
        tier_column,
        origin_population_column,
        endpoint_population_column,
        country_column,
        origin_column,
    }
    require_columns(frame, required, source_name="ILR input")
    if (frame[[origin_population_column, endpoint_population_column]] <= 0).any().any():
        raise SourceSchemaError("ILR populations must be strictly positive")
    if not isinstance(frame[tier_column].dtype, pd.CategoricalDtype):
        raise SourceSchemaError("ILR tier must be an ordered categorical with fixed labels")
    if not frame[tier_column].cat.ordered:
        raise SourceSchemaError("ILR tier categories must be ordered")
    tiers = list(frame[tier_column].cat.categories)
    grouped = frame.groupby([country_column, origin_column, tier_column], observed=False)[
        [origin_population_column, endpoint_population_column]
    ].sum(min_count=1)
    wide0 = grouped[origin_population_column].unstack(tier_column).reindex(columns=tiers)
    wide1 = grouped[endpoint_population_column].unstack(tier_column).reindex(columns=tiers)
    rows: list[dict[str, object]] = []
    for key in wide0.index:
        start = wide0.loc[key]
        end = wide1.loc[key]
        for split in range(1, len(tiers)):
            left = tiers[:split]
            right = tiers[split:]
            valid = start[left + right].notna().all() and end[left + right].notna().all()
            row = {
                country_column: key[0],
                origin_column: key[1],
                "balance_index": split,
                "left_tiers": "|".join(map(str, left)),
                "right_tiers": "|".join(map(str, right)),
                "ilr_eligible": bool(valid),
                "exclusion_reason": None if valid else "empty_origin_fixed_tier_cell",
                balance_name: np.nan,
            }
            if valid:
                scale = np.sqrt(len(left) * len(right) / (len(left) + len(right)))
                ilr0 = scale * (np.log(start[left]).mean() - np.log(start[right]).mean())
                ilr1 = scale * (np.log(end[left]).mean() - np.log(end[right]).mean())
                row[balance_name] = ilr1 - ilr0
            rows.append(row)
    return pd.DataFrame(rows)

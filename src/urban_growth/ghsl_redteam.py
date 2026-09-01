"""Red-team diagnostics for GHSL fixed/dynamic persistence evidence."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

BIRTH_COLUMN = "GC_UCB_YOB _2025"


def attach_mtuc_birth_year(
    fixed_intervals: pd.DataFrame,
    dynamic_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Attach publisher-declared 2025-centre birth year to fixed-boundary intervals."""
    require_columns(
        fixed_intervals,
        {"city_id", "period_start", "population_start"},
        source_name="GHSL fixed intervals",
    )
    require_columns(
        dynamic_panel,
        {"city_id", BIRTH_COLUMN, "quality_controlled_2025"},
        source_name="GHSL MTUC panel",
    )
    metadata = dynamic_panel.loc[
        dynamic_panel["quality_controlled_2025"], ["city_id", BIRTH_COLUMN]
    ].drop_duplicates()
    reject_duplicate_keys(metadata, ["city_id"], source_name="GHSL MTUC birth metadata")
    if metadata[BIRTH_COLUMN].isna().any():
        raise SourceSchemaError("GHSL MTUC birth metadata is missing for a 2025 centre")
    out = fixed_intervals.merge(metadata, on="city_id", how="left", validate="many_to_one")
    if out[BIRTH_COLUMN].isna().any():
        raise SourceSchemaError("A fixed GHSL interval lacks matched MTUC birth metadata")
    out["centre_birth_year"] = pd.to_numeric(out[BIRTH_COLUMN], errors="coerce")
    if out["centre_birth_year"].isna().any():
        raise SourceSchemaError("GHSL centre birth year is not numeric")
    return out.drop(columns=BIRTH_COLUMN)


def origin_defined_fixed_risk_set(
    fixed_intervals: pd.DataFrame,
    dynamic_panel: pd.DataFrame,
    *,
    minimum_population: float = 50_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply origin-existence and origin-population rules to fixed 2025 polygons.

    The denominator is the full fixed interval set. Eligibility is determined only
    from publisher birth year and population measured at the forecast origin.
    """
    if minimum_population <= 0:
        raise SourceSchemaError("GHSL origin risk-set population threshold must be positive")
    working = attach_mtuc_birth_year(fixed_intervals, dynamic_panel)
    population = pd.to_numeric(working["population_start"], errors="coerce")
    if population.isna().any() or not np.isfinite(population).all():
        raise SourceSchemaError("GHSL origin population must be finite")
    working["origin_exists"] = working["centre_birth_year"].le(working["period_start"])
    working["origin_population_eligible"] = population.ge(minimum_population)
    working["origin_risk_set_eligible"] = (
        working["origin_exists"] & working["origin_population_eligible"]
    )
    working["origin_risk_set_exclusion_reason"] = np.select(
        [
            working["origin_risk_set_eligible"],
            ~working["origin_exists"] & ~working["origin_population_eligible"],
            ~working["origin_exists"],
            ~working["origin_population_eligible"],
        ],
        [
            "",
            "not_yet_born_and_below_threshold",
            "not_yet_born",
            "below_origin_population_threshold",
        ],
        default="unclassified",
    )
    denominator = working.groupby("period_start", observed=True).agg(
        fixed_rows=("city_id", "size"),
        fixed_population=("population_start", "sum"),
        eligible_rows=("origin_risk_set_eligible", "sum"),
    ).reset_index()
    eligible_population = (
        working.loc[working["origin_risk_set_eligible"]]
        .groupby("period_start", observed=True)["population_start"]
        .sum()
    )
    denominator["eligible_population"] = denominator["period_start"].map(
        eligible_population
    ).fillna(0.0)
    denominator["eligible_row_share"] = denominator["eligible_rows"] / denominator["fixed_rows"]
    denominator["eligible_population_share"] = (
        denominator["eligible_population"] / denominator["fixed_population"]
    )
    denominator["minimum_origin_population"] = float(minimum_population)
    denominator["eligibility_uses_future_population"] = False
    denominator["eligibility_uses_2025_birth_metadata"] = True
    eligible = working.loc[working["origin_risk_set_eligible"]].copy()
    if eligible.empty:
        raise SourceSchemaError("GHSL origin-defined risk set is empty")
    return eligible.reset_index(drop=True), denominator


def attach_built_up_growth(
    intervals: pd.DataFrame,
    fixed_panel: pd.DataFrame,
    *,
    lookback_years: int = 5,
) -> pd.DataFrame:
    """Attach recent and future fixed-footprint built-up growth to forecast intervals."""
    require_columns(
        intervals,
        {"city_id", "period_start", "period_end", "outcome_start_year"},
        source_name="GHSL forecast intervals",
    )
    require_columns(
        fixed_panel,
        {"city_id", "year", "built_up_area_m2"},
        source_name="GHSL fixed panel",
    )
    reject_duplicate_keys(fixed_panel, ["city_id", "year"], source_name="GHSL fixed panel")
    lookup = fixed_panel.set_index(["city_id", "year"])["built_up_area_m2"]
    out = intervals.copy()

    def values(years: pd.Series) -> np.ndarray:
        index = pd.MultiIndex.from_arrays([out["city_id"], years])
        return pd.to_numeric(lookup.reindex(index), errors="coerce").to_numpy(dtype=float)

    lag = values(out["period_start"] - lookback_years)
    origin = values(out["period_start"])
    outcome_start = values(out["outcome_start_year"])
    endpoint = values(out["period_end"])
    matrix = np.column_stack([lag, origin, outcome_start, endpoint])
    if not np.isfinite(matrix).all() or (matrix <= 0).any():
        raise SourceSchemaError("GHSL built-up growth requires positive finite endpoints")
    future_years = out["period_end"].to_numpy() - out["outcome_start_year"].to_numpy()
    if (future_years <= 0).any():
        raise SourceSchemaError("GHSL built-up outcome horizon must be positive")
    out["recent_built_up_growth"] = (np.log(origin) - np.log(lag)) / lookback_years
    out["future_built_up_growth"] = (
        np.log(endpoint) - np.log(outcome_start)
    ) / future_years
    return out


def built_up_entanglement_diagnostic(
    intervals: pd.DataFrame,
    fixed_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Measure population-growth persistence before and after built-up residualization.

    This is a source-process diagnostic. It does not identify a causal effect of
    built-up change on population growth.
    """
    working = attach_built_up_growth(intervals, fixed_panel)
    require_columns(
        working,
        {"period_start", "recent_growth", "future_growth", "recent_built_up_growth", "future_built_up_growth"},
        source_name="GHSL built-up entanglement intervals",
    )
    rows: list[dict[str, object]] = []
    for origin, group in working.groupby("period_start", sort=True):
        values = group[
            ["recent_growth", "future_growth", "recent_built_up_growth", "future_built_up_growth"]
        ].astype(float)
        finite = np.isfinite(values).all(axis=1)
        values = values.loc[finite]
        if len(values) < 3:
            continue

        def residual(y: np.ndarray, x: np.ndarray) -> np.ndarray:
            design = np.column_stack([np.ones(len(x)), x])
            beta, *_ = np.linalg.lstsq(design, y, rcond=None)
            return y - design @ beta

        recent_residual = residual(
            values["recent_growth"].to_numpy(), values["recent_built_up_growth"].to_numpy()
        )
        future_residual = residual(
            values["future_growth"].to_numpy(), values["future_built_up_growth"].to_numpy()
        )
        raw_x = values["recent_growth"].to_numpy()
        raw_y = values["future_growth"].to_numpy()
        raw_design = np.column_stack([np.ones(len(raw_x)), raw_x])
        raw_beta, *_ = np.linalg.lstsq(raw_design, raw_y, rcond=None)
        resid_design = np.column_stack([np.ones(len(recent_residual)), recent_residual])
        resid_beta, *_ = np.linalg.lstsq(resid_design, future_residual, rcond=None)
        raw_error = raw_x - raw_y
        residual_error = recent_residual - future_residual
        rows.append(
            {
                "origin": int(origin),
                "n": len(values),
                "population_growth_correlation": float(np.corrcoef(raw_x, raw_y)[0, 1]),
                "recent_built_future_population_correlation": float(
                    np.corrcoef(values["recent_built_up_growth"], raw_y)[0, 1]
                ),
                "residual_population_growth_correlation": float(
                    np.corrcoef(recent_residual, future_residual)[0, 1]
                ),
                "raw_persistence_beta": float(raw_beta[1]),
                "built_adjusted_persistence_beta": float(resid_beta[1]),
                "raw_persistence_mae": float(np.abs(raw_error).mean()),
                "built_adjusted_persistence_mae": float(np.abs(residual_error).mean()),
                "raw_persistence_rmse": float(np.sqrt(np.mean(raw_error**2))),
                "built_adjusted_persistence_rmse": float(np.sqrt(np.mean(residual_error**2))),
                "diagnostic_semantics": "source_process_not_causal_control",
            }
        )
    if not rows:
        raise SourceSchemaError("No GHSL built-up entanglement diagnostics were produced")
    return pd.DataFrame(rows)


def restrict_pre_projection_origins(
    frame: pd.DataFrame,
    *,
    origin_column: str = "origin",
    last_origin: int = 2015,
) -> pd.DataFrame:
    """Restrict a result table to origins at or before the last non-2020 sensitivity origin."""
    require_columns(frame, {origin_column}, source_name="cross-source result table")
    out = frame.loc[pd.to_numeric(frame[origin_column], errors="coerce").le(last_origin)].copy()
    if out.empty:
        raise SourceSchemaError("Origin restriction removed all rows")
    out["cross_source_last_origin"] = int(last_origin)
    out["includes_2020_to_2025"] = False
    return out.reset_index(drop=True)

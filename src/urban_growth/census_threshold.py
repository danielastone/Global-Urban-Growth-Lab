"""National-census validation primitives around the WUP observation threshold."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns


@dataclass(frozen=True)
class DelayInterval:
    """Open interval containing WUP-entry delay relative to census crossing."""

    lower: float
    upper: float


def entry_delay_interval(
    *, crossing_lower: float, crossing_upper: float, entry_lower: float, entry_upper: float
) -> DelayInterval:
    """Return the sharp open bounds (w0 - t1, w1 - t0)."""
    if crossing_lower >= crossing_upper or entry_lower >= entry_upper:
        raise SourceSchemaError("Crossing and entry intervals must have positive width")
    return DelayInterval(entry_lower - crossing_upper, entry_upper - crossing_lower)


def classify_threshold_measurement_band(
    population: pd.Series, *, threshold: float = 50_000, tolerance: float = 2_500
) -> pd.Categorical:
    """Flag observations whose census measurement could plausibly cross the threshold."""
    if threshold <= 0 or tolerance < 0:
        raise SourceSchemaError("Threshold must be positive and tolerance non-negative")
    if population.isna().any() or (population <= 0).any():
        raise SourceSchemaError("Census population must be positive and non-null")
    labels = pd.cut(
        population,
        bins=(-float("inf"), threshold - tolerance, threshold + tolerance, float("inf")),
        labels=("clearly_below", "threshold_uncertain", "clearly_above"),
        include_lowest=True,
        right=False,
    )
    return labels


def validate_boundary_cohort(frame: pd.DataFrame) -> None:
    """Enforce the two-endpoint, comparable-geography audit contract."""
    required = {
        "settlement_id",
        "country_code",
        "origin_year",
        "endpoint_year",
        "population_origin",
        "population_endpoint",
        "geography_status",
    }
    require_columns(frame, required, source_name="census boundary cohort")
    if frame.duplicated(["settlement_id", "origin_year", "endpoint_year"]).any():
        raise SourceSchemaError("Census boundary cohort keys must be unique")
    if (frame["endpoint_year"] <= frame["origin_year"]).any():
        raise SourceSchemaError("Census endpoint must follow origin")
    comparable = {"stable", "official_crosswalk", "harmonized_common_geography"}
    invalid = ~frame["geography_status"].isin(comparable)
    if invalid.any():
        raise SourceSchemaError("Boundary cohort contains unresolved or incomparable geography")
    if frame[["population_origin", "population_endpoint"]].isna().any().any():
        raise SourceSchemaError("Boundary cohort requires both population endpoints")


def origin_defined_threshold_cohort(
    frame: pd.DataFrame,
    *,
    cohort_min: float = 25_000,
    cohort_max: float = 100_000,
) -> pd.DataFrame:
    """Select a threshold-study cohort using origin population only.

    Endpoint population is retained as an outcome but never participates in membership.
    This prevents future growth, threshold crossing, or survival at the endpoint from
    redefining the risk set after the forecast origin.
    """
    validate_boundary_cohort(frame)
    if cohort_min <= 0 or cohort_max <= cohort_min:
        raise SourceSchemaError("Origin cohort bounds must be positive and increasing")
    origin_population = pd.to_numeric(frame["population_origin"], errors="coerce")
    endpoint_population = pd.to_numeric(frame["population_endpoint"], errors="coerce")
    if origin_population.isna().any() or endpoint_population.isna().any():
        raise SourceSchemaError("Threshold cohort populations must be numeric")
    if origin_population.le(0).any() or endpoint_population.le(0).any():
        raise SourceSchemaError("Threshold cohort populations must be positive")
    selected = frame.loc[origin_population.between(cohort_min, cohort_max)].copy()
    if selected.empty:
        raise SourceSchemaError("No settlements fall within the declared origin cohort")
    selected["cohort_population_basis"] = "population_origin"
    selected["cohort_min_population"] = float(cohort_min)
    selected["cohort_max_population"] = float(cohort_max)
    selected["cohort_uses_endpoint_population"] = False
    selected["cohort_defined_at_origin"] = True
    return selected.reset_index(drop=True)

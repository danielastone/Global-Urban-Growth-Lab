"""Validation helpers for border-neutral road-network accessibility pilots."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

REQUIRED_ROUTE_COLUMNS = {
    "focal_city_id",
    "rival_city_id",
    "travel_time_hours",
    "route_distance_km",
    "focal_snap_distance_m",
    "rival_snap_distance_m",
    "route_status",
    "crosses_international_border",
    "border_penalty_applied",
}


def validate_border_neutral_routes(
    routes: pd.DataFrame,
    *,
    max_snap_distance_m: float,
    max_travel_time_hours: float = 8.0,
) -> pd.DataFrame:
    """Validate routed city pairs before H5 exposure construction.

    The contract is deliberately routing-engine agnostic. It accepts an audited table of
    pairwise road-network routes and fails closed if any route embeds a border penalty,
    exceeds preregistered snap/travel-time limits, duplicates a city pair, or is not
    explicitly successful.
    """
    require_columns(routes, REQUIRED_ROUTE_COLUMNS, source_name="road accessibility routes")
    if max_snap_distance_m <= 0:
        raise SourceSchemaError("max_snap_distance_m must be positive")
    if max_travel_time_hours <= 0:
        raise SourceSchemaError("max_travel_time_hours must be positive")
    if routes[["focal_city_id", "rival_city_id"]].isna().any().any():
        raise SourceSchemaError("Route city IDs cannot be missing")
    if (routes["focal_city_id"] == routes["rival_city_id"]).any():
        raise SourceSchemaError("Road accessibility routes must exclude self-pairs")
    if routes.duplicated(["focal_city_id", "rival_city_id"]).any():
        raise SourceSchemaError("Road accessibility routes must contain unique directed city pairs")

    numeric = [
        "travel_time_hours",
        "route_distance_km",
        "focal_snap_distance_m",
        "rival_snap_distance_m",
    ]
    if routes[numeric].isna().any().any():
        raise SourceSchemaError("Successful road routes cannot contain missing numeric values")
    if (routes[numeric] < 0).any().any():
        raise SourceSchemaError("Road route time, distance, and snap distances cannot be negative")
    if routes["route_status"].astype("string").ne("ok").any():
        raise SourceSchemaError("Every routed pair must have route_status='ok'")
    if routes["border_penalty_applied"].fillna(False).astype(bool).any():
        raise SourceSchemaError("Primary H5 routes cannot include an international-border penalty")
    if routes[["focal_snap_distance_m", "rival_snap_distance_m"]].gt(max_snap_distance_m).any().any():
        raise SourceSchemaError("Route snap distance exceeds preregistered maximum")
    if routes["travel_time_hours"].gt(max_travel_time_hours).any():
        raise SourceSchemaError("Route travel time exceeds preregistered routing horizon")

    result = routes.copy()
    result["routing_definition"] = "border_neutral_road_network"
    result["max_snap_distance_m"] = float(max_snap_distance_m)
    result["max_travel_time_hours"] = float(max_travel_time_hours)
    return result


def route_quality_summary(routes: pd.DataFrame) -> pd.DataFrame:
    """Summarize route quality separately for domestic and cross-border pairs."""
    require_columns(
        routes,
        {
            "route_status",
            "crosses_international_border",
            "focal_snap_distance_m",
            "rival_snap_distance_m",
        },
        source_name="road accessibility routes",
    )
    rows: list[dict[str, float | int | bool]] = []
    for cross_border, group in routes.groupby("crosses_international_border", dropna=False):
        success = group["route_status"].astype("string").eq("ok")
        snap_max = group[["focal_snap_distance_m", "rival_snap_distance_m"]].max(axis=1)
        rows.append(
            {
                "crosses_international_border": bool(cross_border),
                "pair_count": len(group),
                "route_success_rate": float(success.mean()) if len(group) else 0.0,
                "median_max_snap_distance_m": float(snap_max.median()) if len(group) else 0.0,
            }
        )
    return pd.DataFrame(rows)

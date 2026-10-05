import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.road_accessibility import route_quality_summary, validate_border_neutral_routes


def _routes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "focal_city_id": ["a", "a", "d"],
            "rival_city_id": ["b", "c", "e"],
            "travel_time_hours": [1.0, 2.5, 0.75],
            "route_distance_km": [70.0, 180.0, 45.0],
            "focal_snap_distance_m": [100.0, 100.0, 75.0],
            "rival_snap_distance_m": [125.0, 250.0, 90.0],
            "route_status": ["ok", "ok", "ok"],
            "crosses_international_border": [False, True, False],
            "border_penalty_applied": [False, False, False],
        }
    )


def test_validate_border_neutral_routes_accepts_clean_pairs() -> None:
    result = validate_border_neutral_routes(_routes(), max_snap_distance_m=500)
    assert (result["routing_definition"] == "border_neutral_road_network").all()
    assert (result["max_snap_distance_m"] == 500.0).all()
    assert (result["max_travel_time_hours"] == 8.0).all()


def test_validate_border_neutral_routes_rejects_border_penalty() -> None:
    routes = _routes()
    routes.loc[1, "border_penalty_applied"] = True
    with pytest.raises(SourceSchemaError, match="border penalty"):
        validate_border_neutral_routes(routes, max_snap_distance_m=500)


def test_validate_border_neutral_routes_rejects_route_failure() -> None:
    routes = _routes()
    routes.loc[1, "route_status"] = "no_route"
    with pytest.raises(SourceSchemaError, match="route_status='ok'"):
        validate_border_neutral_routes(routes, max_snap_distance_m=500)


def test_validate_border_neutral_routes_rejects_excessive_snap() -> None:
    routes = _routes()
    routes.loc[1, "rival_snap_distance_m"] = 501.0
    with pytest.raises(SourceSchemaError, match="snap distance"):
        validate_border_neutral_routes(routes, max_snap_distance_m=500)


def test_validate_border_neutral_routes_rejects_duplicate_directed_pairs() -> None:
    routes = pd.concat([_routes(), _routes().iloc[[0]]], ignore_index=True)
    with pytest.raises(SourceSchemaError, match="unique directed city pairs"):
        validate_border_neutral_routes(routes, max_snap_distance_m=500)


def test_route_quality_summary_separates_cross_border_pairs() -> None:
    routes = _routes()
    routes.loc[1, "route_status"] = "no_route"
    summary = route_quality_summary(routes).set_index("crosses_international_border")
    assert summary.loc[False, "pair_count"] == 2
    assert summary.loc[False, "route_success_rate"] == 1.0
    assert summary.loc[True, "pair_count"] == 1
    assert summary.loc[True, "route_success_rate"] == 0.0
    assert summary.loc[True, "median_max_snap_distance_m"] == 250.0

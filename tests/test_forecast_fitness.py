import pandas as pd
import pytest

from urban_growth.forecast_fitness import (
    evaluate_fitness_gated_persistence_baselines,
    evaluate_point_in_time_persistence_baselines,
    fitness_gated_forecast_panel,
    fitness_gated_persistence_errors,
    point_in_time_fitness_gated_forecast_panel,
    point_in_time_persistence_errors,
)
from urban_growth.io import SourceSchemaError


def forecast_panel() -> pd.DataFrame:
    rows = []
    specs = {
        "A": [(2000, 2005, 0.010, 0.012), (2005, 2010, 0.012, 0.014), (2010, 2015, 0.014, 0.013)],
        "B": [(2000, 2005, 0.020, 0.018), (2005, 2010, 0.018, 0.016), (2010, 2015, 0.016, 0.015)],
        "C": [(2000, 2005, -0.005, -0.004), (2005, 2010, -0.004, -0.002), (2010, 2015, -0.002, 0.001)],
    }
    for city_id, intervals in specs.items():
        for start, end, recent, future in intervals:
            rows.append(
                {
                    "city_id": city_id,
                    "country_code": "AAA" if city_id != "C" else "BBB",
                    "period_start": start,
                    "period_end": end,
                    "population_start": 50_000,
                    "recent_growth": recent,
                    "future_growth": future,
                    "growth_eligible": True,
                    "point_in_time_available": True,
                }
            )
    frame = pd.DataFrame(rows)
    frame.loc[
        (frame["city_id"] == "B") & (frame["period_start"] == 2010),
        "growth_eligible",
    ] = False
    return frame


def test_fitness_gate_requires_explicit_boolean_eligibility() -> None:
    panel = forecast_panel().drop(columns="growth_eligible")
    with pytest.raises(SourceSchemaError, match="growth_eligible"):
        fitness_gated_forecast_panel(panel)


def test_fitness_gate_excludes_ineligible_rows() -> None:
    result = fitness_gated_forecast_panel(forecast_panel())
    assert not ((result["city_id"] == "B") & (result["period_start"] == 2010)).any()
    assert result["forecast_fitness_gate_passed"].all()
    assert result["forecast_horizon_years"].eq(5.0).all()


def test_point_in_time_gate_requires_explicit_boolean_availability() -> None:
    panel = forecast_panel().drop(columns="point_in_time_available")
    with pytest.raises(SourceSchemaError, match="point_in_time_available"):
        point_in_time_fitness_gated_forecast_panel(panel)


def test_point_in_time_gate_excludes_late_rows_after_fitness_gate() -> None:
    panel = forecast_panel()
    panel.loc[
        (panel["city_id"] == "C") & (panel["period_start"] == 2010),
        "point_in_time_available",
    ] = False
    result = point_in_time_fitness_gated_forecast_panel(panel)
    assert not ((result["city_id"] == "B") & (result["period_start"] == 2010)).any()
    assert not ((result["city_id"] == "C") & (result["period_start"] == 2010)).any()
    assert result["forecast_availability_gate_passed"].all()


def test_persistence_oos_requires_multiple_usable_origins() -> None:
    with pytest.raises(SourceSchemaError, match="at least two rolling origins"):
        evaluate_fitness_gated_persistence_baselines(forecast_panel(), [2005])


def test_persistence_oos_scores_only_fitness_eligible_test_rows() -> None:
    result = evaluate_fitness_gated_persistence_baselines(forecast_panel(), [2005, 2010])
    assert {"zero_growth", "persistence"}.issubset(set(result["model"]))
    assert result["fitness_gate_enforced"].all()
    assert result["benchmark_stage"].eq("retrospective_persistence_only").all()
    assert result["forecast_horizon_years"].eq(5.0).all()
    counts = result.pivot(index="origin", columns="model", values="n")
    assert counts.loc[2005, "persistence"] == 3
    assert counts.loc[2010, "persistence"] == 2


def test_persistence_oos_rejects_mixed_forecast_horizons() -> None:
    panel = forecast_panel()
    panel.loc[(panel["city_id"] == "A") & (panel["period_start"] == 2000), "period_end"] = 2010
    with pytest.raises(SourceSchemaError, match="cannot pool mixed forecast horizons"):
        evaluate_fitness_gated_persistence_baselines(panel, [2005, 2010])


def test_point_in_time_persistence_cannot_score_late_test_rows() -> None:
    panel = forecast_panel()
    panel.loc[
        (panel["city_id"] == "C") & (panel["period_start"] == 2010),
        "point_in_time_available",
    ] = False
    result = evaluate_point_in_time_persistence_baselines(panel, [2005, 2010])
    counts = result.pivot(index="origin", columns="model", values="n")
    assert counts.loc[2010, "persistence"] == 1
    assert result["fitness_gate_enforced"].all()
    assert result["availability_gate_enforced"].all()
    assert result["benchmark_stage"].eq("point_in_time_persistence_only").all()


def test_row_level_errors_cannot_reintroduce_ineligible_rows() -> None:
    errors = fitness_gated_persistence_errors(forecast_panel(), [2005, 2010])
    excluded = errors.loc[(errors["city_id"] == "B") & (errors["origin"] == 2010)]
    assert excluded.empty
    assert errors["fitness_gate_enforced"].all()
    assert errors["forecast_horizon_years"].eq(5.0).all()


def test_point_in_time_errors_cannot_reintroduce_late_rows() -> None:
    panel = forecast_panel()
    panel.loc[
        (panel["city_id"] == "C") & (panel["period_start"] == 2010),
        "point_in_time_available",
    ] = False
    errors = point_in_time_persistence_errors(panel, [2005, 2010])
    excluded = errors.loc[(errors["city_id"] == "C") & (errors["origin"] == 2010)]
    assert excluded.empty
    assert errors["availability_gate_enforced"].all()

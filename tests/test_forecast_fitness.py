import pandas as pd
import pytest

from urban_growth.forecast_fitness import (
    evaluate_fitness_gated_persistence_baselines,
    fitness_gated_forecast_panel,
    fitness_gated_persistence_errors,
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


def test_persistence_oos_requires_multiple_usable_origins() -> None:
    with pytest.raises(SourceSchemaError, match="at least two rolling origins"):
        evaluate_fitness_gated_persistence_baselines(forecast_panel(), [2005])


def test_persistence_oos_scores_only_fitness_eligible_test_rows() -> None:
    result = evaluate_fitness_gated_persistence_baselines(forecast_panel(), [2005, 2010])
    assert {"zero_growth", "persistence"}.issubset(set(result["model"]))
    assert result["fitness_gate_enforced"].all()
    assert result["benchmark_stage"].eq("persistence_only").all()
    counts = result.pivot(index="origin", columns="model", values="n")
    assert counts.loc[2005, "persistence"] == 3
    assert counts.loc[2010, "persistence"] == 2


def test_row_level_errors_cannot_reintroduce_ineligible_rows() -> None:
    errors = fitness_gated_persistence_errors(forecast_panel(), [2005, 2010])
    excluded = errors.loc[(errors["city_id"] == "B") & (errors["origin"] == 2010)]
    assert excluded.empty
    assert errors["fitness_gate_enforced"].all()

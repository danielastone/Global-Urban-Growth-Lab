from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.ghsl_redteam import (
    BIRTH_COLUMN,
    built_up_entanglement_diagnostic,
    origin_defined_fixed_risk_set,
    restrict_pre_projection_origins,
)


def _dynamic_births() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": ["a", "b", "c"],
            BIRTH_COLUMN: [1975, 2000, 1980],
            "quality_controlled_2025": [True, True, True],
        }
    )


def test_origin_defined_risk_set_uses_birth_and_origin_population_only() -> None:
    fixed = pd.DataFrame(
        {
            "city_id": ["a", "b", "c"],
            "period_start": [1990, 1990, 1990],
            "population_start": [60_000, 300_000, 40_000],
            "period_end": [1995, 1995, 1995],
        }
    )
    eligible, coverage = origin_defined_fixed_risk_set(fixed, _dynamic_births())
    assert eligible["city_id"].tolist() == ["a"]
    assert coverage.loc[0, "fixed_rows"] == 3
    assert coverage.loc[0, "eligible_rows"] == 1
    assert coverage.loc[0, "eligibility_uses_future_population"] == False


def test_origin_defined_risk_set_is_invariant_to_endpoint_population() -> None:
    fixed = pd.DataFrame(
        {
            "city_id": ["a", "c"],
            "period_start": [1990, 1990],
            "population_start": [60_000, 40_000],
            "population_end": [1, 10_000_000],
        }
    )
    first, _ = origin_defined_fixed_risk_set(fixed, _dynamic_births())
    changed = fixed.assign(population_end=[10_000_000, 1])
    second, _ = origin_defined_fixed_risk_set(changed, _dynamic_births())
    assert first["city_id"].tolist() == second["city_id"].tolist() == ["a"]


def test_built_up_partialling_removes_constructed_common_signal() -> None:
    cities = [f"city-{i}" for i in range(10)]
    fixed_panel_rows = []
    intervals = []
    recent_built = np.linspace(0.01, 0.05, len(cities))
    future_built = recent_built.copy()
    recent_noise = np.array([-2, -1, 0, 1, 2, -2, -1, 0, 1, 2]) * 0.001
    future_noise = np.array([1, -2, 2, 0, -1, 2, 0, -2, 1, -1]) * 0.001
    for i, city in enumerate(cities):
        lag = 100.0
        origin = lag * np.exp(recent_built[i] * 5)
        endpoint = origin * np.exp(future_built[i] * 5)
        fixed_panel_rows.extend(
            [
                {"city_id": city, "year": 1985, "built_up_area_m2": lag},
                {"city_id": city, "year": 1990, "built_up_area_m2": origin},
                {"city_id": city, "year": 1995, "built_up_area_m2": endpoint},
            ]
        )
        intervals.append(
            {
                "city_id": city,
                "period_start": 1990,
                "period_end": 1995,
                "outcome_start_year": 1990,
                "recent_growth": recent_built[i] + recent_noise[i],
                "future_growth": future_built[i] + future_noise[i],
            }
        )
    result = built_up_entanglement_diagnostic(pd.DataFrame(intervals), pd.DataFrame(fixed_panel_rows))
    assert result.loc[0, "population_growth_correlation"] > 0.9
    assert abs(result.loc[0, "residual_population_growth_correlation"]) < 0.5
    assert result.loc[0, "diagnostic_semantics"] == "source_process_not_causal_control"


def test_restrict_pre_projection_origins_excludes_2020() -> None:
    frame = pd.DataFrame({"origin": [1985, 2015, 2020], "mae": [1.0, 2.0, 3.0]})
    result = restrict_pre_projection_origins(frame)
    assert result["origin"].tolist() == [1985, 2015]
    assert result["includes_2020_to_2025"].eq(False).all()

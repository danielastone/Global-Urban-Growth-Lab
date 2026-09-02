import numpy as np
import pandas as pd
import pytest

from urban_growth.density_validation import (
    census_density_panel,
    clean_c3_leave_region_out,
    density_discrepancy_bootstrap,
)
from urban_growth.io import SourceSchemaError


def _density_input() -> pd.DataFrame:
    rows = []
    for i in range(18):
        census = 30_000 + i * 20_000
        surface = 1_000 + i * 80
        rows.append({
            "city_id": f"C{i}", "year": 2020, "pilot_region": f"R{i % 6}",
            "census_population": census, "ghs_population": census * (0.8 + i / 50),
            "built_up_surface_m2": surface, "built_up_volume_m3": surface * (4 + i / 10),
            "built_up_surface_annualized_growth": i / 1000,
            "census_population_support_id": f"S{i}", "denominator_support_id": f"S{i}",
            "population_status": "direct_enumeration", "geography_status": "stable",
        })
    return pd.DataFrame(rows)


def test_density_panel_uses_logs_and_registry_ids() -> None:
    result = census_density_panel(_density_input())
    first = result.iloc[0]
    assert first["census_pop_per_built_surface"] == pytest.approx(np.log(30))
    assert first["ghs_census_log_population_discrepancy"] == pytest.approx(np.log(0.8))
    assert first["census_pop_per_built_surface_metric_id"] == "census_pop_per_built_surface"
    assert first["ghs_pop_per_built_surface_metric_id"] == "pop_per_built_surface"


def test_density_panel_rejects_support_mismatch() -> None:
    frame = _density_input()
    frame.loc[0, "denominator_support_id"] = "different"
    with pytest.raises(SourceSchemaError, match="supports must match"):
        census_density_panel(frame)


def test_density_discrepancy_bootstrap_clusters_regions() -> None:
    result = density_discrepancy_bootstrap(
        census_density_panel(_density_input()), repetitions=100, seed=7
    )
    assert result["bootstrap_cluster"].eq("pilot_region").all()
    assert (result["pilot_region_clusters"] >= 2).all()
    assert result["mean_log_discrepancy_ci_lower"].notna().all()


def test_clean_c3_compares_both_features_to_neither() -> None:
    frame = pd.DataFrame({
        "city_id": [f"C{i}" for i in range(18)],
        "pilot_region": [f"R{i % 6}" for i in range(18)],
        "prior_built_surface_annualized_log_growth": np.linspace(0.001, 0.03, 18),
        "prior_log_volume_per_surface": np.linspace(1.2, 2.0, 18),
    })
    frame["census_density_annualized_log_change"] = (
        2 * frame["prior_built_surface_annualized_log_growth"]
    )
    result = clean_c3_leave_region_out(frame).set_index("model")
    assert result.loc["prior_built_surface_growth", "rmse"] < result.loc[
        "neither_intercept_only", "rmse"
    ]

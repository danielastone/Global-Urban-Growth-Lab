import numpy as np
import pandas as pd
import pytest

from urban_growth.dynamic_estimators import (
    bootstrap_dynamic_hierarchy,
    common_dynamic_sample,
    estimator_disagreement_report,
    estimator_registry,
    fit_dynamic_hierarchy,
    simulate_bootstrap_coverage,
    simulate_dynamic_hierarchy,
)
from urban_growth.io import SourceSchemaError


def simulated_panel(seed: int = 9, *, cities: int = 80, periods: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    country = np.repeat(np.arange(8), cities // 8)
    city_effect = rng.normal(0, 0.5, cities)
    lagged = rng.normal(size=cities)
    rows = []
    for period in range(periods):
        shock = rng.normal(0, 0.08, 8)
        x = rng.normal(size=cities)
        outcome = 0.55 * lagged + 0.3 * x + city_effect + shock[country] + rng.normal(
            0, 0.25, cities
        )
        for index in range(cities):
            rows.append(
                {
                    "city_id": index,
                    "country_code": country[index],
                    "period": period,
                    "growth": outcome[index],
                    "lagged_growth": lagged[index],
                    "x": x[index],
                }
            )
        lagged = outcome
    return pd.DataFrame(rows)


def test_registry_keeps_gmm_unimplemented_and_roles_explicit() -> None:
    registry = estimator_registry().set_index("estimator_id")
    assert not registry.loc["restricted_dynamic_gmm", "implemented"]
    assert registry.loc["pooled_dynamic", "role"] == "primary predictive benchmark"
    assert "Nickell" in registry.loc["city_fe_dynamic", "role"]


def test_common_sample_applies_same_complete_case_and_cell_rules() -> None:
    source = simulated_panel(cities=16)
    source.loc[source["city_id"].eq(0) & source["period"].eq(2), "x"] = np.nan
    sample = common_dynamic_sample(
        source, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"]
    )
    assert not sample.isna().any().any()
    assert sample["city_id"].value_counts().min() >= 4
    assert sample["country_period"].value_counts().min() >= 2


def test_common_sample_rejects_duplicate_city_periods() -> None:
    source = simulated_panel(cities=16)
    with pytest.raises(SourceSchemaError, match="duplicate keys"):
        common_dynamic_sample(
            pd.concat([source, source.iloc[[0]]]), outcome="growth",
            lagged_outcome="lagged_growth", covariates=["x"],
        )


def test_hierarchy_recovers_parameters_within_declared_single_panel_tolerances() -> None:
    sample = common_dynamic_sample(
        simulated_panel(), outcome="growth", lagged_outcome="lagged_growth", covariates=["x"]
    )
    result = fit_dynamic_hierarchy(
        sample, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"]
    )
    persistence = result.loc[result["term"].eq("lagged_growth")].set_index("estimator_id")
    covariate = result.loc[result["term"].eq("x")].set_index("estimator_id")
    assert set(persistence.index) == {
        "pooled_dynamic", "city_fe_dynamic", "half_panel_jackknife"
    }
    assert abs(covariate.loc["half_panel_jackknife", "estimate"] - 0.3) < 0.08
    assert abs(persistence.loc["half_panel_jackknife", "estimate"] - 0.55) < 0.08
    assert persistence.loc["half_panel_jackknife", "n_rows"] == len(sample)


def test_disagreement_report_flags_sign_and_magnitude() -> None:
    estimates = pd.DataFrame(
        {
            "estimator_id": [
                "pooled_dynamic", "city_fe_dynamic", "half_panel_jackknife"
            ],
            "term": ["lagged_growth"] * 3,
            "estimate": [0.4, -0.1, 0.2],
        }
    )
    report = estimator_disagreement_report(estimates, practical_tolerance=0.1)
    assert bool(report.loc[0, "sign_disagreement"])
    assert bool(report.loc[0, "practical_disagreement"])
    assert bool(report.loc[0, "must_report_disagreement"])


def test_simulation_grid_reports_bias_without_guaranteeing_correction_wins() -> None:
    result = simulate_dynamic_hierarchy(
        persistence_values=(0.2, 0.8), panel_lengths=(6, 8), replications=2,
        cities=24, countries=4, seed=2,
    )
    assert len(result) == 12
    assert set(result["estimator_id"]) == {
        "pooled_dynamic", "city_fe_dynamic", "half_panel_jackknife"
    }
    assert result["replications"].eq(2).all()
    assert result[["mean_estimate", "bias", "rmse"]].notna().all().all()


def test_multiplier_bootstrap_is_deterministic_and_covers_corrected_estimator() -> None:
    sample = common_dynamic_sample(
        simulated_panel(cities=24), outcome="growth", lagged_outcome="lagged_growth",
        covariates=["x"],
    )
    first = bootstrap_dynamic_hierarchy(
        sample, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"],
        replications=20, seed=11,
    )
    second = bootstrap_dynamic_hierarchy(
        sample, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"],
        replications=20, seed=11,
    )
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 6
    corrected = first.loc[first["estimator_id"].eq("half_panel_jackknife")]
    assert corrected["bootstrap_std_error"].gt(0).all()
    assert corrected["confidence_lower"].lt(corrected["point_estimate"]).all()
    assert corrected["confidence_upper"].gt(corrected["point_estimate"]).all()
    assert not first["production_replications"].any()


def test_multiplier_bootstrap_rejects_too_few_draws() -> None:
    sample = common_dynamic_sample(
        simulated_panel(cities=16), outcome="growth", lagged_outcome="lagged_growth",
        covariates=["x"],
    )
    with pytest.raises(SourceSchemaError, match="at least 20"):
        bootstrap_dynamic_hierarchy(
            sample, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"],
            replications=19,
        )


def test_coverage_smoke_run_cannot_pass_production_gate() -> None:
    result = simulate_bootstrap_coverage(
        persistence_values=(0.6,), panel_lengths=(6,), simulation_replications=2,
        bootstrap_replications=20, cities=24, countries=4, seed=4,
    )
    assert len(result) == 3
    assert not result["production_design"].any()
    assert result["coverage_gate_pass"].isna().all()
    assert result["evaluated_panels"].eq(2).all()
    assert result["median_interval_width"].gt(0).all()

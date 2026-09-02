from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from urban_growth.density_model import (
    density_covariate_registry,
    density_model_preregistration,
    require_density_model_run,
)
from urban_growth.io import SourceSchemaError
from urban_growth.result_manifest import file_sha256


def registered_outcome(tmp_path: Path, *, outcome_id: str = "census_density_change") -> Path:
    output = tmp_path / "outputs" / "density_outcome.csv"
    output.parent.mkdir()
    frame = pd.DataFrame([{
        "outcome_id": outcome_id,
        "density_metric_id": "census_pop_per_built_surface",
        "spatial_support": "enumerated_support",
        "census_vintage": "pilot_2020",
        "value": 0.01,
    }])
    frame.to_csv(output, index=False)
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{
        "path": "outputs/density_outcome.csv",
        "sha256": file_sha256(output),
        "rows": 1,
        "columns": len(frame.columns),
    }]).to_csv(manifest, index=False)
    return manifest


def run_args(tmp_path: Path, **overrides) -> dict:
    values = {
        "outcome_role": "primary_direct_count",
        "outcome_id": "census_density_change",
        "outcome_metric_id": "census_pop_per_built_surface",
        "covariate_ids": ["built_surface_share"],
        "origin": 2010,
        "model_form": "change",
        "timing_basis": "retrospective_measurement",
        "outcome_manifest_path": registered_outcome(tmp_path),
        "manifest_root": tmp_path,
    }
    values.update(overrides)
    return values


def test_covariate_registry_separates_measurement_and_public_availability() -> None:
    registry = density_covariate_registry().set_index("covariate_id")
    assert registry.loc["national_envelope_wup", "admissible_role"] == "comparator_only"
    assert registry.loc["viirs_night_lights", "admissible_role"] == "sensitivity_only"
    assert registry.loc["mean_height_ghsl_2018", "publicly_available_from"] == 2020
    assert registry.loc["mean_height_open_buildings", "publicly_available_from"] == 2024
    assert registry.loc["mean_height_open_buildings", "retrospective_level_from"] == 2016
    assert registry.loc["mean_height_open_buildings", "retrospective_change_from"] == 2017
    assert registry.loc["terrain_slope", "retrospective_level_from"] == 1975


def test_preregistration_locks_cluster_scope_and_pass_rule() -> None:
    primary = density_model_preregistration().query(
        "specification_id == 'density_change_primary'"
    ).iloc[0]
    assert "contemporaneous_country_density_mean" in primary["comparators"]
    assert primary["bootstrap_cluster"] == "state_or_entidad_within_country"
    assert primary["inference_scope"] == "pilot_regions_not_country_generalization"
    assert primary["pass_rule"] == "rmse_improvement_lower_95ci_at_least_5pct_and_mae_not_worse"
    assert primary["minimum_relative_rmse_improvement"] == 0.05
    assert primary["failure_language"] == "open-data density model not supported"


def test_primary_run_requires_manifest_verified_direct_count_outcome(tmp_path: Path) -> None:
    args = run_args(tmp_path)
    output = tmp_path / "outputs" / "density_outcome.csv"
    output.write_text(output.read_text() + "\n", encoding="utf-8")
    with pytest.raises(SourceSchemaError, match="verification failed"):
        require_density_model_run(**args)


def test_manifest_without_qualifying_outcome_reports_absence(tmp_path: Path) -> None:
    args = run_args(tmp_path)
    output = tmp_path / "outputs" / "density_outcome.csv"
    frame = pd.DataFrame({"unrelated_result": [1.0]})
    frame.to_csv(output, index=False)
    pd.DataFrame([{
        "path": "outputs/density_outcome.csv",
        "sha256": file_sha256(output),
        "rows": 1,
        "columns": 1,
    }]).to_csv(tmp_path / "manifest.csv", index=False)
    with pytest.raises(SourceSchemaError, match="no qualifying"):
        require_density_model_run(**args)


def test_unregistered_and_sensitivity_covariates_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(SourceSchemaError, match="Unregistered"):
        require_density_model_run(**run_args(tmp_path, covariate_ids=["new_feature"]))
    second = tmp_path / "second"
    second.mkdir()
    with pytest.raises(SourceSchemaError, match="not admissible"):
        require_density_model_run(**run_args(second, covariate_ids=["viirs_night_lights"]))


def test_retrospective_timing_does_not_claim_historical_public_availability(tmp_path: Path) -> None:
    require_density_model_run(**run_args(tmp_path, covariate_ids=["terrain_slope"]))
    second = tmp_path / "second"
    second.mkdir()
    with pytest.raises(SourceSchemaError, match="unavailable at origin 2010 under real_time"):
        require_density_model_run(
            **run_args(second, covariate_ids=["terrain_slope"], timing_basis="real_time")
        )


def test_open_buildings_change_has_separate_measurement_and_release_dates(tmp_path: Path) -> None:
    require_density_model_run(
        **run_args(tmp_path, covariate_ids=["mean_height_open_buildings"], origin=2017)
    )
    second = tmp_path / "second"
    second.mkdir()
    with pytest.raises(SourceSchemaError, match="unavailable at origin 2020 under real_time"):
        require_density_model_run(
            **run_args(
                second,
                covariate_ids=["mean_height_open_buildings"],
                origin=2020,
                timing_basis="real_time",
            )
        )

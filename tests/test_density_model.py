import pytest

from urban_growth.density_model import (
    density_covariate_registry,
    density_model_preregistration,
    require_density_model_run,
)
from urban_growth.io import SourceSchemaError


def test_covariate_registry_excludes_population_derived_features() -> None:
    registry = density_covariate_registry().set_index("covariate_id")
    assert registry.loc["national_envelope_wup", "admissible_role"] == "comparator_only"
    assert registry.loc["viirs_night_lights", "admissible_role"] == "sensitivity_only"
    assert registry.loc["mean_height_ghsl_2018", "first_valid_origin"] == 2020
    assert registry.loc["mean_height_open_buildings", "first_valid_origin"] == 2024


def test_preregistration_locks_failure_language_and_baseline() -> None:
    primary = (
        density_model_preregistration()
        .query("specification_id == 'density_change_primary'")
        .iloc[0]
    )
    assert "contemporaneous_country_density_mean" in primary["comparators"]
    assert primary["bootstrap_cluster"] == "country"
    assert primary["failure_language"] == "open-data density model not supported"


def test_primary_run_fails_without_direct_count_outcome() -> None:
    with pytest.raises(SourceSchemaError, match="registered direct-count"):
        require_density_model_run(
            outcome_role="primary_direct_count",
            covariate_ids=["built_surface_share"],
            outcome_registered=False,
            expected_manifest_requested=True,
        )


def test_unregistered_and_sensitivity_covariates_fail_closed() -> None:
    with pytest.raises(SourceSchemaError, match="Unregistered"):
        require_density_model_run(
            outcome_role="primary_direct_count",
            covariate_ids=["new_feature"],
            outcome_registered=True,
            expected_manifest_requested=True,
        )
    with pytest.raises(SourceSchemaError, match="not admissible"):
        require_density_model_run(
            outcome_role="primary_direct_count",
            covariate_ids=["viirs_night_lights"],
            outcome_registered=True,
            expected_manifest_requested=True,
        )


def test_real_run_requires_expected_manifest() -> None:
    with pytest.raises(SourceSchemaError, match="expected-output manifest"):
        require_density_model_run(
            outcome_role="primary_direct_count",
            covariate_ids=["terrain_slope"],
            outcome_registered=True,
            expected_manifest_requested=False,
        )

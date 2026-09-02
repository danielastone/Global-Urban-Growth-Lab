import pandas as pd
import pytest

from urban_growth.density_metrics import (
    attach_density_metric_references,
    density_metric_registry,
    require_density_metric_role,
    validate_density_metric_registry,
)
from urban_growth.io import SourceSchemaError


def test_density_registry_contains_locked_initial_set() -> None:
    registry = density_metric_registry().set_index("metric_id")
    assert set(registry.index) == {
        "pop_per_land_area",
        "pop_per_built_surface",
        "pop_per_built_volume",
        "pop_per_residential_volume",
        "census_pop_per_built_surface",
        "census_pop_per_built_volume",
        "built_surface_per_land_area",
        "volume_per_surface",
    }
    assert registry["formula"].str.startswith("log(").all()


def test_committed_density_registry_matches_executable_policy() -> None:
    committed = pd.read_csv("data/density_metric_registry.csv")
    pd.testing.assert_frame_equal(committed, density_metric_registry(), check_dtype=False)


def test_entangled_metrics_are_sensitivity_only() -> None:
    registry = density_metric_registry()
    entangled = registry.loc[registry["lineage_status"].eq("lineage_entangled")]
    assert entangled["admissible_roles"].eq("sensitivity_only").all()
    with pytest.raises(SourceSchemaError, match="not admissible as outcome"):
        require_density_metric_role("pop_per_built_surface", "outcome")
    with pytest.raises(SourceSchemaError, match="not admissible as origin_available_predictor"):
        require_density_metric_role(
            "pop_per_built_surface", "origin_available_predictor", origin=2020
        )


def test_2018_height_metrics_are_unavailable_before_2020() -> None:
    for metric_id in (
        "pop_per_built_volume",
        "pop_per_residential_volume",
        "census_pop_per_built_volume",
        "volume_per_surface",
    ):
        assert density_metric_registry().set_index("metric_id").loc[
            metric_id, "first_valid_origin"
        ] == 2020
    with pytest.raises(SourceSchemaError, match="unavailable before origin 2020"):
        require_density_metric_role(
            "volume_per_surface", "origin_available_predictor", origin=2015
        )
    record = require_density_metric_role(
        "volume_per_surface", "origin_available_predictor", origin=2020
    )
    assert record["lineage_status"] == "clean"


def test_registry_rejects_entangled_headline_role() -> None:
    registry = density_metric_registry()
    registry.loc[
        registry["metric_id"].eq("pop_per_built_volume"), "admissible_roles"
    ] = "outcome"
    with pytest.raises(SourceSchemaError, match="must be sensitivity-only"):
        validate_density_metric_registry(registry)


def test_registry_rejects_non_log_ratio() -> None:
    registry = density_metric_registry()
    registry.loc[0, "formula"] = "population / land_area_m2"
    with pytest.raises(SourceSchemaError, match="log-ratio"):
        validate_density_metric_registry(registry)


def test_downstream_density_columns_receive_registered_ids() -> None:
    frame = pd.DataFrame({"density": [1.2], "form": [-0.3]})
    result = attach_density_metric_references(
        frame,
        {
            "density": "census_pop_per_built_surface",
            "form": "built_surface_per_land_area",
        },
    )
    assert result["density_metric_id"].tolist() == ["census_pop_per_built_surface"]
    assert result["form_metric_id"].tolist() == ["built_surface_per_land_area"]


def test_downstream_density_columns_reject_unknown_id() -> None:
    with pytest.raises(SourceSchemaError, match="Unregistered downstream"):
        attach_density_metric_references(
            pd.DataFrame({"density": [1.2]}), {"density": "invented_density"}
        )

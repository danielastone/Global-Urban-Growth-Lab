"""Pre-registered open-covariate density-model policy."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from urban_growth.density_metrics import (
    DIRECT_COUNT_DENSITY_OUTCOMES,
    require_density_metric_role,
)
from urban_growth.io import SourceSchemaError
from urban_growth.result_manifest import verify_result_manifest


def density_covariate_registry() -> pd.DataFrame:
    """Return the closed candidate set adopted before direct-count outcomes exist."""
    rows = [
        (
            "built_surface_share",
            "GHS_BUILT_S / fixed_polygon_area",
            "clean",
            "1975-2030_5_year",
            1975, 1975, 1980,
            "primary",
            "cross_section_and_change",
        ),
        (
            "mean_height_ghsl_2018",
            "GHS_BUILT_H_2018",
            "clean",
            "2018_snapshot",
            2020, 2020, None,
            "primary",
            "cross_section_only",
        ),
        (
            "mean_height_open_buildings",
            "Google_Open_Buildings_Temporal_v1",
            "clean",
            "2016-2023_annual",
            2024, 2016, 2017,
            "primary",
            "covered_countries_change_only",
        ),
        (
            "nonresidential_volume_share",
            "GHS_BUILT_V_NRES / GHS_BUILT_V_TOT",
            "clean",
            "1975-2030_constructed",
            2020, 2020, None,
            "primary",
            "fixed_2018_height_composition",
        ),
        (
            "terrain_slope",
            "Copernicus_DEM_GLO30",
            "clean",
            "2011-2015_composite",
            2021, 1975, 1980,
            "primary",
            "time_invariant_constraint",
        ),
        (
            "ghsl_land_fraction",
            "GHSL_land_fraction",
            "clean",
            "registered_product_epochs",
            1975, 1975, 1980,
            "primary",
            "source_epoch_required",
        ),
        (
            "accessibility",
            "registered_accessibility.py_features",
            "clean",
            "modern_registered_vintages",
            2018, 2018, 2019,
            "primary",
            "origin_vintage_required",
        ),
        (
            "viirs_night_lights",
            "VIIRS_annual",
            "clean",
            "2012-present_annual",
            2013, 2012, 2013,
            "sensitivity_only",
            "economic_activity_proxy_not_mechanism",
        ),
        (
            "national_envelope_wup",
            "Module_A_WUP_population",
            "lineage_entangled",
            "WUP_registered_epochs",
            1975, 1975, 1980,
            "comparator_only",
            "excluded_from_clean_covariate_model",
        ),
    ]
    columns = [
        "covariate_id",
        "source",
        "lineage_status",
        "epochs_available",
        "publicly_available_from",
        "retrospective_level_from",
        "retrospective_change_from",
        "admissible_role",
        "temporal_constraint",
    ]
    registry = pd.DataFrame(rows, columns=columns)
    required_complete = [
        "covariate_id", "source", "lineage_status", "epochs_available",
        "publicly_available_from", "retrospective_level_from", "admissible_role",
        "temporal_constraint",
    ]
    if registry["covariate_id"].duplicated().any() or registry[required_complete].isna().any().any():
        raise SourceSchemaError("Density covariate registry must be unique and complete")
    if registry.loc[registry["admissible_role"].eq("primary"), "lineage_status"].ne("clean").any():
        raise SourceSchemaError("Primary density covariates must be lineage-clean")
    return registry


def density_model_preregistration() -> pd.DataFrame:
    """Return outcome, comparator, resampling, and falsification policy."""
    common = {
        "evaluation": "held_out_pilot_cities",
        "bootstrap_cluster": "state_or_entidad_within_country",
        "inference_scope": "pilot_regions_not_country_generalization",
        "primary_loss": "rmse",
        "paired_loss_contrast": "covariate_minus_contemporaneous_country",
        "pass_rule": "rmse_improvement_lower_95ci_at_least_5pct_and_mae_not_worse",
        "minimum_relative_rmse_improvement": 0.05,
        "failure_language": "open-data density model not supported",
    }
    return pd.DataFrame(
        [
            {
                **common,
                "specification_id": "density_change_primary",
                "model_form": "change",
                "outcome": "log_census_density_change_fixed_polygon",
                "outcome_role": "primary_direct_count",
                "comparators": "density_persistence|contemporaneous_country_density_mean|national_envelope_only",
            },
            {
                **common,
                "specification_id": "density_level_cross_section",
                "model_form": "cross_section",
                "outcome": "log_census_density_fixed_polygon",
                "outcome_role": "primary_direct_count",
                "comparators": "contemporaneous_country_density_mean|national_envelope_only",
            },
            {
                **common,
                "specification_id": "density_change_ghs_pop_sensitivity",
                "model_form": "change",
                "outcome": "log_ghs_pop_density_change_fixed_polygon",
                "outcome_role": "lineage_entangled_sensitivity_only",
                "comparators": "density_persistence|contemporaneous_country_density_mean|national_envelope_only",
                "falsification_rule": "never_upgrades_primary_failure",
                "failure_language": "sensitivity result only",
            },
        ]
    )


def _require_registered_density_outcome(
    manifest_path: Path,
    *,
    root: Path,
    outcome_id: str,
    outcome_metric_id: str,
) -> Path:
    """Verify a manifest and the identity/support metadata of its direct-count outcome."""
    verify_result_manifest(manifest_path, root=root)
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        entries = list(csv.DictReader(handle))
    matches = []
    qualifying_files = 0
    for entry in entries:
        path = root / entry["path"]
        frame = pd.read_csv(path)
        required = {"outcome_id", "density_metric_id", "spatial_support", "census_vintage"}
        if not required <= set(frame.columns):
            continue
        if frame.empty:
            continue
        qualifying_files += 1
        identities = frame[list(required)].drop_duplicates()
        if len(identities) != 1:
            raise SourceSchemaError("Registered density outcome has ambiguous identity metadata")
        identity = identities.iloc[0]
        if identity["outcome_id"] == outcome_id and identity["density_metric_id"] == outcome_metric_id:
            if identity["spatial_support"] != "enumerated_support":
                raise SourceSchemaError("Direct-count density outcome must use enumerated support")
            matches.append(path)
    if not matches and not qualifying_files:
        raise SourceSchemaError("Manifest has no qualifying direct-count density outcome artifact")
    if not matches:
        raise SourceSchemaError("No manifest-verified density outcome matches the requested identity")
    if len(matches) > 1:
        raise SourceSchemaError(
            "Multiple manifest-verified density outcomes match the requested identity"
        )
    return matches[0]


def require_density_model_run(
    *,
    outcome_role: str,
    outcome_id: str,
    outcome_metric_id: str,
    covariate_ids: list[str],
    origin: int,
    model_form: str,
    timing_basis: str,
    outcome_manifest_path: Path,
    manifest_root: Path = Path("."),
) -> pd.DataFrame:
    """Fail before fitting when the pre-registered empirical contract is unavailable."""
    registry = density_covariate_registry().set_index("covariate_id")
    unknown = sorted(set(covariate_ids) - set(registry.index))
    if unknown:
        raise SourceSchemaError(f"Unregistered density covariates: {', '.join(unknown)}")
    if outcome_role != "primary_direct_count" or outcome_id not in DIRECT_COUNT_DENSITY_OUTCOMES:
        raise SourceSchemaError("Primary density model requires a registered direct-count outcome")
    expected_estimand = DIRECT_COUNT_DENSITY_OUTCOMES[outcome_id]
    if model_form != expected_estimand:
        raise SourceSchemaError("Model form does not match the registered outcome estimand")
    require_density_metric_role(outcome_metric_id, "outcome", estimand=model_form)
    _require_registered_density_outcome(
        outcome_manifest_path,
        root=manifest_root,
        outcome_id=outcome_id,
        outcome_metric_id=outcome_metric_id,
    )
    selected = registry.loc[covariate_ids]
    blocked = selected["admissible_role"].isin({"comparator_only", "sensitivity_only"})
    if blocked.any():
        raise SourceSchemaError(
            f"Covariates not admissible in the primary model: {', '.join(selected.index[blocked])}"
        )
    if timing_basis not in {"real_time", "retrospective_measurement"}:
        raise SourceSchemaError("Density timing_basis must be registered")
    timing_column = (
        "publicly_available_from"
        if timing_basis == "real_time"
        else f"retrospective_{model_form}_from"
    )
    unavailable = selected[timing_column].isna() | selected[timing_column].gt(origin)
    if unavailable.any():
        raise SourceSchemaError(
            f"Covariates unavailable at origin {origin} under {timing_basis}: "
            f"{', '.join(selected.index[unavailable])}"
        )
    return selected.reset_index()

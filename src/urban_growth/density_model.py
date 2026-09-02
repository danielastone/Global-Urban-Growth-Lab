"""Pre-registered open-covariate density-model policy."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError


def density_covariate_registry() -> pd.DataFrame:
    """Return the closed candidate set adopted before direct-count outcomes exist."""
    rows = [
        (
            "built_surface_share",
            "GHS_BUILT_S / fixed_polygon_area",
            "clean",
            "1975-2030_5_year",
            1975,
            "primary",
            "cross_section_and_change",
        ),
        (
            "mean_height_ghsl_2018",
            "GHS_BUILT_H_2018",
            "clean",
            "2018_snapshot",
            2020,
            "primary",
            "cross_section_only",
        ),
        (
            "mean_height_open_buildings",
            "Google_Open_Buildings_Temporal_v1",
            "clean",
            "2016-2023_annual",
            2024,
            "primary",
            "covered_countries_change_only",
        ),
        (
            "nonresidential_volume_share",
            "GHS_BUILT_V_NRES / GHS_BUILT_V_TOT",
            "clean",
            "1975-2030_constructed",
            2020,
            "primary",
            "fixed_2018_height_composition",
        ),
        (
            "terrain_slope",
            "Copernicus_DEM_GLO30",
            "clean",
            "2011-2015_composite",
            2021,
            "primary",
            "time_invariant_constraint",
        ),
        (
            "ghsl_land_fraction",
            "GHSL_land_fraction",
            "clean",
            "registered_product_epochs",
            1975,
            "primary",
            "source_epoch_required",
        ),
        (
            "accessibility",
            "registered_accessibility.py_features",
            "clean",
            "modern_registered_vintages",
            2018,
            "primary",
            "origin_vintage_required",
        ),
        (
            "viirs_night_lights",
            "VIIRS_annual",
            "clean",
            "2012-present_annual",
            2013,
            "sensitivity_only",
            "economic_activity_proxy_not_mechanism",
        ),
        (
            "national_envelope_wup",
            "Module_A_WUP_population",
            "lineage_entangled",
            "WUP_registered_epochs",
            1975,
            "comparator_only",
            "excluded_from_clean_covariate_model",
        ),
    ]
    columns = [
        "covariate_id",
        "source",
        "lineage_status",
        "epochs_available",
        "first_valid_origin",
        "admissible_role",
        "temporal_constraint",
    ]
    registry = pd.DataFrame(rows, columns=columns)
    if registry["covariate_id"].duplicated().any() or registry[columns].isna().any().any():
        raise SourceSchemaError("Density covariate registry must be unique and complete")
    if registry.loc[registry["admissible_role"].eq("primary"), "lineage_status"].ne("clean").any():
        raise SourceSchemaError("Primary density covariates must be lineage-clean")
    return registry


def density_model_preregistration() -> pd.DataFrame:
    """Return outcome, comparator, resampling, and falsification policy."""
    common = {
        "evaluation": "held_out_pilot_cities",
        "bootstrap_cluster": "country",
        "falsification_rule": "covariate_rmse_not_below_contemporaneous_country_rmse",
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


def require_density_model_run(
    *,
    outcome_role: str,
    covariate_ids: list[str],
    outcome_registered: bool,
    expected_manifest_requested: bool,
) -> pd.DataFrame:
    """Fail before fitting when the pre-registered empirical contract is unavailable."""
    registry = density_covariate_registry().set_index("covariate_id")
    unknown = sorted(set(covariate_ids) - set(registry.index))
    if unknown:
        raise SourceSchemaError(f"Unregistered density covariates: {', '.join(unknown)}")
    if outcome_role == "primary_direct_count" and not outcome_registered:
        raise SourceSchemaError("Primary density model requires a registered direct-count outcome")
    selected = registry.loc[covariate_ids]
    blocked = selected["admissible_role"].isin({"comparator_only", "sensitivity_only"})
    if blocked.any():
        raise SourceSchemaError(
            f"Covariates not admissible in the primary model: {', '.join(selected.index[blocked])}"
        )
    if not expected_manifest_requested:
        raise SourceSchemaError("Real density runs require an expected-output manifest")
    return selected.reset_index()

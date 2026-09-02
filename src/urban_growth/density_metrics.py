"""Locked density-metric registry and downstream lineage enforcement."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

REGISTRY_COLUMNS = [
    "metric_id",
    "numerator_source",
    "denominator_source",
    "formula",
    "lineage_status",
    "lineage_scope",
    "epochs_available",
    "first_valid_origin",
    "admissible_roles",
    "admissible_estimands",
    "temporal_constraint",
]
ALLOWED_LINEAGE = {"clean", "lineage_entangled"}
ALLOWED_ROLES = {"outcome", "origin_available_predictor", "sensitivity_only"}
ALLOWED_ESTIMANDS = {"level", "change"}

DIRECT_COUNT_OUTCOMES = {
    "census_density_level": "level",
    "census_density_change": "change",
    "census_population_growth": "change",
}
DIRECT_COUNT_DENSITY_OUTCOMES = {
    key: value for key, value in DIRECT_COUNT_OUTCOMES.items() if key.startswith("census_density_")
}
ENTANGLED_OUTCOMES = {
    "ghs_pop_density_level_sensitivity": "level",
    "ghs_pop_density_change_sensitivity": "change",
    "wup_population_growth": "change",
    "ghs_pop_population_growth": "change",
}


_DENSITY_METRICS = [
    {
        "metric_id": "pop_per_land_area",
        "numerator_source": "WUP_F21_or_GHS_POP",
        "denominator_source": "WUP_F25_or_UCDB_polygon_area",
        "formula": "log(population / land_area_m2)",
        "lineage_status": "lineage_entangled",
        "lineage_scope": "sensitivity_only_all_outcomes",
        "epochs_available": "1975-2030_GHSL;1975-2050_WUP",
        "first_valid_origin": 1975,
        "admissible_roles": "sensitivity_only",
        "admissible_estimands": "level|change",
        "temporal_constraint": "source_matched_epoch",
    },
    {
        "metric_id": "pop_per_built_surface",
        "numerator_source": "WUP_F21_or_GHS_POP",
        "denominator_source": "GH_BUS_TOT",
        "formula": "log(population / built_up_surface_m2)",
        "lineage_status": "lineage_entangled",
        "lineage_scope": "sensitivity_only_all_outcomes",
        "epochs_available": "1975-2030_5_year",
        "first_valid_origin": 1975,
        "admissible_roles": "sensitivity_only",
        "admissible_estimands": "level|change",
        "temporal_constraint": "source_matched_epoch",
    },
    {
        "metric_id": "pop_per_built_volume",
        "numerator_source": "WUP_F21_or_GHS_POP",
        "denominator_source": "GH_BUV_TOT",
        "formula": "log(population / built_up_volume_m3)",
        "lineage_status": "lineage_entangled",
        "lineage_scope": "sensitivity_only_all_outcomes",
        "epochs_available": "1975-2030_5_year_constructed",
        "first_valid_origin": 2020,
        "admissible_roles": "sensitivity_only",
        "admissible_estimands": "level|change",
        "temporal_constraint": "2018_height_snapshot_available_from_2020",
    },
    {
        "metric_id": "pop_per_residential_volume",
        "numerator_source": "WUP_F21_or_GHS_POP",
        "denominator_source": "GH_BUV_TOT_minus_GH_BUV_NRE",
        "formula": "log(population / (built_up_volume_m3 - built_up_volume_nres_m3))",
        "lineage_status": "lineage_entangled",
        "lineage_scope": "sensitivity_only_all_outcomes",
        "epochs_available": "1975-2030_5_year_constructed",
        "first_valid_origin": 2020,
        "admissible_roles": "sensitivity_only",
        "admissible_estimands": "level|change",
        "temporal_constraint": "2018_height_snapshot_available_from_2020",
    },
    {
        "metric_id": "census_pop_per_built_surface",
        "numerator_source": "direct_census_enumeration_pilot",
        "denominator_source": "GH_BUS_TOT",
        "formula": "log(census_population / built_up_surface_m2)",
        "lineage_status": "clean",
        "lineage_scope": "clean_on_enumerated_support_against_direct_count_outcomes",
        "epochs_available": "pilot_matched_epochs",
        "first_valid_origin": 2010,
        "admissible_roles": "outcome|origin_available_predictor",
        "admissible_estimands": "level|change",
        "temporal_constraint": "pilot_geography_and_epoch_match_required",
    },
    {
        "metric_id": "census_pop_per_built_volume",
        "numerator_source": "direct_census_enumeration_pilot",
        "denominator_source": "GH_BUV_TOT",
        "formula": "log(census_population / built_up_volume_m3)",
        "lineage_status": "clean",
        "lineage_scope": "clean_on_enumerated_support_against_direct_count_outcomes",
        "epochs_available": "pilot_matched_epochs_with_constructed_volume",
        "first_valid_origin": 2020,
        "admissible_roles": "outcome|origin_available_predictor",
        "admissible_estimands": "level|change",
        "temporal_constraint": "2018_height_snapshot_and_pilot_match_required",
    },
    {
        "metric_id": "built_surface_per_land_area",
        "numerator_source": "GH_BUS_TOT",
        "denominator_source": "UCDB_polygon_area",
        "formula": "log(built_up_surface_m2 / polygon_area_m2)",
        "lineage_status": "clean",
        "lineage_scope": "clean_against_direct_count_outcomes_only",
        "epochs_available": "1975-2030_5_year",
        "first_valid_origin": 1975,
        "admissible_roles": "outcome|origin_available_predictor",
        "admissible_estimands": "level|change",
        "temporal_constraint": "fixed_2025_polygon",
    },
    {
        "metric_id": "volume_per_surface",
        "numerator_source": "GH_BUV_TOT",
        "denominator_source": "GH_BUS_TOT",
        "formula": "log(built_up_volume_m3 / built_up_surface_m2)",
        "lineage_status": "clean",
        "lineage_scope": "clean_against_direct_count_outcomes_only",
        "epochs_available": "1975-2030_5_year_constructed",
        "first_valid_origin": 2020,
        "admissible_roles": "origin_available_predictor",
        "admissible_estimands": "level",
        "temporal_constraint": "2018_fixed_height_spatial_composition_not_vertical_change",
    },
]


def validate_density_metric_registry(registry: pd.DataFrame) -> pd.DataFrame:
    """Validate a registry and fail closed on lineage, timing, or role ambiguity."""
    require_columns(registry, set(REGISTRY_COLUMNS), source_name="density metric registry")
    out = registry[REGISTRY_COLUMNS].copy()
    if out["metric_id"].isna().any() or out["metric_id"].duplicated().any():
        raise SourceSchemaError("Density metric registry requires unique nonmissing metric_id")
    if out[REGISTRY_COLUMNS].isna().any().any():
        raise SourceSchemaError("Density metric registry has missing required values")
    if not out["lineage_status"].isin(ALLOWED_LINEAGE).all():
        raise SourceSchemaError("Density metric registry has an invalid lineage_status")
    role_sets = out["admissible_roles"].str.split("|").map(set)
    if role_sets.map(lambda roles: not roles or not roles <= ALLOWED_ROLES).any():
        raise SourceSchemaError("Density metric registry has invalid admissible_roles")
    entangled = out["lineage_status"].eq("lineage_entangled")
    if (~role_sets[entangled].map(lambda roles: roles == {"sensitivity_only"})).any():
        raise SourceSchemaError("Lineage-entangled density metrics must be sensitivity-only")
    if role_sets[~entangled].map(lambda roles: "sensitivity_only" in roles).any():
        raise SourceSchemaError("Clean density metrics cannot be mislabeled sensitivity-only")
    estimand_sets = out["admissible_estimands"].str.split("|").map(set)
    if estimand_sets.map(lambda values: not values or not values <= ALLOWED_ESTIMANDS).any():
        raise SourceSchemaError("Density metric registry has invalid admissible_estimands")
    height_proxy = out["metric_id"].eq("volume_per_surface")
    if estimand_sets[height_proxy].map(lambda values: values != {"level"}).any():
        raise SourceSchemaError("volume_per_surface is a level only, never vertical change")
    if not out["formula"].str.startswith("log(").all():
        raise SourceSchemaError("Every density metric must use log-ratio form")
    origin = pd.to_numeric(out["first_valid_origin"], errors="coerce")
    if origin.isna().any() or (origin < 1975).any():
        raise SourceSchemaError("Density metrics require a valid first_valid_origin")
    fixed_height = out["temporal_constraint"].str.contains("2018_height|2018_fixed_height")
    if (origin[fixed_height] < 2020).any():
        raise SourceSchemaError("2018-height metrics cannot be valid before origin 2020")
    out["first_valid_origin"] = origin.astype(int)
    return out.reset_index(drop=True)


def density_metric_registry() -> pd.DataFrame:
    """Return the locked registry without allowing run-time lineage relabeling."""
    return validate_density_metric_registry(pd.DataFrame(_DENSITY_METRICS))


def density_metric_pair_registry() -> pd.DataFrame:
    """Register predictor/outcome lineage; cleanliness is never a unary property."""
    rows = []
    for metric in density_metric_registry().itertuples(index=False):
        for outcome_id, estimand in {**DIRECT_COUNT_OUTCOMES, **ENTANGLED_OUTCOMES}.items():
            direct = outcome_id in DIRECT_COUNT_OUTCOMES
            headline = direct and metric.lineage_status == "clean"
            rows.append(
                {
                    "predictor_metric_id": metric.metric_id,
                    "predictor_admissible_estimands": metric.admissible_estimands,
                    "outcome_id": outcome_id,
                    "outcome_estimand": estimand,
                    "pair_lineage_status": "clean" if headline else "lineage_entangled",
                    "admissible_analysis_role": "headline" if headline else "sensitivity_only",
                }
            )
    return pd.DataFrame(rows)


def require_density_metric_role(
    metric_id: str,
    role: str,
    *,
    origin: int | None = None,
    outcome_id: str | None = None,
    estimand: str = "level",
    analysis_role: str = "headline",
) -> dict:
    """Return metadata only when metric, estimand, outcome pair and timing are admissible."""
    if role not in ALLOWED_ROLES - {"sensitivity_only"}:
        raise SourceSchemaError(f"Unsupported requested density role: {role}")
    registry = density_metric_registry().set_index("metric_id")
    if metric_id not in registry.index:
        raise SourceSchemaError(f"Unregistered density metric_id: {metric_id}")
    record = registry.loc[metric_id]
    roles = set(record["admissible_roles"].split("|"))
    if role not in roles:
        raise SourceSchemaError(f"Density metric {metric_id} is not admissible as {role}")
    if estimand not in ALLOWED_ESTIMANDS:
        raise SourceSchemaError(f"Unsupported density estimand: {estimand}")
    if estimand not in set(record["admissible_estimands"].split("|")):
        raise SourceSchemaError(f"Density metric {metric_id} is not admissible as {estimand}")
    if role == "origin_available_predictor":
        if outcome_id is None:
            raise SourceSchemaError("Density predictors require a registered outcome_id")
        pairs = density_metric_pair_registry().set_index(["predictor_metric_id", "outcome_id"])
        if (metric_id, outcome_id) not in pairs.index:
            raise SourceSchemaError(f"Unregistered density metric/outcome pair: {metric_id}/{outcome_id}")
        pair = pairs.loc[(metric_id, outcome_id)]
        if analysis_role not in {"headline", "sensitivity_only"}:
            raise SourceSchemaError(f"Unsupported analysis_role: {analysis_role}")
        if pair["admissible_analysis_role"] != analysis_role:
            raise SourceSchemaError(
                f"Density metric/outcome pair {metric_id}/{outcome_id} is "
                f"{pair['admissible_analysis_role']}, not {analysis_role}"
            )
        if origin is None:
            raise SourceSchemaError("Origin-available density predictors require an origin")
        if origin < record["first_valid_origin"]:
            raise SourceSchemaError(
                f"Density metric {metric_id} is unavailable before origin "
                f"{record['first_valid_origin']}"
            )
    result = record.to_dict()
    if role == "origin_available_predictor":
        result.update(pair.to_dict())
    return result


def attach_density_metric_references(
    frame: pd.DataFrame, column_to_metric_id: Mapping[str, str]
) -> pd.DataFrame:
    """Attach a registry ID beside every declared downstream density column."""
    if not column_to_metric_id:
        raise SourceSchemaError("At least one downstream density column must be declared")
    require_columns(frame, set(column_to_metric_id), source_name="downstream density output")
    registry_ids = set(density_metric_registry()["metric_id"])
    unknown = sorted(set(column_to_metric_id.values()) - registry_ids)
    if unknown:
        raise SourceSchemaError(f"Unregistered downstream density metric_id: {', '.join(unknown)}")
    out = frame.copy()
    for column, metric_id in column_to_metric_id.items():
        out[f"{column}_metric_id"] = metric_id
    return out

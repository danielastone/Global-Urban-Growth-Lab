"""Direct national settlement-envelope decomposition from country DEGURBA totals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.density_metrics import density_metric_registry
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

DEGURBA_CATEGORIES = ("city", "town_and_semi_dense", "rural")


def extent_density_reconciliation(
    fixed_polygon_intervals: pd.DataFrame,
    national_intervals: pd.DataFrame,
    constant_membership_intervals: pd.DataFrame,
    *,
    relative_tolerance: float = 1e-6,
    absolute_tolerance: float = 1.0,
) -> pd.DataFrame:
    """Reconcile fixed-polygon extent/density change with F01 Cities change.

    The two fixed-polygon terms use the symmetric two-factor (Shapley) identity,
    so their sum is exactly the change in ``surface * density``.  The remaining
    F01 difference is called reclassification only when an independently
    documented constant-membership F21 universe agrees with the fixed-polygon
    change within the registered tolerance.  Otherwise it remains an
    unidentified composition residual.
    """
    fixed_required = {
        "country_code", "polygon_id", "period_start", "period_end",
        "built_surface_start", "built_surface_end", "density_start", "density_end",
        "density_metric_id", "density_lineage_status",
        "origin_membership_eligible", "origin_membership_validated",
        "origin_membership_basis",
    }
    national_required = {
        "country_code", "period_start", "period_end", "city_population_start",
        "city_population_end", "category_presence_transition",
        "large_share_change_flag", "large_share_change_threshold",
        "composition_discontinuity_flag", "interval_observation_status",
    }
    membership_required = {
        "country_code", "period_start", "period_end", "f21_population_start",
        "f21_population_end", "constant_membership_validated",
        "membership_semantics_source",
    }
    require_columns(fixed_polygon_intervals, fixed_required, source_name="fixed-polygon intervals")
    require_columns(national_intervals, national_required, source_name="national intervals")
    require_columns(
        constant_membership_intervals,
        membership_required,
        source_name="constant-membership intervals",
    )
    reject_duplicate_keys(
        fixed_polygon_intervals,
        ["country_code", "polygon_id", "period_start", "period_end"],
        source_name="fixed-polygon intervals",
    )
    interval_key = ["country_code", "period_start", "period_end"]
    reject_duplicate_keys(national_intervals, interval_key, source_name="national intervals")
    reject_duplicate_keys(
        constant_membership_intervals,
        interval_key,
        source_name="constant-membership intervals",
    )
    if relative_tolerance < 0 or absolute_tolerance < 0:
        raise SourceSchemaError("Reconciliation tolerances must be nonnegative")

    numeric_columns = [
        "built_surface_start", "built_surface_end", "density_start", "density_end",
    ]
    fixed = fixed_polygon_intervals.copy()
    for column in numeric_columns:
        fixed[column] = pd.to_numeric(fixed[column], errors="coerce")
    if fixed[numeric_columns].isna().any().any() or not np.isfinite(
        fixed[numeric_columns].to_numpy(dtype=float)
    ).all():
        raise SourceSchemaError("Fixed-polygon extent and density values must be finite")
    if (fixed[numeric_columns] < 0).any().any():
        raise SourceSchemaError("Fixed-polygon extent and density values must be nonnegative")
    if not fixed["origin_membership_eligible"].isin([True, False]).all():
        raise SourceSchemaError("origin_membership_eligible must be boolean")
    if not fixed["origin_membership_validated"].eq(True).all():
        raise SourceSchemaError("Every origin-membership decision must be independently validated")
    if fixed["origin_membership_basis"].isna().any():
        raise SourceSchemaError("Every fixed polygon requires an origin-membership basis")
    if fixed["origin_membership_basis"].eq("year_of_construction_only").any():
        raise SourceSchemaError("Construction year does not establish Cities-class membership")
    for column in ("density_metric_id", "density_lineage_status"):
        if fixed.groupby(interval_key)[column].nunique(dropna=False).gt(1).any():
            raise SourceSchemaError(f"Each country interval must use one {column}")
    metric_registry = density_metric_registry().set_index("metric_id")
    used_metric_ids = set(fixed["density_metric_id"])
    unknown_metrics = used_metric_ids - set(metric_registry.index)
    if unknown_metrics:
        raise SourceSchemaError(f"Unregistered reconciliation density metric: {sorted(unknown_metrics)}")
    invalid_denominators = [
        metric_id for metric_id in used_metric_ids
        if metric_registry.loc[metric_id, "denominator_source"] != "GH_BUS_TOT"
    ]
    if invalid_denominators:
        raise SourceSchemaError(
            "Extent-density reconciliation requires population per GH_BUS_TOT: "
            f"{', '.join(sorted(invalid_denominators))}"
        )
    for metric_id in used_metric_ids:
        supplied = set(fixed.loc[fixed["density_metric_id"].eq(metric_id), "density_lineage_status"])
        expected = metric_registry.loc[metric_id, "lineage_status"]
        if supplied != {expected}:
            raise SourceSchemaError(f"Density lineage does not match registry for {metric_id}")

    expected_fixed_intervals = set(map(tuple, fixed[interval_key].drop_duplicates().to_numpy()))
    fixed = fixed.loc[fixed["origin_membership_eligible"]].copy()
    if fixed.empty:
        raise SourceSchemaError("No origin-eligible fixed polygons remain")
    retained_intervals = set(map(tuple, fixed[interval_key].drop_duplicates().to_numpy()))
    if retained_intervals != expected_fixed_intervals:
        raise SourceSchemaError("At least one country interval has no origin-eligible fixed polygon")

    surface_start = fixed["built_surface_start"]
    surface_end = fixed["built_surface_end"]
    density_start = fixed["density_start"]
    density_end = fixed["density_end"]
    fixed["fixed_population_start"] = surface_start * density_start
    fixed["fixed_population_end"] = surface_end * density_end
    fixed["horizontal_extent_change"] = (
        0.5 * (density_start + density_end) * (surface_end - surface_start)
    )
    fixed["in_place_densification_change"] = (
        0.5 * (surface_start + surface_end) * (density_end - density_start)
    )
    aggregation = {
        "fixed_population_start": "sum", "fixed_population_end": "sum",
        "horizontal_extent_change": "sum", "in_place_densification_change": "sum",
        "polygon_id": "nunique", "density_metric_id": "first",
        "density_lineage_status": "first",
    }
    result = fixed.groupby(interval_key, as_index=False).agg(aggregation).rename(
        columns={"polygon_id": "polygon_count"}
    )
    result["fixed_polygon_population_change"] = (
        result["fixed_population_end"] - result["fixed_population_start"]
    )
    result["fixed_identity_error"] = result["fixed_polygon_population_change"] - (
        result["horizontal_extent_change"] + result["in_place_densification_change"]
    )
    if not np.allclose(result["fixed_identity_error"], 0, atol=1e-8, rtol=1e-10):
        raise SourceSchemaError("Extent-density decomposition does not close")

    flag_columns = [
        "city_population_start", "city_population_end", "category_presence_transition",
        "large_share_change_flag", "large_share_change_threshold",
        "composition_discontinuity_flag", "interval_observation_status",
    ]
    result = result.merge(
        national_intervals[interval_key + flag_columns], on=interval_key, validate="one_to_one"
    ).merge(constant_membership_intervals, on=interval_key, validate="one_to_one")
    for column in (
        "city_population_start", "city_population_end", "f21_population_start",
        "f21_population_end",
    ):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    check_columns = [
        "city_population_start", "city_population_end", "f21_population_start",
        "f21_population_end",
    ]
    if result[check_columns].isna().any().any() or not np.isfinite(
        result[check_columns].to_numpy(dtype=float)
    ).all():
        raise SourceSchemaError("F01 and F21 reconciliation populations must be finite")
    if (result[check_columns] < 0).any().any():
        raise SourceSchemaError("F01 and F21 reconciliation populations must be nonnegative")
    if not result["constant_membership_validated"].isin([True, False]).all():
        raise SourceSchemaError("constant_membership_validated must be boolean")
    if result.loc[result["constant_membership_validated"], "membership_semantics_source"].isna().any():
        raise SourceSchemaError("Validated membership requires a methodology source")

    result["f01_cities_population_change"] = (
        result["city_population_end"] - result["city_population_start"]
    )
    result["f21_constant_membership_change"] = (
        result["f21_population_end"] - result["f21_population_start"]
    )
    result["fixed_vs_f21_change_difference"] = (
        result["fixed_polygon_population_change"] - result["f21_constant_membership_change"]
    )
    scale = np.maximum(
        np.maximum(result["f21_population_start"], result["f21_population_end"]), 1.0
    )
    allowed_error = absolute_tolerance + relative_tolerance * scale
    result["f21_crosscheck_within_tolerance"] = (
        result["fixed_vs_f21_change_difference"].abs() <= allowed_error
    )
    result["f01_composition_residual"] = (
        result["f01_cities_population_change"] - result["fixed_polygon_population_change"]
    )
    identified = (
        result["constant_membership_validated"] & result["f21_crosscheck_within_tolerance"]
    )
    result["residual_interpretation"] = np.where(
        identified, "net_reclassification", "unidentified_composition_residual"
    )
    result["net_reclassification_change"] = result["f01_composition_residual"].where(identified)
    result["f01_reconciliation_error"] = result["f01_cities_population_change"] - (
        result["horizontal_extent_change"] + result["in_place_densification_change"]
        + result["f01_composition_residual"]
    )
    result["relative_tolerance"] = relative_tolerance
    result["absolute_tolerance"] = absolute_tolerance
    result["admissible_role"] = np.where(
        result["density_lineage_status"].eq("clean"),
        "accounting_decomposition", "construction_sensitive_sensitivity_only",
    )
    if not np.allclose(result["f01_reconciliation_error"], 0, atol=1e-8, rtol=1e-10):
        raise SourceSchemaError("F01 reconciliation does not close")
    return result.sort_values(interval_key).reset_index(drop=True)


def national_envelope_intervals(
    panel: pd.DataFrame,
    *,
    interval_years: int = 5,
    origin_step_years: int = 5,
    origin_anchor_year: int = 1950,
    estimate_end_year: int = 2025,
    large_share_change_threshold: float = 0.25,
) -> pd.DataFrame:
    """Decompose national population change and settlement-class reallocation."""
    required = {
        "country_code", "year", "category", "population", "observation_type",
        "revision_semantics", "subregion_name", "region_name",
    }
    require_columns(panel, required, source_name="national settlement panel")
    reject_duplicate_keys(
        panel, ["country_code", "year", "category"], source_name="national settlement panel"
    )
    if interval_years <= 0 or origin_step_years <= 0:
        raise SourceSchemaError("National-envelope interval and origin step must be positive")
    if not 0 < large_share_change_threshold <= 1:
        raise SourceSchemaError("Large-share-change threshold must be in (0, 1]")
    unknown = set(panel["category"].dropna()) - set(DEGURBA_CATEGORIES)
    if unknown:
        raise SourceSchemaError(f"Unknown national settlement categories: {sorted(unknown)}")
    population = pd.to_numeric(panel["population"], errors="coerce")
    if population.isna().any() or not np.isfinite(population).all() or (population < 0).any():
        raise SourceSchemaError("National settlement population must be finite and nonnegative")
    source = panel.assign(population=population)
    metadata = source[
        ["country_code", "year", "subregion_name", "region_name", "observation_type",
         "revision_semantics"]
    ].drop_duplicates()
    reject_duplicate_keys(metadata, ["country_code", "year"], source_name="national metadata")
    wide = source.pivot(
        index=["country_code", "year"], columns="category", values="population"
    ).reset_index()
    if any(category not in wide for category in DEGURBA_CATEGORIES):
        raise SourceSchemaError("National settlement panel lacks a required category")
    if wide[list(DEGURBA_CATEGORIES)].isna().any().any():
        raise SourceSchemaError("National settlement panel has incomplete country-year composition")
    start = wide.rename(columns={
        category: f"{category}_population_start" for category in DEGURBA_CATEGORIES
    })
    end = wide.rename(columns={
        "year": "period_end",
        **{category: f"{category}_population_end" for category in DEGURBA_CATEGORIES},
    })
    start["period_end"] = start["year"] + interval_years
    result = start.merge(end, on=["country_code", "period_end"], validate="one_to_one")
    result = result.rename(columns={"year": "period_start"})
    result = result.loc[
        result["period_end"].le(estimate_end_year)
        & result["period_start"].sub(origin_anchor_year).mod(origin_step_years).eq(0)
    ].copy()
    result = result.merge(
        metadata.rename(columns={"year": "period_start", "observation_type": "start_status"}),
        on=["country_code", "period_start"], validate="many_to_one",
    ).merge(
        metadata[["country_code", "year", "observation_type"]].rename(
            columns={"year": "period_end", "observation_type": "end_status"}
        ),
        on=["country_code", "period_end"], validate="many_to_one",
    )
    start_columns = [f"{category}_population_start" for category in DEGURBA_CATEGORIES]
    end_columns = [f"{category}_population_end" for category in DEGURBA_CATEGORIES]
    result["total_population_start"] = result[start_columns].sum(axis=1)
    result["total_population_end"] = result[end_columns].sum(axis=1)
    if (result[["total_population_start", "total_population_end"]] <= 0).any().any():
        raise SourceSchemaError("National total population must be positive at both endpoints")
    result["total_population_change"] = (
        result["total_population_end"] - result["total_population_start"]
    )
    result["total_annualized_log_growth"] = (
        np.log(result["total_population_end"]) - np.log(result["total_population_start"])
    ) / interval_years
    for category in DEGURBA_CATEGORIES:
        start_population = result[f"{category}_population_start"]
        end_population = result[f"{category}_population_end"]
        start_share = start_population / result["total_population_start"]
        end_share = end_population / result["total_population_end"]
        result[f"{category}_population_change"] = end_population - start_population
        result[f"{category}_share_start"] = start_share
        result[f"{category}_share_end"] = end_share
        result[f"{category}_share_change"] = end_share - start_share
        result[f"{category}_reallocation_change"] = (
            end_population - start_population - start_share * result["total_population_change"]
        )
        positive = (start_population > 0) & (end_population > 0)
        result[f"{category}_log_growth_available"] = positive
        log_growth = pd.Series(np.nan, index=result.index, dtype=float)
        log_growth.loc[positive] = (
            np.log(end_population.loc[positive]) - np.log(start_population.loc[positive])
        ) / interval_years
        result[f"{category}_annualized_log_growth"] = log_growth
    share_change_columns = [f"{category}_share_change" for category in DEGURBA_CATEGORIES]
    reallocation_columns = [f"{category}_reallocation_change" for category in DEGURBA_CATEGORIES]
    if not np.allclose(result[share_change_columns].sum(axis=1), 0, atol=1e-10):
        raise SourceSchemaError("National settlement share changes do not sum to zero")
    if not np.allclose(result[reallocation_columns].sum(axis=1), 0, atol=1e-6):
        raise SourceSchemaError("National settlement reallocations do not sum to zero")
    presence_transitions = []
    for category in DEGURBA_CATEGORIES:
        start_positive = result[f"{category}_population_start"].gt(0)
        end_positive = result[f"{category}_population_end"].gt(0)
        presence_transitions.append(start_positive.ne(end_positive))
    result["category_presence_transition"] = pd.concat(presence_transitions, axis=1).any(axis=1)
    result["large_share_change_threshold"] = large_share_change_threshold
    result["large_share_change_flag"] = result[share_change_columns].abs().max(axis=1).ge(
        large_share_change_threshold
    )
    result["composition_discontinuity_flag"] = (
        result["category_presence_transition"] | result["large_share_change_flag"]
    )
    result["interval_observation_status"] = np.where(
        result["start_status"].eq("estimate") & result["end_status"].eq("estimate"),
        "retrospective_revised_estimate", "contains_projection",
    )
    return result.sort_values(["country_code", "period_start"]).reset_index(drop=True)


def national_envelope_feature_registry() -> pd.DataFrame:
    """Separate explanatory outcomes from features available at a forecast origin."""
    return pd.DataFrame(
        [
            {
                "feature_family": "realized_envelope_growth",
                "timing": "period_start_to_period_end",
                "retrospective_role": "Module A outcome",
                "future_usable_at_origin": False,
            },
            {
                "feature_family": "lagged_envelope_growth",
                "timing": "period_start_minus_interval_to_period_start",
                "retrospective_role": "forecast covariate",
                "future_usable_at_origin": True,
            },
            {
                "feature_family": "origin_settlement_shares",
                "timing": "period_start",
                "retrospective_role": "forecast covariate",
                "future_usable_at_origin": True,
            },
            {
                "feature_family": "realized_share_change",
                "timing": "period_start_to_period_end",
                "retrospective_role": "Module A outcome",
                "future_usable_at_origin": False,
            },
        ]
    )


def national_envelope_forecast_features(intervals: pd.DataFrame) -> pd.DataFrame:
    """Build origin-available features without copying realized outcome-period values."""
    required = {
        "country_code", "period_start", "period_end", "total_annualized_log_growth",
        *{f"{category}_share_start" for category in DEGURBA_CATEGORIES},
        *{f"{category}_share_change" for category in DEGURBA_CATEGORIES},
    }
    require_columns(intervals, required, source_name="national envelope intervals")
    reject_duplicate_keys(
        intervals, ["country_code", "period_start"], source_name="national envelope intervals"
    )
    lag_columns = [
        "country_code", "period_end", "total_annualized_log_growth",
        *[f"{category}_share_change" for category in DEGURBA_CATEGORIES],
    ]
    lagged = intervals[lag_columns].rename(
        columns={
            "period_end": "period_start",
            "total_annualized_log_growth": "lagged_total_annualized_log_growth",
            **{
                f"{category}_share_change": f"lagged_{category}_share_change"
                for category in DEGURBA_CATEGORIES
            },
        }
    )
    origin_columns = [
        "country_code", "period_start", "period_end",
        *[f"{category}_share_start" for category in DEGURBA_CATEGORIES],
    ]
    result = intervals[origin_columns].merge(
        lagged, on=["country_code", "period_start"], how="left", validate="one_to_one"
    )
    result["lagged_envelope_available"] = result["lagged_total_annualized_log_growth"].notna()
    result["uses_outcome_period_value"] = False
    return result.sort_values(["country_code", "period_start"]).reset_index(drop=True)


def national_envelope_summaries(intervals: pd.DataFrame) -> pd.DataFrame:
    """Summarize direct national envelopes with country-equal and population weights."""
    metrics = [
        "total_annualized_log_growth",
        *[f"{category}_share_change" for category in DEGURBA_CATEGORIES],
    ]
    required = {
        "country_code", "period_start", "period_end", "region_name",
        "total_population_start", "composition_discontinuity_flag", *metrics,
    }
    require_columns(intervals, required, source_name="national envelope intervals")
    records = []
    group_designs = [
        ("global", pd.Series("Global", index=intervals.index)),
        ("region", intervals["region_name"]),
    ]
    for sample_name, sample in (
        ("all", intervals),
        ("stable_composition", intervals.loc[~intervals["composition_discontinuity_flag"]]),
    ):
        for aggregation_level, labels in group_designs:
            working = sample.assign(_group=labels.reindex(sample.index))
            for (period_start, period_end, group_name), group in working.groupby(
                ["period_start", "period_end", "_group"], sort=True
            ):
                weights = group["total_population_start"].to_numpy(dtype=float)
                for weighting in ("country_equal", "population_start"):
                    row: dict[str, int | float | str] = {
                        "sample": sample_name,
                        "aggregation_level": aggregation_level,
                        "group_name": str(group_name),
                        "period_start": int(period_start),
                        "period_end": int(period_end),
                        "weighting": weighting,
                        "country_count": group["country_code"].nunique(),
                    }
                    for metric in metrics:
                        values = group[metric].to_numpy(dtype=float)
                        row[metric] = (
                            float(values.mean()) if weighting == "country_equal"
                            else float(np.average(values, weights=weights))
                        )
                    records.append(row)
    return pd.DataFrame(records).sort_values(
        ["sample", "aggregation_level", "group_name", "period_start", "weighting"]
    ).reset_index(drop=True)

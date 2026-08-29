"""Leakage-resistant forecast evaluation primitives."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns
from urban_growth.outcomes import add_size_bins


@dataclass(frozen=True)
class ForecastMetrics:
    n: int
    mae: float
    rmse: float
    median_absolute_error: float
    bias: float
    directional_accuracy: float


def rolling_origin_splits(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    start_column: str = "period_start",
    end_column: str = "period_end",
) -> Iterator[tuple[int, pd.Index, pd.Index]]:
    """Yield train/test indices where training outcomes predate each origin."""
    for origin in origins:
        train = panel.index[panel[end_column] <= origin]
        test = panel.index[panel[start_column] == origin]
        if len(train) and len(test):
            yield origin, train, test


def attach_national_city_category_baseline(
    intervals: pd.DataFrame,
    national_panel: pd.DataFrame,
    *,
    lookback_years: int = 5,
) -> pd.DataFrame:
    """Attach pre-origin national Cities-category growth from WUP F01.

    This is a revised-history demographic comparator. Both endpoints precede
    or equal the city forecast origin; no future national value is used. The
    primary variant subtracts the focal F21 city from both F01 national endpoints.
    The inclusive variant is retained only to measure mechanical self-inclusion.
    """
    require_columns(
        intervals,
        {
            "country_code", "period_start", "population_lag", "population_start",
        },
        source_name="forecast intervals",
    )
    require_columns(
        national_panel,
        {
            "country_code", "year", "national_city_category_population",
            "revision_semantics", "subregion_id", "subregion_name", "region_id",
            "region_name",
        },
        source_name="national city-category panel",
    )
    reject_duplicate_keys(
        national_panel, ["country_code", "year"], source_name="national city-category panel"
    )
    if national_panel["revision_semantics"].ne("WUP_2025_revised_history").any():
        raise SourceSchemaError("National baseline revision semantics are not declared correctly")
    if lookback_years <= 0:
        raise SourceSchemaError("National baseline lookback must be positive")
    national = national_panel.set_index(["country_code", "year"])
    hierarchy = national_panel[
        [
            "country_code", "subregion_id", "subregion_name", "region_id", "region_name"
        ]
    ].drop_duplicates()
    reject_duplicate_keys(hierarchy, ["country_code"], source_name="WUP F01 hierarchy")
    keys = intervals[["country_code", "period_start"]].drop_duplicates().copy()
    keys = keys.merge(hierarchy, on="country_code", how="left", validate="many_to_one")
    if keys[["subregion_id", "region_id"]].isna().any().any():
        raise SourceSchemaError("National baseline lacks a regional mapping")
    origin_index = pd.MultiIndex.from_frame(
        keys.rename(columns={"period_start": "year"})[["country_code", "year"]]
    )
    lag_keys = keys.assign(year=keys["period_start"] - lookback_years)
    lag_index = pd.MultiIndex.from_frame(lag_keys[["country_code", "year"]])
    origin_population = national["national_city_category_population"].reindex(
        origin_index
    ).to_numpy()
    lag_population = national["national_city_category_population"].reindex(
        lag_index
    ).to_numpy()
    if pd.isna(origin_population).any() or pd.isna(lag_population).any():
        raise SourceSchemaError("National city-category baseline lacks a required country-year")
    if (origin_population <= 0).any() or (lag_population <= 0).any():
        raise SourceSchemaError("National city-category baseline requires positive endpoints")
    keys["national_city_category_recent_growth"] = (
        np.log(origin_population) - np.log(lag_population)
    ) / lookback_years
    result = intervals.merge(
        keys,
        on=["country_code", "period_start"],
        how="left",
        validate="many_to_one",
    )
    result["national_city_category_recent_growth_inclusive"] = result[
        "national_city_category_recent_growth"
    ]
    national_lookup = national_panel.set_index(["country_code", "year"])[
        "national_city_category_population"
    ]
    origin_lookup = pd.MultiIndex.from_frame(
        result.rename(columns={"period_start": "year"})[["country_code", "year"]]
    )
    lag_result = result.assign(year=result["period_start"] - lookback_years)
    lag_lookup = pd.MultiIndex.from_frame(lag_result[["country_code", "year"]])
    national_origin = national_lookup.reindex(origin_lookup).to_numpy()
    national_lag = national_lookup.reindex(lag_lookup).to_numpy()
    residual_origin = national_origin - result["population_start"].to_numpy()
    residual_lag = national_lag - result["population_lag"].to_numpy()
    if (residual_origin <= 0).any() or (residual_lag <= 0).any():
        raise SourceSchemaError(
            "Focal city is not a strictly smaller positive component of national Cities totals"
        )
    result["national_city_category_recent_growth_leave_city_out"] = (
        np.log(residual_origin) - np.log(residual_lag)
    ) / lookback_years
    result["national_focal_share_origin"] = (
        result["population_start"].to_numpy() / national_origin
    )
    result["national_focal_share_lag"] = (
        result["population_lag"].to_numpy() / national_lag
    )
    result["national_baseline_revision_semantics"] = "WUP_2025_revised_history"
    result["national_baseline_uses_future_value"] = False
    result["national_baseline_focal_city_excluded"] = True
    result["national_focal_component_membership_assumed"] = True
    result["national_focal_subtraction_semantics"] = (
        "F21_city_subtracted_from_F01_Cities_same_revision"
    )
    return result


def build_forecast_intervals(
    city_year_panel: pd.DataFrame,
    origins: list[int],
    *,
    lookback_years: int = 5,
    horizon_years: int = 5,
    outcome_gap_years: int = 0,
    allowed_outcome_types: set[str] | None = None,
) -> pd.DataFrame:
    """Create lagged predictors and later outcomes from exact source years.

    The default permits estimate outcomes only. Callers must explicitly opt into
    evaluating publisher projections as outcomes.
    """
    required = {
        "city_id", "year", "population", "observation_type", "ISO3_Code",
        "City_Name", "built_up_share_of_land", "population_density_per_km2",
    }
    require_columns(city_year_panel, required, source_name="WUP city-year forecast source")
    reject_duplicate_keys(city_year_panel, ["city_id", "year"], source_name="WUP forecast")
    if lookback_years <= 0 or horizon_years <= 0 or outcome_gap_years < 0:
        raise SourceSchemaError("Forecast lookback/horizon must be positive and gap non-negative")
    if not origins or any(not isinstance(year, int) for year in origins):
        raise SourceSchemaError("Forecast origins must be a non-empty list of integer years")
    allowed = {"estimate"} if allowed_outcome_types is None else allowed_outcome_types
    if not allowed:
        raise SourceSchemaError("At least one outcome observation type must be allowed")

    ranked_source = city_year_panel.copy()
    rank_groups = ranked_source.groupby(["ISO3_Code", "year"])["population"]
    ranked_source["_country_rank"] = rank_groups.rank(method="average", ascending=False)
    ranked_source["_country_city_count"] = rank_groups.transform("count")
    ranked_source["_country_rank_percentile"] = (
        (ranked_source["_country_rank"] - 0.5) / ranked_source["_country_city_count"]
    )
    source = ranked_source.set_index(["city_id", "year"])
    frames: list[pd.DataFrame] = []
    for origin in sorted(set(origins)):
        lag_year = origin - lookback_years
        outcome_start_year = origin + outcome_gap_years
        future_year = outcome_start_year + horizon_years
        available_cities = source.index.get_level_values("city_id").unique()
        keys = pd.MultiIndex.from_product(
            [available_cities, sorted({lag_year, origin, outcome_start_year, future_year})],
            names=["city_id", "year"],
        )
        complete = source.reindex(keys).reset_index()
        wide = complete.pivot(index="city_id", columns="year")
        has_population = wide["population"].notna().all(axis=1)
        if not has_population.any():
            continue
        wide = wide.loc[has_population]
        outcome_start_type = wide[("observation_type", outcome_start_year)]
        outcome_end_type = wide[("observation_type", future_year)]
        allowed_outcome = outcome_end_type.isin(allowed)
        if outcome_gap_years:
            allowed_outcome &= outcome_start_type.isin(allowed)
        wide = wide.loc[allowed_outcome]
        if wide.empty:
            continue
        result = pd.DataFrame(index=wide.index)
        result["country_code"] = wide[("ISO3_Code", origin)]
        result["city_name"] = wide[("City_Name", origin)]
        result["period_start"] = origin
        result["period_end"] = future_year
        result["outcome_start_year"] = outcome_start_year
        result["outcome_gap_years"] = outcome_gap_years
        result["population_lag"] = wide[("population", lag_year)]
        result["population_start"] = wide[("population", origin)]
        result["population_end"] = wide[("population", future_year)]
        result["country_rank_lag"] = wide[("_country_rank", lag_year)]
        result["country_rank_origin"] = wide[("_country_rank", origin)]
        result["country_city_count_lag"] = wide[("_country_city_count", lag_year)]
        result["country_city_count_origin"] = wide[("_country_city_count", origin)]
        result["country_rank_percentile_lag"] = wide[
            ("_country_rank_percentile", lag_year)
        ]
        result["country_rank_percentile_origin"] = wide[
            ("_country_rank_percentile", origin)
        ]
        result["recent_growth"] = (
            np.log(result["population_start"]) - np.log(result["population_lag"])
        ) / lookback_years
        result["future_growth"] = (
            np.log(result["population_end"])
            - np.log(wide[("population", outcome_start_year)])
        ) / horizon_years
        result["built_up_share_at_origin"] = wide[("built_up_share_of_land", origin)]
        result["population_density_at_origin"] = wide[
            ("population_density_per_km2", origin)
        ]
        result["lag_observation_type"] = wide[("observation_type", lag_year)]
        result["origin_observation_type"] = wide[("observation_type", origin)]
        result["outcome_start_observation_type"] = outcome_start_type.loc[wide.index]
        result["outcome_observation_type"] = outcome_end_type.loc[wide.index]
        result["coverage_selection"] = "complete_lag_origin_outcome_start_end"
        frames.append(result.reset_index())
    if not frames:
        raise SourceSchemaError("No complete forecast intervals satisfy the declared rules")
    panel = pd.concat(frames, ignore_index=True)
    reject_duplicate_keys(
        panel, ["city_id", "period_start", "period_end"], source_name="forecast intervals"
    )
    return panel.sort_values(["period_start", "city_id"]).reset_index(drop=True)


def build_ghsl_fixed_forecast_intervals(
    fixed_panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_gap_years: int = 0,
    reconciliation: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build intervals only from GHSL statistics inside fixed 2025 polygons.

    This is a stable-polygon sensitivity analysis, not a vintage-correct forecast:
    the historical statistics use a boundary defined using 2025 settlement extent.
    """
    required = {
        "city_id", "year", "population", "built_up_area_m2",
        "urban_centre_area_km2", "boundary_mode", "boundary_product",
        "GC_UCN_MAI_2025", "GC_CNT_GAD_2025",
    }
    require_columns(fixed_panel, required, source_name="GHSL fixed-boundary forecast source")
    if fixed_panel["boundary_mode"].ne("fixed").any():
        raise SourceSchemaError("GHSL forecast sensitivity requires fixed boundaries only")
    expected_product = "ucdb_fixed_2025_boundary"
    if fixed_panel["boundary_product"].ne(expected_product).any():
        raise SourceSchemaError(f"GHSL forecast sensitivity requires {expected_product}")
    reconciled = reconciliation is not None
    if reconciliation is not None:
        reconciliation_required = {
            "city_id", "population_difference", "built_up_area_difference_m2",
            "urban_centre_area_difference_km2",
        }
        require_columns(
            reconciliation,
            reconciliation_required,
            source_name="GHSL 2025 cross-stream reconciliation",
        )
        reject_duplicate_keys(
            reconciliation, ["city_id"], source_name="GHSL 2025 cross-stream reconciliation"
        )
        fixed_ids = set(fixed_panel["city_id"].unique())
        reconciliation_ids = set(reconciliation["city_id"])
        if fixed_ids != reconciliation_ids:
            raise SourceSchemaError("GHSL reconciliation does not cover the fixed entity universe")
        if reconciliation["population_difference"].abs().gt(0.500001).any():
            raise SourceSchemaError("GHSL reconciliation exceeds population rounding tolerance")
        exact_columns = [
            "built_up_area_difference_m2", "urban_centre_area_difference_km2"
        ]
        if reconciliation[exact_columns].ne(0).any().any():
            raise SourceSchemaError("GHSL reconciliation has nonzero area differences")
    source = fixed_panel.copy()
    source["ISO3_Code"] = source["GC_CNT_GAD_2025"]
    source["City_Name"] = source["GC_UCN_MAI_2025"]
    source["observation_type"] = "retrospective_model_epoch"
    source["built_up_share_of_land"] = source["built_up_area_m2"] / (
        source["urban_centre_area_km2"] * 1_000_000
    )
    source["population_density_per_km2"] = (
        source["population"] / source["urban_centre_area_km2"]
    )
    result = build_forecast_intervals(
        source,
        origins,
        outcome_gap_years=outcome_gap_years,
        allowed_outcome_types={"retrospective_model_epoch"},
    )
    result["boundary_mode"] = "fixed"
    result["boundary_product"] = expected_product
    result["boundary_reference_year"] = 2025
    result["boundary_temporally_fixed"] = True
    result["boundary_history_uses_future_reference"] = True
    result["cross_stream_reconciled"] = reconciled
    return result


def build_ghsl_dynamic_forecast_intervals(
    dynamic_panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_gap_years: int = 0,
) -> pd.DataFrame:
    """Build intervals from quality-controlled GHSL multi-temporal polygons."""
    required = {
        "city_id", "year", "population", "built_up_area_m2",
        "urban_centre_area_km2", "boundary_mode", "boundary_product",
        "GC_UCN_MAI_2025", "GC_CNT_GAD_2025", "quality_controlled_2025",
    }
    require_columns(dynamic_panel, required, source_name="GHSL dynamic-boundary source")
    expected_product = "ucdb_multitemporal_boundaries"
    if dynamic_panel["boundary_mode"].ne("dynamic").any():
        raise SourceSchemaError("GHSL dynamic sensitivity requires dynamic boundaries only")
    if dynamic_panel["boundary_product"].ne(expected_product).any():
        raise SourceSchemaError(f"GHSL dynamic sensitivity requires {expected_product}")
    source = dynamic_panel.loc[dynamic_panel["quality_controlled_2025"]].copy()
    if source.empty:
        raise SourceSchemaError("GHSL dynamic sensitivity has no quality-controlled entities")
    source["ISO3_Code"] = source["GC_CNT_GAD_2025"]
    source["City_Name"] = source["GC_UCN_MAI_2025"]
    source["observation_type"] = "retrospective_model_epoch"
    source["built_up_share_of_land"] = source["built_up_area_m2"] / (
        source["urban_centre_area_km2"] * 1_000_000
    )
    source["population_density_per_km2"] = (
        source["population"] / source["urban_centre_area_km2"]
    )
    result = build_forecast_intervals(
        source,
        origins,
        outcome_gap_years=outcome_gap_years,
        allowed_outcome_types={"retrospective_model_epoch"},
    )
    result["boundary_mode"] = "dynamic"
    result["boundary_product"] = expected_product
    result["boundary_reference_year"] = pd.NA
    result["boundary_temporally_fixed"] = False
    result["boundary_history_uses_future_reference"] = False
    result["cross_stream_reconciled"] = False
    return result


def matched_boundary_forecast_panels(
    fixed: pd.DataFrame,
    dynamic: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restrict fixed and dynamic panels to identical city-origin forecast rows."""
    keys = ["city_id", "period_start", "period_end"]
    required = {*keys, "country_code", "boundary_mode"}
    require_columns(fixed, required, source_name="fixed boundary forecast panel")
    require_columns(dynamic, required, source_name="dynamic boundary forecast panel")
    reject_duplicate_keys(fixed, keys, source_name="fixed boundary forecast panel")
    reject_duplicate_keys(dynamic, keys, source_name="dynamic boundary forecast panel")
    if fixed["boundary_mode"].ne("fixed").any() or dynamic["boundary_mode"].ne(
        "dynamic"
    ).any():
        raise SourceSchemaError("Boundary panel modes are not fixed versus dynamic")
    matched = fixed[keys + ["country_code"]].merge(
        dynamic[keys + ["country_code"]],
        on=keys,
        how="inner",
        suffixes=("_fixed", "_dynamic"),
        validate="one_to_one",
    )
    if matched.empty:
        raise SourceSchemaError("Fixed and dynamic panels have no matched forecast rows")
    if matched["country_code_fixed"].ne(matched["country_code_dynamic"]).any():
        raise SourceSchemaError("Fixed and dynamic matched rows disagree on country")
    matched_keys = matched[keys]
    fixed_matched = fixed.merge(matched_keys, on=keys, validate="one_to_one")
    dynamic_matched = dynamic.merge(matched_keys, on=keys, validate="one_to_one")
    sort = ["period_start", "city_id"]
    return (
        fixed_matched.sort_values(sort).reset_index(drop=True),
        dynamic_matched.sort_values(sort).reset_index(drop=True),
    )


def score_forecast(actual: pd.Series, predicted: pd.Series) -> ForecastMetrics:
    """Score matched observations after dropping non-finite pairs."""
    pairs = pd.concat({"actual": actual, "predicted": predicted}, axis=1).dropna()
    finite = np.isfinite(pairs).all(axis=1)
    pairs = pairs.loc[finite]
    if pairs.empty:
        raise ValueError("No finite matched observations to score")
    error = pairs["predicted"] - pairs["actual"]
    return ForecastMetrics(
        n=len(pairs),
        mae=float(error.abs().mean()),
        rmse=float(np.sqrt((error**2).mean())),
        median_absolute_error=float(error.abs().median()),
        bias=float(error.mean()),
        directional_accuracy=float(
            (np.sign(pairs["predicted"]) == np.sign(pairs["actual"])).mean()
        ),
    )


def baseline_predictions(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    outcome_column: str = "future_growth",
    persistence_column: str = "recent_growth",
) -> pd.DataFrame:
    """Predict simple baselines using training outcomes and test-origin information only."""
    required = {"country_code", outcome_column}
    require_columns(train, required, source_name="forecast training set")
    require_columns(
        test, {"country_code", persistence_column}, source_name="forecast test set"
    )
    valid_train = train.loc[np.isfinite(train[outcome_column])].copy()
    if valid_train.empty:
        raise SourceSchemaError("No finite training outcomes for forecast baselines")
    global_mean = float(valid_train[outcome_column].mean())
    country_means = valid_train.groupby("country_code")[outcome_column].mean()
    predictions = pd.DataFrame(index=test.index)
    predictions["zero_growth"] = 0.0
    predictions["global_mean"] = global_mean
    for group_column in ["region_id", "subregion_id"]:
        if group_column in train.columns and group_column in test.columns:
            label = group_column.removesuffix("_id")
            group_means = valid_train.groupby(group_column)[outcome_column].mean()
            predictions[f"{label}_mean"] = test[group_column].map(group_means).fillna(
                global_mean
            )
    predictions["country_mean"] = test["country_code"].map(country_means).fillna(global_mean)
    national_column = "national_city_category_recent_growth"
    if national_column in test.columns:
        predictions["national_city_category_persistence_inclusive"] = pd.to_numeric(
            test[national_column], errors="coerce"
        )
    national_loo_column = "national_city_category_recent_growth_leave_city_out"
    if national_loo_column in test.columns:
        predictions["national_city_category_persistence_leave_city_out"] = pd.to_numeric(
            test[national_loo_column], errors="coerce"
        )
    if "city_id" in train.columns and "city_id" in test.columns:
        country_totals = valid_train.groupby("country_code")[outcome_column].agg(["sum", "count"])
        city_totals = valid_train.groupby(["country_code", "city_id"])[outcome_column].agg(
            ["sum", "count"]
        )
        test_keys = pd.MultiIndex.from_frame(test[["country_code", "city_id"]])
        focal_sum = city_totals["sum"].reindex(test_keys, fill_value=0).to_numpy()
        focal_count = city_totals["count"].reindex(test_keys, fill_value=0).to_numpy()
        country_sum = test["country_code"].map(country_totals["sum"]).to_numpy()
        country_count = test["country_code"].map(country_totals["count"]).to_numpy()
        global_focal = valid_train.groupby("city_id")[outcome_column].agg(["sum", "count"])
        global_focal_sum = test["city_id"].map(global_focal["sum"]).fillna(0).to_numpy()
        global_focal_count = test["city_id"].map(global_focal["count"]).fillna(0).to_numpy()
        global_without_count = len(valid_train) - global_focal_count
        global_without = np.divide(
            valid_train[outcome_column].sum() - global_focal_sum,
            global_without_count,
            out=np.full(len(test), global_mean, dtype=float),
            where=global_without_count > 0,
        )
        if "region_id" in train.columns and "region_id" in test.columns:
            predictions["global_mean_leave_city_out"] = global_without
        for group_column in ["region_id", "subregion_id"]:
            if group_column not in train.columns or group_column not in test.columns:
                continue
            label = group_column.removesuffix("_id")
            group_totals = valid_train.groupby(group_column)[outcome_column].agg(
                ["sum", "count"]
            )
            group_city_totals = valid_train.groupby(
                [group_column, "city_id"]
            )[outcome_column].agg(["sum", "count"])
            group_test_keys = pd.MultiIndex.from_frame(test[[group_column, "city_id"]])
            group_focal_sum = group_city_totals["sum"].reindex(
                group_test_keys, fill_value=0
            ).to_numpy()
            group_focal_count = group_city_totals["count"].reindex(
                group_test_keys, fill_value=0
            ).to_numpy()
            group_sum = test[group_column].map(group_totals["sum"]).to_numpy()
            group_count = test[group_column].map(group_totals["count"]).to_numpy()
            group_without_count = group_count - group_focal_count
            predictions[f"{label}_mean_leave_city_out"] = np.divide(
                group_sum - group_focal_sum,
                group_without_count,
                out=global_without.copy(),
                where=group_without_count > 0,
            )
        country_without_count = country_count - focal_count
        predictions["country_mean_leave_city_out"] = np.divide(
            country_sum - focal_sum,
            country_without_count,
            out=global_without.copy(),
            where=country_without_count > 0,
        )
    predictions["persistence"] = pd.to_numeric(test[persistence_column], errors="coerce")
    return predictions


def evaluate_rolling_baselines(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Score matched baseline predictions at chronological rolling origins."""
    require_columns(
        panel,
        {"period_start", "period_end", "country_code", outcome_column, "recent_growth"},
        source_name="forecast interval panel",
    )
    rows: list[dict[str, float | int | str]] = []
    for origin, train_index, test_index in rolling_origin_splits(panel, origins):
        train = panel.loc[train_index]
        test = panel.loc[test_index]
        predictions = baseline_predictions(train, test, outcome_column=outcome_column)
        matched = pd.concat(
            {"actual": test[outcome_column], **{c: predictions[c] for c in predictions}}, axis=1
        ).dropna()
        finite = np.isfinite(matched).all(axis=1)
        matched = matched.loc[finite]
        if matched.empty:
            continue
        for model in predictions.columns:
            metrics = score_forecast(matched["actual"], matched[model])
            rows.append(
                {
                    "origin": origin,
                    "model": model,
                    "n": metrics.n,
                    "mae": metrics.mae,
                    "rmse": metrics.rmse,
                    "median_absolute_error": metrics.median_absolute_error,
                    "bias": metrics.bias,
                    "directional_accuracy": metrics.directional_accuracy,
                }
            )
    if not rows:
        raise SourceSchemaError("No rolling-origin baseline evaluations were produced")
    result = pd.DataFrame(rows)
    counts = result.pivot(index="origin", columns="model", values="n")
    if counts.nunique(axis=1).gt(1).any():
        raise SourceSchemaError("Baseline models were not scored on identical observations")
    return result.sort_values(["origin", "model"]).reset_index(drop=True)


def evaluate_rolling_hierarchy_models(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Compare origin and pre-growth frozen hierarchy using country fixed effects."""
    required = {
        "city_id", "country_code", "period_start", "period_end", outcome_column,
        "recent_growth", "population_lag", "population_start",
        "country_rank_percentile_lag", "country_rank_percentile_origin",
    }
    require_columns(panel, required, source_name="hierarchy forecast interval panel")
    specifications = {
        "country_loo_plus_recent_growth": ["recent_growth"],
        "origin_hierarchy": [
            "recent_growth", "log_population_start", "country_rank_percentile_origin",
        ],
        "frozen_hierarchy": [
            "recent_growth", "log_population_lag", "country_rank_percentile_lag",
        ],
    }
    working = panel.copy()
    working["log_population_lag"] = np.log(working["population_lag"])
    working["log_population_start"] = np.log(working["population_start"])
    rows: list[dict[str, float | int | str]] = []
    for origin, train_index, test_index in rolling_origin_splits(working, origins):
        train = working.loc[train_index]
        test = working.loc[test_index]
        baseline = baseline_predictions(train, test, outcome_column=outcome_column)
        for model, features in specifications.items():
            columns = ["country_code", outcome_column, *features]
            fit = train[columns].dropna().copy()
            fit = fit.loc[np.isfinite(fit.select_dtypes(include="number")).all(axis=1)]
            country_means = fit.groupby("country_code")[[outcome_column, *features]].mean()
            group_means = fit.groupby("country_code")[[outcome_column, *features]].transform(
                "mean"
            )
            demeaned = fit[[outcome_column, *features]] - group_means
            x_train = demeaned[features].to_numpy()
            y_train = demeaned[outcome_column].to_numpy()
            beta, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
            global_feature_means = fit[features].mean()
            test_feature_means = pd.DataFrame(
                {
                    feature: test["country_code"]
                    .map(country_means[feature])
                    .fillna(global_feature_means[feature])
                    for feature in features
                },
                index=test.index,
            )
            prediction = baseline["country_mean_leave_city_out"] + (
                test[features] - test_feature_means
            ).to_numpy() @ beta
            metrics = score_forecast(test[outcome_column], pd.Series(prediction, index=test.index))
            rows.append(
                {
                    "origin": origin,
                    "model": model,
                    "n": metrics.n,
                    "mae": metrics.mae,
                    "rmse": metrics.rmse,
                    "median_absolute_error": metrics.median_absolute_error,
                    "bias": metrics.bias,
                    "directional_accuracy": metrics.directional_accuracy,
                }
            )
    if not rows:
        raise SourceSchemaError("No rolling hierarchy evaluations were produced")
    return pd.DataFrame(rows).sort_values(["origin", "model"]).reset_index(drop=True)


def rolling_baseline_errors(
    panel: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Return matched row-level errors for prespecified subgroup analysis."""
    require_columns(
        panel,
        {
            "city_id", "period_start", "period_end", "country_code", "population_start",
            outcome_column, "recent_growth",
        },
        source_name="forecast interval panel",
    )
    frames: list[pd.DataFrame] = []
    for origin, train_index, test_index in rolling_origin_splits(panel, origins):
        train = panel.loc[train_index]
        test = panel.loc[test_index]
        predictions = baseline_predictions(train, test, outcome_column=outcome_column)
        identity_columns = ["city_id", "country_code"]
        if "city_name" in test.columns:
            identity_columns.append("city_name")
        matched = test[
            [*identity_columns, "population_start", outcome_column]
        ].copy()
        matched = matched.rename(columns={outcome_column: "actual"})
        matched = matched.join(predictions)
        matched = matched.dropna()
        matched = matched.loc[np.isfinite(matched.select_dtypes(include="number")).all(axis=1)]
        if matched.empty:
            continue
        matched["origin"] = origin
        matched = add_size_bins(matched, population_column="population_start")
        long = matched.melt(
            id_vars=[
                *identity_columns, "population_start", "size_bin", "origin", "actual"
            ],
            value_vars=list(predictions.columns),
            var_name="model",
            value_name="predicted",
        )
        long["error"] = long["predicted"] - long["actual"]
        long["absolute_error"] = long["error"].abs()
        frames.append(long)
    if not frames:
        raise SourceSchemaError("No rolling-origin row-level errors were produced")
    return pd.concat(frames, ignore_index=True)


def balanced_origin_cohort(panel: pd.DataFrame, origins: list[int]) -> pd.DataFrame:
    """Restrict a forecast panel to cities observed at every declared origin."""
    required = {"city_id", "period_start", "period_end"}
    require_columns(panel, required, source_name="forecast interval panel")
    if not origins or len(set(origins)) != len(origins):
        raise SourceSchemaError("Balanced cohort origins must be unique and non-empty")
    reject_duplicate_keys(
        panel, ["city_id", "period_start", "period_end"], source_name="forecast intervals"
    )
    declared = set(origins)
    subset = panel.loc[panel["period_start"].isin(declared)].copy()
    observed = subset.groupby("city_id")["period_start"].agg(lambda x: set(x))
    eligible = observed.index[observed.eq(declared)]
    result = subset.loc[subset["city_id"].isin(eligible)].copy()
    if result.empty:
        raise SourceSchemaError("No cities have complete intervals at every declared origin")
    result["cohort_selection"] = "balanced_all_declared_origins"
    return result.sort_values(["period_start", "city_id"]).reset_index(drop=True)


def equal_country_forecast_metrics(
    errors: pd.DataFrame,
    *,
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Score models after giving every country equal weight within each group."""
    groups = group_columns or []
    required = {"model", "country_code", "error", "absolute_error", *groups}
    require_columns(errors, required, source_name="row-level forecast errors")
    working = errors.copy()
    working["squared_error"] = working["error"] ** 2
    country_keys = [*groups, "model", "country_code"]
    country = working.groupby(country_keys, observed=True).agg(
        country_mae=("absolute_error", "mean"),
        country_mse=("squared_error", "mean"),
        country_bias=("error", "mean"),
        country_rows=("error", "size"),
    ).reset_index()
    result_keys = [*groups, "model"]
    result = country.groupby(result_keys, observed=True).agg(
        countries=("country_code", "nunique"),
        n_rows=("country_rows", "sum"),
        equal_country_mae=("country_mae", "mean"),
        equal_country_mse=("country_mse", "mean"),
        equal_country_bias=("country_bias", "mean"),
    ).reset_index()
    result["equal_country_rmse"] = np.sqrt(result.pop("equal_country_mse"))
    return result.sort_values(result_keys).reset_index(drop=True)


def equal_origin_forecast_metrics(
    errors: pd.DataFrame,
    *,
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Score models with every forecast origin receiving equal weight."""
    groups = group_columns or []
    required = {"origin", "model", "error", "absolute_error", *groups}
    require_columns(errors, required, source_name="row-level forecast errors")
    working = errors.copy()
    if not np.isfinite(working[["error", "absolute_error"]]).all().all():
        raise SourceSchemaError("Equal-origin metrics require finite errors")
    working["squared_error"] = working["error"] ** 2
    origin_keys = [*groups, "model", "origin"]
    origin = working.groupby(origin_keys, observed=True).agg(
        origin_mae=("absolute_error", "mean"),
        origin_mse=("squared_error", "mean"),
        origin_bias=("error", "mean"),
        origin_rows=("error", "size"),
    ).reset_index()
    result_keys = [*groups, "model"]
    result = origin.groupby(result_keys, observed=True).agg(
        origins=("origin", "nunique"),
        n_rows=("origin_rows", "sum"),
        equal_origin_mae=("origin_mae", "mean"),
        equal_origin_mse=("origin_mse", "mean"),
        equal_origin_bias=("origin_bias", "mean"),
        minimum_origin_rows=("origin_rows", "min"),
        maximum_origin_rows=("origin_rows", "max"),
    ).reset_index()
    result["equal_origin_rmse"] = np.sqrt(result.pop("equal_origin_mse"))
    result["estimand"] = "origins_equal_cities_equal_within_origin"
    return result.sort_values(result_keys).reset_index(drop=True)


def equal_country_origin_forecast_metrics(
    errors: pd.DataFrame,
    *,
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Give countries equal weight within origin, then origins equal weight."""
    groups = group_columns or []
    required = {
        "origin", "model", "country_code", "error", "absolute_error", *groups,
    }
    require_columns(errors, required, source_name="row-level forecast errors")
    working = errors.copy()
    if not np.isfinite(working[["error", "absolute_error"]]).all().all():
        raise SourceSchemaError("Equal-country-origin metrics require finite errors")
    working["squared_error"] = working["error"] ** 2
    country_origin_keys = [*groups, "model", "origin", "country_code"]
    country_origin = working.groupby(country_origin_keys, observed=True).agg(
        country_origin_mae=("absolute_error", "mean"),
        country_origin_mse=("squared_error", "mean"),
        country_origin_bias=("error", "mean"),
        country_origin_rows=("error", "size"),
    ).reset_index()
    origin_keys = [*groups, "model", "origin"]
    origin = country_origin.groupby(origin_keys, observed=True).agg(
        origin_equal_country_mae=("country_origin_mae", "mean"),
        origin_equal_country_mse=("country_origin_mse", "mean"),
        origin_equal_country_bias=("country_origin_bias", "mean"),
        countries=("country_code", "nunique"),
        origin_rows=("country_origin_rows", "sum"),
    ).reset_index()
    result_keys = [*groups, "model"]
    result = origin.groupby(result_keys, observed=True).agg(
        origins=("origin", "nunique"),
        n_rows=("origin_rows", "sum"),
        equal_country_origin_mae=("origin_equal_country_mae", "mean"),
        equal_country_origin_mse=("origin_equal_country_mse", "mean"),
        equal_country_origin_bias=("origin_equal_country_bias", "mean"),
        minimum_countries_per_origin=("countries", "min"),
        maximum_countries_per_origin=("countries", "max"),
    ).reset_index()
    result["equal_country_origin_rmse"] = np.sqrt(
        result.pop("equal_country_origin_mse")
    )
    result["estimand"] = "origins_equal_countries_equal_within_origin"
    return result.sort_values(result_keys).reset_index(drop=True)




def sequential_interval_calibration(
    errors: pd.DataFrame,
    *,
    miscoverage: float = 0.10,
    minimum_calibration_rows: int = 100,
    minimum_calibration_origins: int = 2,
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Audit symmetric empirical error bands using strictly earlier origins.

    These are sequential retrospective calibration bands. Coverage guarantees
    still require exchangeability, which temporal drift and clustered cities may
    violate; the output therefore reports realized coverage rather than claiming
    distribution-free validity.
    """
    groups = group_columns or []
    required = {
        "origin", "model", "country_code", "absolute_error", *groups,
    }
    require_columns(errors, required, source_name="row-level forecast errors")
    if not 0 < miscoverage < 1:
        raise SourceSchemaError("Interval miscoverage must be between zero and one")
    if minimum_calibration_rows < 1 or minimum_calibration_origins < 1:
        raise SourceSchemaError("Calibration minimums must be positive")
    working = errors.copy()
    if not np.isfinite(working["absolute_error"]).all():
        raise SourceSchemaError("Interval calibration requires finite absolute errors")
    keys = [*groups, "model"]
    rows: list[dict[str, float | int | str]] = []
    grouper: str | list[str] = keys[0] if len(keys) == 1 else keys
    for key, model_group in working.groupby(grouper, observed=True, sort=True):
        key_values = (key,) if len(keys) == 1 else key
        labels = dict(zip(keys, key_values, strict=True))
        for origin in sorted(model_group["origin"].unique()):
            calibration = model_group.loc[model_group["origin"] < origin]
            calibration_origin_count = calibration["origin"].nunique()
            if (
                len(calibration) < minimum_calibration_rows
                or calibration_origin_count < minimum_calibration_origins
            ):
                continue
            test = model_group.loc[model_group["origin"].eq(origin)]
            if test.empty:
                continue
            quantile_level = min(
                1.0,
                np.ceil((len(calibration) + 1) * (1 - miscoverage))
                / len(calibration),
            )
            radius = float(
                np.quantile(
                    calibration["absolute_error"], quantile_level, method="higher"
                )
            )
            covered = test["absolute_error"].le(radius)
            country_coverage = covered.groupby(test["country_code"]).mean()
            row: dict[str, float | int | str] = dict(labels)
            row.update(
                {
                    "origin": int(origin),
                    "nominal_coverage": 1 - miscoverage,
                    "empirical_city_coverage": float(covered.mean()),
                    "equal_country_coverage": float(country_coverage.mean()),
                    "coverage_gap": float(covered.mean() - (1 - miscoverage)),
                    "interval_radius": radius,
                    "interval_width": 2 * radius,
                    "test_rows": len(test),
                    "test_countries": int(test["country_code"].nunique()),
                    "calibration_rows": len(calibration),
                    "calibration_origins": int(calibration_origin_count),
                    "calibration_origin_end": int(calibration["origin"].max()),
                    "calibration_uses_current_or_future_origin": False,
                    "interval_semantics": (
                        "symmetric_pre_origin_empirical_absolute_error_band"
                    ),
                }
            )
            rows.append(row)
    if not rows:
        raise SourceSchemaError("No origin had enough prior errors for interval calibration")
    return pd.DataFrame(rows).sort_values([*groups, "origin", "model"]).reset_index(
        drop=True
    )


def locked_origin_model_evaluation(
    errors: pd.DataFrame,
    *,
    locked_origin: int,
    development_origins: list[int] | None = None,
) -> pd.DataFrame:
    """Select on earlier origins and evaluate once on a declared locked origin.

    The locked-origin best model is reported only as a hindsight diagnostic. It
    must not replace the model selected from development origins.
    """
    required = {"origin", "model", "absolute_error"}
    require_columns(errors, required, source_name="row-level forecast errors")
    working = errors.copy()
    if not np.isfinite(working["absolute_error"]).all():
        raise SourceSchemaError("Locked-origin evaluation requires finite absolute errors")
    available = set(working["origin"].unique())
    if locked_origin not in available:
        raise SourceSchemaError("Locked origin is absent from forecast errors")
    if development_origins is None:
        development = sorted(origin for origin in available if origin < locked_origin)
    else:
        if not development_origins or len(set(development_origins)) != len(
            development_origins
        ):
            raise SourceSchemaError("Development origins must be unique and non-empty")
        development = sorted(development_origins)
        if locked_origin in development:
            raise SourceSchemaError("Locked origin cannot be used for model selection")
        if any(origin >= locked_origin for origin in development):
            raise SourceSchemaError("Development origins must precede the locked origin")
        missing = set(development) - available
        if missing:
            raise SourceSchemaError("A declared development origin is absent")
    if not development:
        raise SourceSchemaError("No development origins precede the locked origin")

    development_rows = working.loc[working["origin"].isin(development)]
    locked_rows = working.loc[working["origin"].eq(locked_origin)]
    development_scores = development_rows.groupby("model", observed=True).agg(
        development_mae=("absolute_error", "mean"),
        development_n=("absolute_error", "size"),
        development_origins=("origin", "nunique"),
    )
    locked_scores = locked_rows.groupby("model", observed=True).agg(
        locked_mae=("absolute_error", "mean"),
        locked_n=("absolute_error", "size"),
    )
    common = development_scores.join(locked_scores, how="inner")
    if common.empty:
        raise SourceSchemaError("No model is available in both development and locked origins")
    common = common.reset_index().sort_values(
        ["development_mae", "model"], kind="stable"
    )
    selected = common.iloc[0]
    locked_order = common.sort_values(["locked_mae", "model"], kind="stable").reset_index(
        drop=True
    )
    locked_order["locked_rank"] = np.arange(1, len(locked_order) + 1)
    selected_locked_rank = int(
        locked_order.loc[locked_order["model"].eq(selected["model"]), "locked_rank"].iloc[0]
    )
    hindsight_best = locked_order.iloc[0]
    return pd.DataFrame(
        [
            {
                "locked_origin": locked_origin,
                "development_origin_start": min(development),
                "development_origin_end": max(development),
                "development_origins": int(selected["development_origins"]),
                "selected_model": selected["model"],
                "selection_metric": "pooled_city_origin_mae",
                "development_mae": float(selected["development_mae"]),
                "development_n": int(selected["development_n"]),
                "locked_mae": float(selected["locked_mae"]),
                "locked_n": int(selected["locked_n"]),
                "locked_rank": selected_locked_rank,
                "hindsight_best_model": hindsight_best["model"],
                "hindsight_best_locked_mae": float(hindsight_best["locked_mae"]),
                "selection_regret": float(
                    selected["locked_mae"] - hindsight_best["locked_mae"]
                ),
                "hindsight_best_is_diagnostic_only": True,
            }
        ]
    )


def paired_error_comparison(
    errors: pd.DataFrame,
    *,
    model_a: str = "persistence",
    model_b: str = "country_mean",
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Compare absolute errors for two models on the same city-origin rows."""
    groups = group_columns or ["origin", "size_bin"]
    required = {"city_id", "origin", "model", "absolute_error", *groups}
    require_columns(errors, required, source_name="row-level forecast errors")
    subset = errors.loc[errors["model"].isin([model_a, model_b])]
    index = ["city_id", "origin", *[c for c in groups if c != "origin"]]
    paired = subset.pivot(index=index, columns="model", values="absolute_error").dropna()
    if model_a not in paired or model_b not in paired:
        raise SourceSchemaError("Requested models do not have matched row-level errors")
    paired["difference"] = paired[model_a] - paired[model_b]
    paired["a_wins"] = paired[model_a] < paired[model_b]
    paired = paired.reset_index()
    result = paired.groupby(groups, observed=True).agg(
        n=("difference", "size"),
        model_a_mae=(model_a, "mean"),
        model_b_mae=(model_b, "mean"),
        mean_difference=("difference", "mean"),
        median_difference=("difference", "median"),
        model_a_win_rate=("a_wins", "mean"),
    )
    result = result.reset_index()
    result["model_a"] = model_a
    result["model_b"] = model_b
    return result


def cluster_bootstrap_paired_difference(
    errors: pd.DataFrame,
    *,
    model_a: str = "persistence",
    model_b: str = "country_mean",
    group_columns: list[str] | None = None,
    cluster_column: str = "country_code",
    repetitions: int = 2_000,
    seed: int = 20260827,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Bootstrap paired MAE differences by resampling whole country clusters."""
    groups = group_columns or ["origin", "size_bin"]
    required = {
        "city_id", "origin", "model", "absolute_error", cluster_column, *groups,
    }
    require_columns(errors, required, source_name="row-level forecast errors")
    if repetitions < 100:
        raise SourceSchemaError("Cluster bootstrap requires at least 100 repetitions")
    if not 0 < confidence < 1:
        raise SourceSchemaError("Bootstrap confidence must be between zero and one")
    subset = errors.loc[errors["model"].isin([model_a, model_b])]
    index = [
        "city_id", "origin", cluster_column, *[c for c in groups if c not in {"origin", cluster_column}]
    ]
    paired = subset.pivot(index=index, columns="model", values="absolute_error").dropna()
    if model_a not in paired or model_b not in paired:
        raise SourceSchemaError("Requested models do not have matched row-level errors")
    paired["difference"] = paired[model_a] - paired[model_b]
    paired = paired.reset_index()
    alpha = (1 - confidence) / 2
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int | str]] = []
    grouper: str | list[str] = groups[0] if len(groups) == 1 else groups
    for group_key, group in paired.groupby(grouper, observed=True, sort=True):
        keys = (group_key,) if len(groups) == 1 else group_key
        clusters = group.groupby(cluster_column)["difference"].agg(["sum", "count"])
        cluster_count = len(clusters)
        if cluster_count < 2:
            continue
        draws = rng.integers(0, cluster_count, size=(repetitions, cluster_count))
        sums = clusters["sum"].to_numpy()[draws].sum(axis=1)
        counts = clusters["count"].to_numpy()[draws].sum(axis=1)
        estimates = sums / counts
        row: dict[str, float | int | str] = dict(zip(groups, keys, strict=True))
        row.update(
            {
                "model_a": model_a,
                "model_b": model_b,
                "n": len(group),
                "clusters": cluster_count,
                "observed_mean_difference": float(group["difference"].mean()),
                "ci_lower": float(np.quantile(estimates, alpha)),
                "ci_upper": float(np.quantile(estimates, 1 - alpha)),
                "probability_model_a_better": float((estimates < 0).mean()),
                "repetitions": repetitions,
                "seed": seed,
            }
        )
        rows.append(row)
    if not rows:
        raise SourceSchemaError("No groups had enough clusters for bootstrap inference")
    return pd.DataFrame(rows)


def two_way_cluster_bootstrap_paired_difference(
    errors: pd.DataFrame,
    *,
    model_a: str = "persistence",
    model_b: str = "country_mean_leave_city_out",
    group_columns: list[str] | None = None,
    country_column: str = "country_code",
    time_column: str = "origin",
    repetitions: int = 2_000,
    seed: int = 20260827,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Bootstrap paired MAE differences by independently resampling countries and origins."""
    groups = group_columns or []
    required = {
        "city_id", "model", "absolute_error", country_column, time_column, *groups,
    }
    require_columns(errors, required, source_name="row-level forecast errors")
    if repetitions < 100:
        raise SourceSchemaError("Two-way bootstrap requires at least 100 repetitions")
    if not 0 < confidence < 1:
        raise SourceSchemaError("Bootstrap confidence must be between zero and one")
    subset = errors.loc[errors["model"].isin([model_a, model_b])]
    index = list(dict.fromkeys(["city_id", country_column, time_column, *groups]))
    paired = subset.pivot(index=index, columns="model", values="absolute_error").dropna()
    if model_a not in paired or model_b not in paired:
        raise SourceSchemaError("Requested models do not have matched row-level errors")
    paired["difference"] = paired[model_a] - paired[model_b]
    paired = paired.reset_index()
    if groups:
        grouper: str | list[str] = groups[0] if len(groups) == 1 else groups
        grouped = paired.groupby(grouper, observed=True, sort=True)
    else:
        grouped = [((), paired)]
    alpha = (1 - confidence) / 2
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int | str]] = []
    for group_key, group in grouped:
        countries = sorted(group[country_column].unique())
        times = sorted(group[time_column].unique())
        if len(countries) < 2 or len(times) < 2:
            continue
        cells = group.groupby([country_column, time_column])["difference"].agg(["sum", "count"])
        sums = cells["sum"].unstack(fill_value=0).reindex(
            index=countries, columns=times, fill_value=0
        ).to_numpy()
        counts = cells["count"].unstack(fill_value=0).reindex(
            index=countries, columns=times, fill_value=0
        ).to_numpy()
        country_draws = rng.multinomial(
            len(countries), np.full(len(countries), 1 / len(countries)), size=repetitions
        )
        time_draws = rng.multinomial(
            len(times), np.full(len(times), 1 / len(times)), size=repetitions
        )
        sampled_sums = np.einsum("rc,ct,rt->r", country_draws, sums, time_draws)
        sampled_counts = np.einsum("rc,ct,rt->r", country_draws, counts, time_draws)
        estimates = sampled_sums / sampled_counts
        keys = (group_key,) if len(groups) == 1 else group_key
        row: dict[str, float | int | str] = dict(zip(groups, keys, strict=True))
        row.update(
            {
                "model_a": model_a,
                "model_b": model_b,
                "n": len(group),
                "countries": len(countries),
                "time_clusters": len(times),
                "observed_mean_difference": float(group["difference"].mean()),
                "ci_lower": float(np.quantile(estimates, alpha)),
                "ci_upper": float(np.quantile(estimates, 1 - alpha)),
                "probability_model_a_better": float((estimates < 0).mean()),
                "repetitions": repetitions,
                "seed": seed,
            }
        )
        rows.append(row)
    if not rows:
        raise SourceSchemaError("No groups had enough country and time clusters")
    return pd.DataFrame(rows)


def leave_one_cluster_out_paired_difference(
    errors: pd.DataFrame,
    *,
    origin: int,
    cluster_columns: list[str] | None = None,
    model_a: str = "persistence",
    model_b: str = "country_mean",
) -> pd.DataFrame:
    """Measure how excluding each country or city changes a paired MAE difference."""
    clusters = cluster_columns or ["country_code"]
    required = {
        "city_id", "origin", "model", "absolute_error", *clusters,
    }
    require_columns(errors, required, source_name="row-level forecast errors")
    subset = errors.loc[
        errors["origin"].eq(origin) & errors["model"].isin([model_a, model_b])
    ]
    index = list(dict.fromkeys(["city_id", "origin", *clusters]))
    paired = subset.pivot(index=index, columns="model", values="absolute_error").dropna()
    if model_a not in paired or model_b not in paired:
        raise SourceSchemaError("Requested models do not have matched row-level errors")
    paired["difference"] = paired[model_a] - paired[model_b]
    paired = paired.reset_index()
    total_n = len(paired)
    if total_n < 2:
        raise SourceSchemaError("Leave-one-cluster-out analysis requires at least two rows")
    total_sum = float(paired["difference"].sum())
    overall = total_sum / total_n
    rows: list[dict[str, float | int | str]] = []
    grouper: str | list[str] = clusters[0] if len(clusters) == 1 else clusters
    for key, group in paired.groupby(grouper, sort=True, observed=True):
        excluded_n = total_n - len(group)
        if not excluded_n:
            continue
        keys = (key,) if len(clusters) == 1 else key
        without = (total_sum - float(group["difference"].sum())) / excluded_n
        row: dict[str, float | int | str] = dict(zip(clusters, keys, strict=True))
        row.update(
            {
                "origin": origin,
                "model_a": model_a,
                "model_b": model_b,
                "cluster_n": len(group),
                "cluster_share": len(group) / total_n,
                "cluster_mean_difference": float(group["difference"].mean()),
                "overall_mean_difference": overall,
                "excluded_mean_difference": without,
                "exclusion_shift": without - overall,
            }
        )
        rows.append(row)
    if not rows:
        raise SourceSchemaError("No leave-one-cluster-out estimates were produced")
    result = pd.DataFrame(rows)
    return result.sort_values("exclusion_shift", key=lambda x: x.abs(), ascending=False).reset_index(
        drop=True
    )


def temporal_reversal_diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    """Describe period-specific persistence, reversals, and country-adjusted association."""
    required = {
        "city_id", "country_code", "period_start", "recent_growth", "future_growth",
    }
    require_columns(panel, required, source_name="forecast interval panel")
    rows: list[dict[str, float | int]] = []
    for origin, group in panel.groupby("period_start", sort=True):
        data = group[["country_code", "recent_growth", "future_growth"]].dropna().copy()
        finite = np.isfinite(data[["recent_growth", "future_growth"]]).all(axis=1)
        data = data.loc[finite]
        if len(data) < 2:
            continue
        recent = data["recent_growth"]
        future = data["future_growth"]
        country_recent = data.groupby("country_code")["recent_growth"].transform("mean")
        country_future = data.groupby("country_code")["future_growth"].transform("mean")
        recent_residual = recent - country_recent
        future_residual = future - country_future
        variance = float(recent.var(ddof=0))
        slope = float(np.cov(recent, future, ddof=0)[0, 1] / variance) if variance else np.nan
        nonzero = recent.ne(0) & future.ne(0)
        rows.append(
            {
                "origin": int(origin),
                "n": len(data),
                "countries": data["country_code"].nunique(),
                "mean_recent_growth": float(recent.mean()),
                "mean_future_growth": float(future.mean()),
                "mean_growth_change": float((future - recent).mean()),
                "mean_absolute_growth_change": float((future - recent).abs().mean()),
                "pearson_correlation": float(recent.corr(future)),
                "spearman_correlation": float(recent.rank().corr(future.rank())),
                "within_country_correlation": float(recent_residual.corr(future_residual)),
                "persistence_slope": slope,
                "sign_agreement": float((np.sign(recent) == np.sign(future)).mean()),
                "reversal_rate_nonzero": float(
                    (np.sign(recent[nonzero]) != np.sign(future[nonzero])).mean()
                ),
            }
        )
    if not rows:
        raise SourceSchemaError("No periods available for temporal reversal diagnostics")
    return pd.DataFrame(rows)

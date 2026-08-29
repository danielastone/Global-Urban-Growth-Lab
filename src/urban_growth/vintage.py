"""Vintage-correct forecast diagnostics across explicitly different WUP definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.forecast import cluster_bootstrap_paired_difference, score_forecast
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def reciprocal_nearest_crosswalk(
    vintage_panel: pd.DataFrame,
    current_panel: pd.DataFrame,
    *,
    maximum_distance_km: float = 10.0,
) -> pd.DataFrame:
    """Match cities only when they are reciprocal geographic nearest neighbours."""
    vintage_required = {
        "city_id", "country_location_id", "city_name", "latitude", "longitude"
    }
    current_required = {
        "city_id", "LocID", "City_Name", "PWCent_Latitude", "PWCent_Longitude"
    }
    require_columns(vintage_panel, vintage_required, source_name="WUP vintage panel")
    require_columns(current_panel, current_required, source_name="WUP current panel")
    if maximum_distance_km <= 0:
        raise SourceSchemaError("Crosswalk distance must be positive")
    old = vintage_panel[list(vintage_required)].drop_duplicates()
    new = current_panel[list(current_required)].drop_duplicates()
    reject_duplicate_keys(old, ["city_id"], source_name="WUP vintage city metadata")
    reject_duplicate_keys(new, ["city_id"], source_name="WUP current city metadata")
    rows: list[dict[str, float | int | str]] = []
    for country, old_group in old.groupby("country_location_id", sort=True):
        new_group = new.loc[new["LocID"].eq(country)]
        if new_group.empty:
            continue
        old_lat = np.radians(old_group["latitude"].to_numpy())[:, None]
        old_lon = np.radians(old_group["longitude"].to_numpy())[:, None]
        new_lat = np.radians(new_group["PWCent_Latitude"].to_numpy())[None, :]
        new_lon = np.radians(new_group["PWCent_Longitude"].to_numpy())[None, :]
        haversine = np.sin((new_lat - old_lat) / 2) ** 2 + (
            np.cos(old_lat) * np.cos(new_lat) * np.sin((new_lon - old_lon) / 2) ** 2
        )
        distances = 6371.0 * 2 * np.arcsin(np.sqrt(haversine))
        old_to_new = distances.argmin(axis=1)
        new_to_old = distances.argmin(axis=0)
        for old_position, new_position in enumerate(old_to_new):
            distance = float(distances[old_position, new_position])
            if new_to_old[new_position] != old_position or distance > maximum_distance_km:
                continue
            old_row = old_group.iloc[old_position]
            new_row = new_group.iloc[new_position]
            rows.append(
                {
                    "vintage_city_id": old_row["city_id"],
                    "current_city_id": new_row["city_id"],
                    "country_location_id": country,
                    "vintage_city_name": old_row["city_name"],
                    "current_city_name": new_row["City_Name"],
                    "distance_km": distance,
                    "match_method": "reciprocal_nearest_within_country",
                }
            )
    if not rows:
        raise SourceSchemaError("No reciprocal WUP vintage crosswalk matches")
    result = pd.DataFrame(rows)
    reject_duplicate_keys(result, ["vintage_city_id"], source_name="WUP vintage crosswalk")
    reject_duplicate_keys(result, ["current_city_id"], source_name="WUP vintage crosswalk")
    return result.sort_values(["country_location_id", "vintage_city_id"]).reset_index(drop=True)


def vintage_crosswalk_coverage(
    vintage_panel: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    primary_distance_km: float = 5.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit whether reciprocal geographic matching selects the vintage universe."""
    require_columns(
        vintage_panel,
        {"city_id", "country_location_id", "country_name", "year", "population"},
        source_name="WUP vintage panel",
    )
    require_columns(
        crosswalk,
        {"vintage_city_id", "distance_km"},
        source_name="WUP vintage crosswalk",
    )
    if primary_distance_km <= 0:
        raise SourceSchemaError("Primary crosswalk distance must be positive")
    years = [2013, 2018, 2023]
    wide = vintage_panel.loc[vintage_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    metadata = vintage_panel[
        ["city_id", "country_location_id", "country_name"]
    ].drop_duplicates().set_index("city_id")
    reject_duplicate_keys(metadata.reset_index(), ["city_id"], source_name="vintage metadata")
    working = wide.join(metadata).dropna(subset=years)
    distances = crosswalk.set_index("vintage_city_id")["distance_km"]
    working["distance_km"] = working.index.map(distances)
    working["match_status"] = np.select(
        [
            working["distance_km"].le(1),
            working["distance_km"].le(primary_distance_km),
            working["distance_km"].le(10),
        ],
        ["within_1km", "1_to_5km", "5_to_10km"],
        default="no_reciprocal_match_within_10km",
    )
    working["matched_primary"] = working["distance_km"].le(primary_distance_km)
    working["prior_growth"] = (np.log(working[2018]) - np.log(working[2013])) / 5
    working["published_projected_growth"] = (
        np.log(working[2023]) - np.log(working[2018])
    ) / 5
    summary = working.groupby("match_status", sort=False).agg(
        cities=(2018, "size"),
        countries=("country_location_id", "nunique"),
        population_2018_mean=(2018, "mean"),
        population_2018_median=(2018, "median"),
        population_2018_std=(2018, "std"),
        prior_growth_mean=("prior_growth", "mean"),
        prior_growth_std=("prior_growth", "std"),
        published_projected_growth_mean=("published_projected_growth", "mean"),
        published_projected_growth_std=("published_projected_growth", "std"),
    ).reset_index()
    country = working.groupby(
        ["country_location_id", "country_name"], sort=True
    ).agg(
        vintage_cities=(2018, "size"),
        primary_matches=("matched_primary", "sum"),
    ).reset_index()
    country["excluded_cities"] = country["vintage_cities"] - country["primary_matches"]
    country["primary_match_rate"] = country["primary_matches"] / country["vintage_cities"]
    return summary, country


def vintage_country_weighting_diagnostics(
    vintage_panel: pd.DataFrame,
    current_panel: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    origin_year: int = 2018,
    lookback_years: int = 5,
    horizon_years: int = 5,
    maximum_distance_km: float = 5.0,
    repetitions: int = 2_000,
    seed: int = 20260827,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare city and country weighting and audit country influence."""
    if repetitions <= 0:
        raise SourceSchemaError("Bootstrap repetitions must be positive")
    years = [origin_year - lookback_years, origin_year, origin_year + horizon_years]
    old = vintage_panel.loc[vintage_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    new = current_panel.loc[current_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    old.columns = [f"vintage_{year}" for year in old.columns]
    new.columns = [f"current_{year}" for year in new.columns]
    matched = crosswalk.loc[crosswalk["distance_km"].le(maximum_distance_km)].merge(
        old, left_on="vintage_city_id", right_index=True, validate="one_to_one"
    ).merge(new, left_on="current_city_id", right_index=True, validate="one_to_one")
    value_columns = [
        *(f"vintage_{year}" for year in years), *(f"current_{year}" for year in years)
    ]
    matched = matched.dropna(subset=value_columns).copy()
    if matched.empty or (matched[value_columns] <= 0).any().any():
        raise SourceSchemaError("Country diagnostics require positive complete populations")
    actual = (
        np.log(matched[f"current_{origin_year + horizon_years}"])
        - np.log(matched[f"current_{origin_year}"])
    ) / horizon_years
    projection = (
        np.log(matched[f"vintage_{origin_year + horizon_years}"])
        - np.log(matched[f"vintage_{origin_year}"])
    ) / horizon_years
    persistence = (
        np.log(matched[f"vintage_{origin_year}"])
        - np.log(matched[f"vintage_{origin_year - lookback_years}"])
    ) / lookback_years
    matched["published_absolute_error"] = (projection - actual).abs()
    matched["persistence_absolute_error"] = (persistence - actual).abs()
    matched["mae_difference"] = (
        matched["published_absolute_error"] - matched["persistence_absolute_error"]
    )
    country = matched.groupby("country_location_id", sort=True).agg(
        cities=("mae_difference", "size"),
        published_projection_mae=("published_absolute_error", "mean"),
        vintage_persistence_mae=("persistence_absolute_error", "mean"),
        mae_difference=("mae_difference", "mean"),
    ).reset_index()
    total_error_difference = matched["mae_difference"].sum()
    country["leave_country_out_city_weighted_difference"] = (
        total_error_difference - country["mae_difference"] * country["cities"]
    ) / (len(matched) - country["cities"])
    country_means = country["mae_difference"].to_numpy()
    rng = np.random.default_rng(seed)
    draws = country_means[
        rng.integers(0, len(country_means), size=(repetitions, len(country_means)))
    ].mean(axis=1)
    summary = pd.DataFrame(
        [{
            "origin": origin_year,
            "target_end": origin_year + horizon_years,
            "maximum_distance_km": maximum_distance_km,
            "cities": len(matched),
            "countries": len(country),
            "city_weighted_mae_difference": matched["mae_difference"].mean(),
            "equal_country_mae_difference": country_means.mean(),
            "equal_country_ci_lower": np.quantile(draws, 0.025),
            "equal_country_ci_upper": np.quantile(draws, 0.975),
            "country_median_mae_difference": np.median(country_means),
            "countries_published_projection_wins": int((country_means < 0).sum()),
            "countries_vintage_persistence_wins": int((country_means > 0).sum()),
            "leave_country_out_minimum": country[
                "leave_country_out_city_weighted_difference"
            ].min(),
            "leave_country_out_maximum": country[
                "leave_country_out_city_weighted_difference"
            ].max(),
            "bootstrap_repetitions": repetitions,
            "bootstrap_seed": seed,
        }]
    )
    return summary, country


def vintage_revision_decomposition(
    vintage_panel: pd.DataFrame,
    current_panel: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    origin_year: int = 2018,
    horizon_years: int = 5,
    maximum_distance_km: float = 5.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Decompose the cross-revision growth-score discrepancy.

    The target term remains a mixture of true forecast error, target revision,
    and urban-definition change. No algebra using these two editions can identify
    those components separately.
    """
    if horizon_years <= 0 or maximum_distance_km <= 0:
        raise SourceSchemaError("Vintage decomposition horizon and distance must be positive")
    target_year = origin_year + horizon_years
    old = vintage_panel.loc[vintage_panel["year"].isin([origin_year, target_year])].pivot(
        index="city_id", columns="year", values="population"
    )
    new = current_panel.loc[current_panel["year"].isin([origin_year, target_year])].pivot(
        index="city_id", columns="year", values="population"
    )
    old = old.rename(columns={
        origin_year: "vintage_origin_population",
        target_year: "vintage_target_population",
    })
    new = new.rename(columns={
        origin_year: "current_origin_population",
        target_year: "current_target_population",
    })
    matched = crosswalk.loc[crosswalk["distance_km"].le(maximum_distance_km)].merge(
        old, left_on="vintage_city_id", right_index=True, validate="one_to_one"
    ).merge(new, left_on="current_city_id", right_index=True, validate="one_to_one")
    values = [
        "vintage_origin_population", "vintage_target_population",
        "current_origin_population", "current_target_population",
    ]
    matched = matched.dropna(subset=values).copy()
    if matched.empty or (matched[values] <= 0).any().any():
        raise SourceSchemaError("Vintage decomposition requires positive complete populations")
    matched["origin_revision_log_gap"] = (
        np.log(matched["vintage_origin_population"])
        - np.log(matched["current_origin_population"])
    )
    matched["target_total_log_gap"] = (
        np.log(matched["vintage_target_population"])
        - np.log(matched["current_target_population"])
    )
    matched["reported_growth_error"] = (
        matched["target_total_log_gap"] - matched["origin_revision_log_gap"]
    ) / horizon_years
    published_growth = (
        np.log(matched["vintage_target_population"])
        - np.log(matched["vintage_origin_population"])
    ) / horizon_years
    revised_growth = (
        np.log(matched["current_target_population"])
        - np.log(matched["current_origin_population"])
    ) / horizon_years
    matched["direct_growth_error"] = published_growth - revised_growth
    matched["decomposition_identity_residual"] = (
        matched["reported_growth_error"] - matched["direct_growth_error"]
    )
    matched["target_component_identification"] = (
        "forecast_error_plus_target_revision_plus_definition_change"
    )
    matched["origin_component_identification"] = (
        "origin_revision_plus_definition_change"
    )
    matched["comparison_status"] = (
        "cross_revision_cross_definition_not_clean_forecast_error"
    )
    summary = pd.DataFrame([{
        "origin": origin_year,
        "target_end": target_year,
        "horizon_years": horizon_years,
        "maximum_distance_km": maximum_distance_km,
        "cities": len(matched),
        "countries": matched["country_location_id"].nunique(),
        "mean_origin_revision_log_gap": matched["origin_revision_log_gap"].mean(),
        "mae_origin_revision_annualized": (
            matched["origin_revision_log_gap"].abs().mean() / horizon_years
        ),
        "mean_target_total_log_gap": matched["target_total_log_gap"].mean(),
        "mae_target_total_annualized": (
            matched["target_total_log_gap"].abs().mean() / horizon_years
        ),
        "reported_growth_mae": matched["reported_growth_error"].abs().mean(),
        "identity_residual_max_abs": (
            matched["decomposition_identity_residual"].abs().max()
        ),
        "target_component_identification": (
            "forecast_error_plus_target_revision_plus_definition_change"
        ),
        "comparison_status": (
            "cross_revision_cross_definition_not_clean_forecast_error"
        ),
    }])
    return matched.reset_index(drop=True), summary


def evaluate_wup2018_vintage(
    vintage_panel: pd.DataFrame,
    current_panel: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    origin_year: int = 2018,
    lookback_years: int = 5,
    horizon_years: int = 5,
    distance_thresholds: tuple[float, ...] = (1.0, 5.0, 10.0),
    population_agreement_thresholds: tuple[float | None, ...] = (None, 0.1, 0.2, 0.5),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score 2018-vintage predictors against later revised estimates.

    Only published projection versus vintage persistence is a like-for-like
    predictor ranking. The target still changes revision and urban definition.
    Retrospective persistence is a hindsight diagnostic, not a 2018 competitor.
    Population-agreement restrictions use later-revision information and are
    sensitivities, not valid real-time sample-selection rules.
    """
    years = [origin_year - lookback_years, origin_year, origin_year + horizon_years]
    old = vintage_panel.loc[vintage_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    new = current_panel.loc[current_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    old.columns = [f"vintage_{year}" for year in old.columns]
    new.columns = [f"current_{year}" for year in new.columns]
    matched = crosswalk.merge(
        old, left_on="vintage_city_id", right_index=True, validate="one_to_one"
    ).merge(new, left_on="current_city_id", right_index=True, validate="one_to_one")
    value_columns = [
        *(f"vintage_{year}" for year in years), *(f"current_{year}" for year in years)
    ]
    matched = matched.dropna(subset=value_columns).copy()
    if matched.empty or (matched[value_columns] <= 0).any().any():
        raise SourceSchemaError("Vintage evaluation requires positive complete populations")
    matched["origin_absolute_log_difference"] = np.abs(
        np.log(matched[f"current_{origin_year}"])
        - np.log(matched[f"vintage_{origin_year}"])
    )
    matched["actual"] = (
        np.log(matched[f"current_{origin_year + horizon_years}"])
        - np.log(matched[f"current_{origin_year}"])
    ) / horizon_years
    matched["published_projection"] = (
        np.log(matched[f"vintage_{origin_year + horizon_years}"])
        - np.log(matched[f"vintage_{origin_year}"])
    ) / horizon_years
    matched["vintage_persistence"] = (
        np.log(matched[f"vintage_{origin_year}"])
        - np.log(matched[f"vintage_{origin_year - lookback_years}"])
    ) / lookback_years
    matched["retrospective_persistence"] = (
        np.log(matched[f"current_{origin_year}"])
        - np.log(matched[f"current_{origin_year - lookback_years}"])
    ) / lookback_years
    models = ["published_projection", "vintage_persistence", "retrospective_persistence"]
    metric_rows: list[dict[str, float | int | str]] = []
    error_frames: list[pd.DataFrame] = []
    for distance in distance_thresholds:
        for agreement in population_agreement_thresholds:
            sample = matched.loc[matched["distance_km"].le(distance)].copy()
            agreement_label = "unrestricted"
            if agreement is not None:
                sample = sample.loc[
                    sample["origin_absolute_log_difference"].le(np.log1p(agreement))
                ]
                agreement_label = f"within_{int(agreement * 100)}pct"
            if sample.empty:
                continue
            for model in models:
                metrics = score_forecast(sample["actual"], sample[model])
                metric_rows.append(
                    {
                        "origin": origin_year,
                        "target_end": origin_year + horizon_years,
                        "distance_threshold_km": distance,
                        "origin_population_agreement": agreement_label,
                        "selection_uses_later_revision": agreement is not None,
                        "model": model,
                        "predictor_information_set": (
                            "revised_2025_hindsight"
                            if model == "retrospective_persistence"
                            else "available_in_2018"
                        ),
                        "eligible_for_like_for_like_2018_ranking": (
                            model != "retrospective_persistence"
                        ),
                        "target_comparability": "cross_revision_cross_definition",
                        "n": metrics.n,
                        "countries": sample["country_location_id"].nunique(),
                        "mae": metrics.mae,
                        "rmse": metrics.rmse,
                        "bias": metrics.bias,
                        "directional_accuracy": metrics.directional_accuracy,
                    }
                )
            long = sample.melt(
                id_vars=["current_city_id", "country_location_id"],
                value_vars=models[:2], var_name="model", value_name="predicted",
            )
            actual = sample.set_index("current_city_id")["actual"]
            long["actual"] = long["current_city_id"].map(actual)
            long["error"] = long["predicted"] - long["actual"]
            long["absolute_error"] = long["error"].abs()
            long["distance_threshold_km"] = distance
            long["origin_population_agreement"] = agreement_label
            long = long.rename(
                columns={"current_city_id": "city_id", "country_location_id": "country_code"}
            )
            long["origin"] = origin_year
            error_frames.append(long)
    metrics = pd.DataFrame(metric_rows)
    errors = pd.concat(error_frames, ignore_index=True)
    bootstrap = cluster_bootstrap_paired_difference(
        errors,
        model_a="published_projection",
        model_b="vintage_persistence",
        group_columns=["distance_threshold_km", "origin_population_agreement"],
    )
    return metrics, bootstrap
